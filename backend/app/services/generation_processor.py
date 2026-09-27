from __future__ import annotations

import logging
import math
import re
import uuid
from collections.abc import Mapping
from typing import Any

from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.models import (
    GenerationJob,
    GenerationStatus,
    Product,
    ProductImage,
    TargetSurface,
    VisualizationProject,
    get_datetime_utc,
)
from app.services.image_edit import (
    ImageAsset,
    ImageEditErrorCategory,
    ImageEditInput,
    ImageEditProvider,
    ImageEditProviderError,
    ImageEditResult,
    create_image_edit_provider,
)
from app.services.image_edit_prompts import (
    ImageEditPrompt,
    build_floor_prompt,
    build_wall_prompt,
)
from app.services.image_metadata import ImageMetadataError, image_dimensions
from app.services.storage import StorageNamespace, StorageService, get_storage_service

logger = logging.getLogger(__name__)


class GenerationProcessingError(Exception):
    def __init__(self, error_code: str, safe_message: str) -> None:
        self.error_code = error_code
        self.safe_message = safe_message
        super().__init__(safe_message)


_PROVIDER_FAILURES = {
    ImageEditErrorCategory.PROVIDER_AUTH_ERROR: (
        "provider_error",
        "Image provider authentication failed.",
    ),
    ImageEditErrorCategory.PROVIDER_RATE_LIMITED: (
        "provider_error",
        "Image provider rate limit was reached.",
    ),
    ImageEditErrorCategory.PROVIDER_TIMEOUT: (
        "provider_timeout",
        "Image provider request timed out.",
    ),
    ImageEditErrorCategory.PROVIDER_INVALID_REQUEST: (
        "provider_error",
        "Image provider rejected the image request.",
    ),
    ImageEditErrorCategory.PROVIDER_UNAVAILABLE: (
        "provider_error",
        "Image provider is temporarily unavailable.",
    ),
    ImageEditErrorCategory.PROVIDER_CONTENT_REJECTED: (
        "content_rejected",
        "Image provider rejected the submitted content.",
    ),
    ImageEditErrorCategory.PROVIDER_UNKNOWN_ERROR: (
        "provider_error",
        "Image provider returned an unusable result.",
    ),
}
_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


def validate_reference_image(
    *, storage: StorageService, product: Product, image: ProductImage
) -> bytes:
    if image.product_id != product.id or not image.is_primary:
        raise GenerationProcessingError(
            "unsuitable_product", "The product has no valid primary reference image."
        )
    try:
        content = _read_object(storage, image.storage_key)
        asset = ImageAsset(content=content, content_type=image.content_type)
        image_dimensions(asset.content, asset.content_type)
    except FileNotFoundError, ValueError, ImageMetadataError:
        raise GenerationProcessingError(
            "unsuitable_product", "The product has no valid primary reference image."
        ) from None
    return content


def process_generation_job(job_id: uuid.UUID | str) -> None:
    """Run one persisted pending job; duplicate scheduling is safe to ignore."""
    normalized_id = uuid.UUID(str(job_id))
    try:
        prepared = _transition_to_processing(normalized_id)
        if prepared is None:
            return
        request, prompt, source_dimensions = prepared
        provider = create_image_edit_provider()
        _persist_provider_identity(normalized_id, provider)
        result = provider.edit(request)
        output_dimensions = _validate_result(result, source_dimensions)
        stored = get_storage_service().upload(
            content=result.image_bytes,
            content_type=result.content_type,
            namespace=StorageNamespace.GENERATION_RESULTS,
            private=True,
        )
        if not _persist_completion(
            normalized_id,
            result,
            prompt,
            stored.key,
            output_dimensions,
        ):
            _delete_stored_output(stored.key, normalized_id)
    except GenerationProcessingError as error:
        _mark_failed(normalized_id, error.error_code, error.safe_message)
    except ImageEditProviderError as error:
        error_code, message = _PROVIDER_FAILURES.get(
            error.category,
            _PROVIDER_FAILURES[ImageEditErrorCategory.PROVIDER_UNKNOWN_ERROR],
        )
        _mark_failed(normalized_id, error_code, message)
    except Exception as error:
        _mark_failed(
            normalized_id,
            "internal_error",
            "Generation could not be completed.",
        )
        logger.error(
            "Generation processing failed job_id=%s exception_type=%s",
            normalized_id,
            type(error).__name__,
        )


def _transition_to_processing(
    job_id: uuid.UUID,
) -> tuple[ImageEditInput, ImageEditPrompt, tuple[int, int]] | None:
    storage = get_storage_service()
    with Session(engine) as session:
        job = session.exec(
            select(GenerationJob).where(GenerationJob.id == job_id).with_for_update()
        ).first()
        if job is None or job.status != GenerationStatus.PENDING:
            return None
        job.status = GenerationStatus.PROCESSING
        job.started_at = get_datetime_utc()
        job.provider = settings.IMAGE_EDIT_PROVIDER
        session.add(job)
        session.commit()

        project = session.get(VisualizationProject, job.project_id)
        product = session.get(Product, job.selected_product_id)
        if project is None:
            raise GenerationProcessingError(
                "invalid_room_photo", "The room image is no longer available."
            )
        if product is None or not product.is_active:
            raise GenerationProcessingError(
                "unsuitable_product", "The selected product is no longer available."
            )
        surface = TargetSurface(job.target_surface)
        if surface not in (product.suitable_surfaces or []):
            raise GenerationProcessingError(
                "unsuitable_product",
                "The selected product is not suitable for this surface.",
            )
        primary_images = session.exec(
            select(ProductImage).where(
                ProductImage.product_id == product.id,
                ProductImage.is_primary.is_(True),
            )
        ).all()
        if len(primary_images) != 1:
            raise GenerationProcessingError(
                "unsuitable_product",
                "The product has no valid primary reference image.",
            )
        product_image = primary_images[0]

        try:
            source_bytes = _read_object(storage, project.source_image_key)
            source_image = ImageAsset(
                content=source_bytes,
                content_type=project.source_image_content_type,
            )
            source_dimensions = image_dimensions(
                source_image.content, source_image.content_type
            )
        except FileNotFoundError, ValueError, ImageMetadataError:
            raise GenerationProcessingError(
                "invalid_room_photo", "The room image is no longer valid."
            ) from None
        if source_dimensions != (
            project.source_image_width_px,
            project.source_image_height_px,
        ):
            raise GenerationProcessingError(
                "invalid_room_photo", "The room image dimensions are inconsistent."
            )

        product_bytes = validate_reference_image(
            storage=storage, product=product, image=product_image
        )
        prompt = (
            build_floor_prompt(product, product_image)
            if surface is TargetSurface.FLOOR
            else build_wall_prompt(product, product_image)
        )
        request = ImageEditInput(
            source_room_image=source_image,
            product_reference_image=ImageAsset(
                content=product_bytes,
                content_type=product_image.content_type,
            ),
            target_surface=surface,
            instructions=prompt.instructions,
        )
        job.prompt_version = prompt.prompt_version
        session.add(job)
        session.commit()
        return request, prompt, source_dimensions


def _persist_provider_identity(job_id: uuid.UUID, provider: ImageEditProvider) -> None:
    with Session(engine) as session:
        job = session.get(GenerationJob, job_id)
        if job is None or job.status != GenerationStatus.PROCESSING:
            return
        job.provider = _safe_identifier(provider.provider_name, max_length=64)
        job.provider_model = _safe_identifier(provider.model, max_length=120)
        session.add(job)
        session.commit()


def _validate_result(
    result: ImageEditResult, source_dimensions: tuple[int, int]
) -> tuple[int, int]:
    if not result.image_bytes:
        raise GenerationProcessingError(
            "provider_error", "Image provider returned an empty image."
        )
    try:
        output_dimensions = image_dimensions(result.image_bytes, result.content_type)
    except ValueError, ImageMetadataError:
        raise GenerationProcessingError(
            "provider_error", "Image provider returned an unsupported image."
        ) from None
    if output_dimensions != source_dimensions:
        raise GenerationProcessingError(
            "provider_error",
            "Image provider returned an image with incorrect dimensions.",
        )
    return output_dimensions


def _persist_completion(
    job_id: uuid.UUID,
    result: ImageEditResult,
    prompt: ImageEditPrompt,
    output_key: str,
    dimensions: tuple[int, int],
) -> bool:
    try:
        with Session(engine) as session:
            job = session.get(GenerationJob, job_id)
            if job is None or job.status != GenerationStatus.PROCESSING:
                return False
            job.status = GenerationStatus.COMPLETED
            job.provider = _safe_identifier(result.provider, max_length=64)
            job.provider_model = _safe_identifier(result.model, max_length=120)
            job.provider_params = _sanitize_provider_metadata(result.provider_metadata)
            job.prompt_version = prompt.prompt_version
            job.output_image_key = output_key
            job.output_image_url = f"{settings.API_V1_STR}/generations/{job_id}/result"
            job.output_image_content_type = result.content_type
            job.output_image_width_px, job.output_image_height_px = dimensions
            job.error_code = None
            job.error_message = None
            job.completed_at = get_datetime_utc()
            session.add(job)
            session.commit()
        return True
    except Exception as error:
        logger.error(
            "Generation completion persistence failed job_id=%s exception_type=%s",
            job_id,
            type(error).__name__,
        )
        _mark_failed(
            job_id,
            "internal_error",
            "Generation could not be completed.",
        )
        return False


def _mark_failed(job_id: uuid.UUID, error_code: str, safe_message: str) -> None:
    try:
        with Session(engine) as session:
            job = session.get(GenerationJob, job_id)
            if job is None or job.status in {
                GenerationStatus.COMPLETED,
                GenerationStatus.FAILED,
            }:
                return
            job.status = GenerationStatus.FAILED
            job.error_code = error_code
            job.error_message = safe_message[:500]
            job.output_image_key = None
            job.output_image_url = None
            job.output_image_content_type = None
            job.output_image_width_px = None
            job.output_image_height_px = None
            job.completed_at = get_datetime_utc()
            session.add(job)
            session.commit()
    except Exception as error:
        logger.error(
            "Could not persist failed generation job_id=%s exception_type=%s",
            job_id,
            type(error).__name__,
        )


def _delete_stored_output(key: str, job_id: uuid.UUID) -> None:
    try:
        get_storage_service().delete(key)
    except Exception as error:
        logger.error(
            "Could not compensate generation output job_id=%s exception_type=%s",
            job_id,
            type(error).__name__,
        )


def _read_object(storage: StorageService, key: str) -> bytes:
    content = bytearray()
    for chunk in storage.stream(key):
        content.extend(chunk)
        if len(content) > storage.max_file_size_bytes:
            raise ValueError("Stored image exceeds the allowed size")
    return bytes(content)


def _sanitize_provider_metadata(
    metadata: Mapping[str, Any],
) -> dict[str, str | int | float]:
    safe: dict[str, str | int | float] = {}
    output_format = metadata.get("output_format")
    if isinstance(output_format, str) and output_format in {"png", "jpeg", "webp"}:
        safe["output_format"] = output_format
    created = metadata.get("created")
    if (
        isinstance(created, (int, float))
        and not isinstance(created, bool)
        and math.isfinite(created)
    ):
        safe["created"] = created
    return safe


def _safe_identifier(value: str, *, max_length: int) -> str:
    if (
        not value
        or len(value) > max_length
        or not _SAFE_IDENTIFIER.fullmatch(value)
        or any(
            term in value.lower()
            for term in ("secret", "token", "credential", "apikey")
        )
    ):
        raise GenerationProcessingError(
            "provider_error", "Image provider returned invalid metadata."
        )
    return value
