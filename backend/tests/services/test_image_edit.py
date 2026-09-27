from __future__ import annotations

import base64
from types import SimpleNamespace
from typing import Any

import httpx
import openai
import pytest
from pydantic import SecretStr

from app.core.config import settings
from app.models import TargetSurface
from app.services import openai_image_edit as openai_image_edit_module
from app.services.image_edit import (
    ImageAsset,
    ImageEditErrorCategory,
    ImageEditInput,
    ImageEditInstructions,
    ImageEditProviderError,
    create_image_edit_provider,
)
from app.services.openai_image_edit import OpenAIImageEditProvider


class FakeImagesAPI:
    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def edit(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


class FakeOpenAIClient:
    def __init__(self, images: FakeImagesAPI) -> None:
        self.images = images


def _input(
    *,
    provider_parameters: dict[str, Any] | None = None,
) -> ImageEditInput:
    return ImageEditInput(
        source_room_image=ImageAsset(b"\x89PNG\r\n\x1a\nroom", "image/png"),
        product_reference_image=ImageAsset(b"\xff\xd8\xffproduct", "image/jpeg"),
        target_surface=TargetSurface.FLOOR,
        instructions=ImageEditInstructions(
            instruction="Apply the reference appearance.",
            constraints=("Keep the room composition unchanged.", "No new objects."),
        ),
        provider_parameters=provider_parameters or {},
    )


def test_openai_adapter_edits_with_both_images_and_normalizes_result() -> None:
    images_api = FakeImagesAPI(
        response=SimpleNamespace(
            data=[SimpleNamespace(b64_json="iVBORw0KGgo=")],
            output_format="png",
            created=1_800_000_000,
            _request_id="req_safe_123",
        )
    )
    provider = OpenAIImageEditProvider(
        client=FakeOpenAIClient(images_api),
        model="configured-image-model",
        default_parameters={"quality": "medium"},
    )

    result = provider.edit(_input())

    assert result.provider == "openai"
    assert result.model == "configured-image-model"
    assert result.provider_request_id == "req_safe_123"
    assert result.image_bytes == b"\x89PNG\r\n\x1a\n"
    assert result.content_type == "image/png"
    assert result.provider_metadata == {
        "created": 1_800_000_000,
        "output_format": "png",
    }
    call = images_api.calls[0]
    assert call["model"] == "configured-image-model"
    assert call["n"] == 1
    assert call["image"] == [
        ("source-room.png", b"\x89PNG\r\n\x1a\nroom", "image/png"),
        ("product-reference.jpg", b"\xff\xd8\xffproduct", "image/jpeg"),
    ]
    assert "Target surface: FLOOR" in call["prompt"]
    assert "Apply the reference appearance." in call["prompt"]
    assert "Keep the room composition unchanged." in call["prompt"]


def test_request_parameters_override_defaults_but_not_core_fields() -> None:
    images_api = FakeImagesAPI(
        response=SimpleNamespace(
            data=[SimpleNamespace(b64_json="iVBORw0KGgo=")],
            output_format="png",
            created=None,
            _request_id=None,
        )
    )
    provider = OpenAIImageEditProvider(
        client=FakeOpenAIClient(images_api),
        model="configured-model",
        default_parameters={"quality": "low"},
    )

    provider.edit(
        _input(
            provider_parameters={
                "quality": "high",
                "model": "untrusted-model",
                "n": 4,
                "output_format": "png",
            }
        )
    )

    call = images_api.calls[0]
    assert call["model"] == "configured-model"
    assert call["n"] == 1
    assert call["quality"] == "high"
    assert call["output_format"] == "png"


@pytest.mark.parametrize(
    ("data", "output_format"),
    [([], "png"), ([SimpleNamespace(b64_json="")], "png")],
)
def test_openai_adapter_rejects_missing_or_empty_output(
    data: list[Any], output_format: str
) -> None:
    provider = OpenAIImageEditProvider(
        client=FakeOpenAIClient(
            FakeImagesAPI(
                response=SimpleNamespace(
                    data=data, output_format=output_format, created=None
                )
            )
        ),
        model="configured-model",
    )

    with pytest.raises(ImageEditProviderError) as error:
        provider.edit(_input())

    assert error.value.category == ImageEditErrorCategory.PROVIDER_UNKNOWN_ERROR


@pytest.mark.parametrize(
    ("data", "output_format"),
    [
        ([SimpleNamespace(b64_json="aGVsbG8=")], "png"),
        ([SimpleNamespace(b64_json="iVBORw0KGgo=")], "gif"),
    ],
)
def test_openai_adapter_rejects_unsupported_or_mismatched_output_mime(
    data: list[Any], output_format: str
) -> None:
    provider = OpenAIImageEditProvider(
        client=FakeOpenAIClient(
            FakeImagesAPI(
                response=SimpleNamespace(
                    data=data, output_format=output_format, created=None
                )
            )
        ),
        model="configured-model",
    )

    with pytest.raises(ImageEditProviderError) as error:
        provider.edit(_input())

    assert error.value.category == ImageEditErrorCategory.PROVIDER_UNKNOWN_ERROR


@pytest.mark.parametrize(
    ("image_bytes", "output_format", "content_type"),
    [
        (b"\x89PNG\r\n\x1a\nresult", "png", "image/png"),
        (b"\xff\xd8\xffresult", "jpeg", "image/jpeg"),
        (b"RIFFdataWEBPresult", "webp", "image/webp"),
    ],
)
def test_openai_adapter_normalizes_each_supported_output_format(
    image_bytes: bytes, output_format: str, content_type: str
) -> None:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    provider = OpenAIImageEditProvider(
        client=FakeOpenAIClient(
            FakeImagesAPI(
                response=SimpleNamespace(
                    data=[SimpleNamespace(b64_json=encoded)],
                    output_format=output_format,
                    created=None,
                )
            )
        ),
        model="configured-model",
    )

    result = provider.edit(_input())

    assert result.image_bytes == image_bytes
    assert result.content_type == content_type


def test_provider_input_requires_nonempty_supported_images() -> None:
    with pytest.raises(ValueError):
        ImageEditInput(
            source_room_image=ImageAsset(b"", "image/png"),
            product_reference_image=ImageAsset(b"\x89PNGdata", "image/png"),
            target_surface=TargetSurface.WALL,
            instructions=ImageEditInstructions(instruction="Edit."),
        )


def test_provider_error_message_does_not_expose_upstream_details() -> None:
    error = ImageEditProviderError(
        ImageEditErrorCategory.PROVIDER_AUTH_ERROR,
        "Image provider authentication failed.",
    )

    assert str(error) == "Image provider authentication failed."
    assert "api-key-secret" not in str(error)
    assert "raw response body" not in str(error)


def _status_error(
    error_type: type[Exception], status_code: int, *, body: Any = None
) -> Exception:
    request = httpx.Request("POST", "https://api.openai.com/v1/images/edits")
    response = httpx.Response(status_code, request=request)
    return error_type(
        "raw provider body with private prompt", response=response, body=body
    )  # type: ignore[call-arg]


@pytest.mark.parametrize(
    ("provider_error", "category"),
    [
        (
            _status_error(openai.AuthenticationError, 401),
            ImageEditErrorCategory.PROVIDER_AUTH_ERROR,
        ),
        (
            _status_error(openai.PermissionDeniedError, 403),
            ImageEditErrorCategory.PROVIDER_AUTH_ERROR,
        ),
        (
            _status_error(openai.RateLimitError, 429),
            ImageEditErrorCategory.PROVIDER_RATE_LIMITED,
        ),
        (
            openai.APITimeoutError(
                httpx.Request("POST", "https://api.openai.com/v1/images/edits")
            ),
            ImageEditErrorCategory.PROVIDER_TIMEOUT,
        ),
        (
            _status_error(openai.BadRequestError, 400),
            ImageEditErrorCategory.PROVIDER_INVALID_REQUEST,
        ),
        (
            _status_error(
                openai.BadRequestError,
                400,
                body={"error": {"code": "content_policy_violation"}},
            ),
            ImageEditErrorCategory.PROVIDER_CONTENT_REJECTED,
        ),
        (
            _status_error(openai.InternalServerError, 500),
            ImageEditErrorCategory.PROVIDER_UNAVAILABLE,
        ),
        (
            openai.APIConnectionError(
                request=httpx.Request("POST", "https://api.openai.com/v1/images/edits")
            ),
            ImageEditErrorCategory.PROVIDER_UNAVAILABLE,
        ),
    ],
)
def test_openai_errors_map_to_safe_internal_categories(
    provider_error: Exception, category: ImageEditErrorCategory
) -> None:
    provider = OpenAIImageEditProvider(
        client=FakeOpenAIClient(FakeImagesAPI(error=provider_error)),
        model="configured-model",
    )

    with pytest.raises(ImageEditProviderError) as error:
        provider.edit(_input())

    assert error.value.category == category
    assert "raw provider body" not in str(error.value)
    assert "private prompt" not in str(error.value)


def test_factory_reads_provider_configuration_without_logging_api_key() -> None:
    images_api = FakeImagesAPI(
        response=SimpleNamespace(
            data=[SimpleNamespace(b64_json="iVBORw0KGgo=")],
            output_format="png",
            created=None,
        )
    )
    configuration = settings.model_copy(
        update={
            "IMAGE_EDIT_PROVIDER": "openai",
            "OPENAI_API_KEY": SecretStr("unit-test-secret"),
            "OPENAI_IMAGE_MODEL": "configured-from-settings",
            "OPENAI_IMAGE_TIMEOUT_SECONDS": 23.0,
            "OPENAI_IMAGE_PARAMETERS": {"quality": "high"},
        }
    )

    provider = create_image_edit_provider(
        configuration, client=FakeOpenAIClient(images_api)
    )
    result = provider.edit(_input())

    assert result.model == "configured-from-settings"
    assert images_api.calls[0]["model"] == "configured-from-settings"
    assert images_api.calls[0]["quality"] == "high"


def test_factory_requires_configured_api_key_without_revealing_it() -> None:
    configuration = settings.model_copy(
        update={"IMAGE_EDIT_PROVIDER": "openai", "OPENAI_API_KEY": None}
    )

    with pytest.raises(ImageEditProviderError) as error:
        create_image_edit_provider(configuration)

    assert error.value.category == ImageEditErrorCategory.PROVIDER_AUTH_ERROR
    assert "OPENAI_API_KEY" in str(error.value)


def test_factory_passes_secret_timeout_model_and_parameters_to_sdk_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    images_api = FakeImagesAPI()
    fake_client = FakeOpenAIClient(images_api)
    constructor_options: dict[str, Any] = {}

    def build_client(**kwargs: Any) -> FakeOpenAIClient:
        constructor_options.update(kwargs)
        return fake_client

    monkeypatch.setattr(openai_image_edit_module, "OpenAI", build_client)
    configuration = settings.model_copy(
        update={
            "IMAGE_EDIT_PROVIDER": "openai",
            "OPENAI_API_KEY": SecretStr("private-test-key"),
            "OPENAI_IMAGE_MODEL": "configured-via-settings",
            "OPENAI_IMAGE_TIMEOUT_SECONDS": 31.0,
            "OPENAI_IMAGE_PARAMETERS": {"quality": "medium"},
        }
    )

    provider = create_image_edit_provider(configuration)

    assert provider.model == "configured-via-settings"
    assert constructor_options == {
        "api_key": "private-test-key",
        "timeout": 31.0,
        "max_retries": 0,
    }
    assert provider.default_parameters == {"quality": "medium"}


def test_unexpected_provider_exception_is_sanitized(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = OpenAIImageEditProvider(
        client=FakeOpenAIClient(
            FakeImagesAPI(error=RuntimeError("api-key-secret and image bytes"))
        ),
        model="configured-model",
    )

    with pytest.raises(ImageEditProviderError) as error:
        provider.edit(_input())

    assert error.value.category == ImageEditErrorCategory.PROVIDER_UNKNOWN_ERROR
    assert "api-key-secret" not in str(error.value)
    assert "image bytes" not in str(error.value)
    assert "api-key-secret" not in caplog.text
