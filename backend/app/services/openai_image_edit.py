from __future__ import annotations

import base64
import binascii
from collections.abc import Mapping
from typing import Any

import openai
from openai import OpenAI
from pydantic import SecretStr

from app.services.image_edit import (
    ImageEditErrorCategory,
    ImageEditInput,
    ImageEditProviderError,
    ImageEditResult,
)

_OUTPUT_FORMATS = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}
_INPUT_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
_CONTENT_REJECTION_CODES = {
    "content_policy_violation",
    "image_content_policy_violation",
    "image_generation_user_error",
}


class OpenAIImageEditProvider:
    """OpenAI Images API adapter; all SDK details stay within this class."""

    provider_name = "openai"

    def __init__(
        self,
        *,
        model: str,
        timeout_seconds: float = 180.0,
        default_parameters: Mapping[str, Any] | None = None,
        api_key: SecretStr | None = None,
        client: Any | None = None,
    ) -> None:
        if client is None:
            if api_key is None or not api_key.get_secret_value().strip():
                raise ImageEditProviderError(
                    ImageEditErrorCategory.PROVIDER_AUTH_ERROR,
                    "OPENAI_API_KEY is not configured.",
                )
            try:
                client = OpenAI(
                    api_key=api_key.get_secret_value(),
                    timeout=timeout_seconds,
                    max_retries=0,
                )
            except Exception:
                raise ImageEditProviderError(
                    ImageEditErrorCategory.PROVIDER_UNKNOWN_ERROR,
                    "Image provider client could not be initialized.",
                ) from None
        self.client = client
        self.model = model
        self.default_parameters = dict(default_parameters or {})

    def edit(self, request: ImageEditInput) -> ImageEditResult:
        image_inputs = [
            self._image_file(
                request.source_room_image.content,
                request.source_room_image.content_type,
                "source-room",
            ),
            self._image_file(
                request.product_reference_image.content,
                request.product_reference_image.content_type,
                "product-reference",
            ),
        ]
        parameters = {**self.default_parameters, **request.provider_parameters}
        for reserved in ("image", "model", "prompt", "n", "stream"):
            parameters.pop(reserved, None)

        try:
            response = self.client.images.edit(
                image=image_inputs,
                model=self.model,
                prompt=self._prompt_text(request),
                n=1,
                stream=False,
                **parameters,
            )
        except Exception as error:
            self._raise_safe_error(error)

        image_bytes, content_type, output_format = self._normalize_output(response)
        request_id = getattr(response, "_request_id", None) or getattr(
            response, "id", None
        )
        if not isinstance(request_id, str):
            request_id = None
        metadata: dict[str, str | int | float] = {"output_format": output_format}
        created = getattr(response, "created", None)
        if isinstance(created, (int, float)) and not isinstance(created, bool):
            metadata["created"] = created
        return ImageEditResult(
            provider=self.provider_name,
            model=self.model,
            provider_request_id=request_id,
            image_bytes=image_bytes,
            content_type=content_type,
            provider_metadata=metadata,
        )

    @staticmethod
    def _image_file(
        content: bytes, content_type: str, label: str
    ) -> tuple[str, bytes, str]:
        extension = _INPUT_EXTENSIONS.get(content_type)
        if extension is None:
            raise ImageEditProviderError(
                ImageEditErrorCategory.PROVIDER_INVALID_REQUEST,
                "Image edit input has an unsupported content type.",
            )
        return f"{label}.{extension}", content, content_type

    @staticmethod
    def _prompt_text(request: ImageEditInput) -> str:
        lines = [
            f"Target surface: {request.target_surface.value}",
            request.instructions.instruction,
        ]
        if request.instructions.constraints:
            lines.append(
                "Additional instructions:\n"
                + "\n".join(
                    f"- {constraint}" for constraint in request.instructions.constraints
                )
            )
        return "\n\n".join(lines)

    @staticmethod
    def _normalize_output(response: Any) -> tuple[bytes, str, str]:
        images = getattr(response, "data", None)
        if not images:
            raise _safe_output_error()
        encoded = getattr(images[0], "b64_json", None)
        if not isinstance(encoded, str) or not encoded:
            raise _safe_output_error()
        try:
            image_bytes = base64.b64decode(encoded, validate=True)
        except binascii.Error, ValueError:
            raise _safe_output_error() from None
        if not image_bytes:
            raise _safe_output_error()

        detected_type = _detect_content_type(image_bytes)
        if detected_type is None:
            raise _safe_output_error()
        reported_format = getattr(response, "output_format", None)
        if reported_format is None:
            output_format = detected_type.removeprefix("image/")
        else:
            output_format = str(reported_format)
            declared_type = _OUTPUT_FORMATS.get(output_format)
            if declared_type is None or declared_type != detected_type:
                raise _safe_output_error()
        return image_bytes, detected_type, output_format

    @classmethod
    def _raise_safe_error(cls, error: Exception) -> None:
        if isinstance(
            error, (openai.AuthenticationError, openai.PermissionDeniedError)
        ):
            category = ImageEditErrorCategory.PROVIDER_AUTH_ERROR
        elif isinstance(error, openai.RateLimitError):
            category = ImageEditErrorCategory.PROVIDER_RATE_LIMITED
        elif isinstance(error, openai.APITimeoutError):
            category = ImageEditErrorCategory.PROVIDER_TIMEOUT
        elif isinstance(error, openai.BadRequestError):
            category = (
                ImageEditErrorCategory.PROVIDER_CONTENT_REJECTED
                if cls._is_content_rejection(error)
                else ImageEditErrorCategory.PROVIDER_INVALID_REQUEST
            )
        elif isinstance(error, openai.UnprocessableEntityError):
            category = ImageEditErrorCategory.PROVIDER_INVALID_REQUEST
        elif isinstance(error, openai.APIConnectionError):
            category = ImageEditErrorCategory.PROVIDER_UNAVAILABLE
        elif isinstance(error, openai.APIStatusError) and error.status_code >= 500:
            category = ImageEditErrorCategory.PROVIDER_UNAVAILABLE
        else:
            category = ImageEditErrorCategory.PROVIDER_UNKNOWN_ERROR
        raise ImageEditProviderError(category, _SAFE_MESSAGES[category]) from None

    @staticmethod
    def _is_content_rejection(error: openai.BadRequestError) -> bool:
        body = error.body
        if not isinstance(body, dict):
            return False
        details = body.get("error")
        if not isinstance(details, dict):
            return False
        return (
            details.get("code") in _CONTENT_REJECTION_CODES
            or details.get("type") in _CONTENT_REJECTION_CODES
        )


_SAFE_MESSAGES = {
    ImageEditErrorCategory.PROVIDER_AUTH_ERROR: "Image provider authentication failed.",
    ImageEditErrorCategory.PROVIDER_RATE_LIMITED: "Image provider rate limit was reached.",
    ImageEditErrorCategory.PROVIDER_TIMEOUT: "Image provider request timed out.",
    ImageEditErrorCategory.PROVIDER_INVALID_REQUEST: "Image provider rejected the request.",
    ImageEditErrorCategory.PROVIDER_UNAVAILABLE: "Image provider is temporarily unavailable.",
    ImageEditErrorCategory.PROVIDER_CONTENT_REJECTED: "Image provider rejected the submitted content.",
    ImageEditErrorCategory.PROVIDER_UNKNOWN_ERROR: "Image provider returned an unusable result.",
}


def _safe_output_error() -> ImageEditProviderError:
    return ImageEditProviderError(
        ImageEditErrorCategory.PROVIDER_UNKNOWN_ERROR,
        _SAFE_MESSAGES[ImageEditErrorCategory.PROVIDER_UNKNOWN_ERROR],
    )


def _detect_content_type(content: bytes) -> str | None:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return "image/webp"
    return None
