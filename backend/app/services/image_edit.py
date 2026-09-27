from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from app.core.config import Settings, settings
from app.models import TargetSurface

_INPUT_SIGNATURES: dict[str, Callable[[bytes], bool]] = {
    "image/jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
    "image/png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/webp": lambda data: (
        len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    ),
}


class ImageEditErrorCategory(StrEnum):
    PROVIDER_AUTH_ERROR = "provider_auth_error"
    PROVIDER_RATE_LIMITED = "provider_rate_limited"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_INVALID_REQUEST = "provider_invalid_request"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_CONTENT_REJECTED = "provider_content_rejected"
    PROVIDER_UNKNOWN_ERROR = "provider_unknown_error"


class ImageEditProviderError(Exception):
    """Safe, provider-neutral error; never includes upstream response details."""

    def __init__(self, category: ImageEditErrorCategory, safe_message: str) -> None:
        self.category = category
        self.safe_message = safe_message
        super().__init__(safe_message)


@dataclass(frozen=True)
class ImageAsset:
    content: bytes
    content_type: str

    def __post_init__(self) -> None:
        signature = _INPUT_SIGNATURES.get(self.content_type)
        if not self.content or signature is None or not signature(self.content):
            raise ValueError(
                "Image content must be non-empty and match a supported type"
            )


@dataclass(frozen=True)
class ImageEditInstructions:
    instruction: str
    constraints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.instruction.strip() or any(
            not item.strip() for item in self.constraints
        ):
            raise ValueError("Image edit instructions cannot be empty")


@dataclass(frozen=True)
class ImageEditInput:
    source_room_image: ImageAsset
    product_reference_image: ImageAsset
    target_surface: TargetSurface
    instructions: ImageEditInstructions
    provider_parameters: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ImageEditResult:
    provider: str
    model: str
    provider_request_id: str | None
    image_bytes: bytes
    content_type: str
    provider_metadata: Mapping[str, str | int | float]


class ImageEditProvider(Protocol):
    """Provider-neutral image editing port for application/domain code."""

    @property
    def provider_name(self) -> str: ...

    @property
    def model(self) -> str: ...

    def edit(self, request: ImageEditInput) -> ImageEditResult: ...


def create_image_edit_provider(
    configuration: Settings = settings, *, client: Any | None = None
) -> ImageEditProvider:
    """Construct the configured provider behind the provider-neutral port."""
    if configuration.IMAGE_EDIT_PROVIDER == "openai":
        from app.services.openai_image_edit import OpenAIImageEditProvider

        return OpenAIImageEditProvider(
            api_key=configuration.OPENAI_API_KEY,
            model=configuration.OPENAI_IMAGE_MODEL,
            timeout_seconds=configuration.OPENAI_IMAGE_TIMEOUT_SECONDS,
            default_parameters=configuration.OPENAI_IMAGE_PARAMETERS,
            client=client,
        )
    raise ImageEditProviderError(
        ImageEditErrorCategory.PROVIDER_UNKNOWN_ERROR,
        "Configured image provider is not available.",
    )
