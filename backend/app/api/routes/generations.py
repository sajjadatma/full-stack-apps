from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import selectinload
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep, ensure_permissions
from app.core.config import settings
from app.core.i18n import t
from app.core.rbac import (
    GENERATIONS_CREATE,
    GENERATIONS_READ_ANY,
    GENERATIONS_READ_OWN,
    has_permissions,
)
from app.models import (
    GenerationJob,
    GenerationJobPublic,
    GenerationJobsPublic,
    GenerationProductSummaryPublic,
    GenerationRequest,
    GenerationStatus,
    Product,
    ProductImage,
    TargetSurface,
    VisualizationProject,
)
from app.services.generation_processor import (
    GenerationProcessingError,
    process_generation_job,
    validate_reference_image,
)
from app.services.image_edit_prompts import (
    ImageEditPrompt,
    build_floor_prompt,
    build_wall_prompt,
)
from app.services.image_metadata import ImageMetadataError, image_dimensions
from app.services.storage import StorageService, get_storage_service

router = APIRouter(prefix="/generations", tags=["generations"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=GenerationJobPublic, status_code=202)
def create_generation(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    request: GenerationRequest,
) -> GenerationJobPublic:
    ensure_permissions(current_user, GENERATIONS_CREATE)
    project = session.exec(
        select(VisualizationProject).where(
            VisualizationProject.id == request.visualization_project_id,
            VisualizationProject.owner_id == current_user.id,
        )
    ).first()
    if project is None:
        raise HTTPException(
            status_code=404, detail=t("visualization_project_not_found")
        )

    product = session.get(Product, request.selected_product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=422, detail=t("generation_product_unavailable"))
    if (
        not product.suitable_surfaces
        or request.target_surface not in product.suitable_surfaces
    ):
        raise HTTPException(status_code=422, detail=t("generation_product_unsuitable"))

    primary_images = session.exec(
        select(ProductImage).where(
            ProductImage.product_id == product.id,
            ProductImage.is_primary.is_(True),
        )
    ).all()
    if len(primary_images) != 1:
        raise HTTPException(
            status_code=422, detail=t("generation_primary_image_required")
        )
    product_image = primary_images[0]
    storage = get_storage_service()
    try:
        validate_reference_image(storage=storage, product=product, image=product_image)
        _validate_project_source(storage, project)
    except GenerationProcessingError as error:
        raise HTTPException(status_code=422, detail=error.safe_message) from None

    prompt = _build_prompt(request.target_surface, product, product_image)
    job = GenerationJob(
        project_id=project.id,
        selected_product_id=product.id,
        target_surface=request.target_surface,
        status=GenerationStatus.PENDING,
        prompt_version=prompt.prompt_version,
        retry_count=0,
    )
    session.add(job)
    try:
        session.commit()
        session.refresh(job)
    except Exception as error:
        session.rollback()
        logger.error(
            "Could not persist pending generation exception_type=%s",
            type(error).__name__,
        )
        raise HTTPException(
            status_code=500, detail=t("generation_create_failed")
        ) from None

    response = _job_public(job)
    background_tasks.add_task(process_generation_job, job.id)
    return response


@router.post("/{job_id}/retry", response_model=GenerationJobPublic, status_code=202)
def retry_generation(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    job_id: uuid.UUID,
) -> GenerationJobPublic:
    ensure_permissions(current_user, GENERATIONS_CREATE, GENERATIONS_READ_OWN)
    source = session.get(GenerationJob, job_id)
    if source is None:
        raise HTTPException(status_code=404, detail=t("generation_not_found"))
    project = session.get(VisualizationProject, source.project_id)
    if project is None or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail=t("generation_not_found"))
    if source.status != GenerationStatus.FAILED:
        raise HTTPException(status_code=409, detail=t("generation_retry_not_allowed"))

    product = session.get(Product, source.selected_product_id)
    if product is None or not product.is_active:
        raise HTTPException(status_code=422, detail=t("generation_product_unavailable"))
    surface = TargetSurface(source.target_surface)
    if not product.suitable_surfaces or surface not in product.suitable_surfaces:
        raise HTTPException(status_code=422, detail=t("generation_product_unsuitable"))
    primary_images = session.exec(
        select(ProductImage).where(
            ProductImage.product_id == product.id,
            ProductImage.is_primary.is_(True),
        )
    ).all()
    if len(primary_images) != 1:
        raise HTTPException(
            status_code=422, detail=t("generation_primary_image_required")
        )
    product_image = primary_images[0]
    storage = get_storage_service()
    try:
        validate_reference_image(storage=storage, product=product, image=product_image)
        _validate_project_source(storage, project)
    except GenerationProcessingError as error:
        raise HTTPException(status_code=422, detail=error.safe_message) from None

    prompt = _build_prompt(surface, product, product_image)
    retry = GenerationJob(
        project_id=source.project_id,
        selected_product_id=source.selected_product_id,
        target_surface=surface,
        status=GenerationStatus.PENDING,
        retry_count=source.retry_count + 1,
        retry_of_job_id=source.id,
        prompt_version=prompt.prompt_version,
    )
    session.add(retry)
    try:
        session.commit()
        session.refresh(retry)
    except Exception as error:
        session.rollback()
        logger.error(
            "Could not persist retried generation source_job_id=%s exception_type=%s",
            source.id,
            type(error).__name__,
        )
        raise HTTPException(
            status_code=500, detail=t("generation_retry_create_failed")
        ) from None

    response = _job_public(retry)
    background_tasks.add_task(process_generation_job, retry.id)
    return response


@router.get("/", response_model=GenerationJobsPublic)
def read_generations(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> GenerationJobsPublic:
    ensure_permissions(
        current_user,
        GENERATIONS_READ_OWN,
        GENERATIONS_READ_ANY,
        require_all=False,
    )
    can_read_any = has_permissions(current_user, GENERATIONS_READ_ANY)
    owner_join = GenerationJob.project_id == VisualizationProject.id
    count_statement = (
        select(func.count())
        .select_from(GenerationJob)
        .join(VisualizationProject, owner_join)
    )
    jobs_statement = (
        select(GenerationJob)
        .join(VisualizationProject, owner_join)
        .options(
            selectinload(GenerationJob.selected_product).selectinload(Product.images)
        )
        .order_by(
            col(GenerationJob.created_at).desc(),
            col(GenerationJob.id).desc(),
        )
        .offset(skip)
        .limit(limit)
    )
    if not can_read_any:
        owner_filter = VisualizationProject.owner_id == current_user.id
        count_statement = count_statement.where(owner_filter)
        jobs_statement = jobs_statement.where(owner_filter)
    count = session.exec(count_statement).one()
    jobs = session.exec(jobs_statement).all()
    return GenerationJobsPublic(data=[_job_public(job) for job in jobs], count=count)


@router.get("/{job_id}", response_model=GenerationJobPublic)
def read_generation(
    *, session: SessionDep, current_user: CurrentUser, job_id: uuid.UUID
) -> GenerationJobPublic:
    return _job_public(
        _readable_job(session=session, current_user=current_user, job_id=job_id)
    )


@router.get(
    "/{job_id}/product-image",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {
                "image/jpeg": {"schema": {"type": "string", "format": "binary"}},
                "image/png": {"schema": {"type": "string", "format": "binary"}},
                "image/webp": {"schema": {"type": "string", "format": "binary"}},
            }
        }
    },
)
def read_generation_product_image(
    *, session: SessionDep, current_user: CurrentUser, job_id: uuid.UUID
) -> StreamingResponse:
    job = _readable_job(session=session, current_user=current_user, job_id=job_id)
    product = job.selected_product or session.get(Product, job.selected_product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=t("product_image_not_found"))
    primary_image = session.exec(
        select(ProductImage).where(
            ProductImage.product_id == product.id,
            ProductImage.is_primary.is_(True),
        )
    ).first()
    if primary_image is None:
        raise HTTPException(status_code=404, detail=t("product_image_not_found"))
    try:
        content = get_storage_service().stream(primary_image.storage_key)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=t("product_image_not_found")
        ) from None
    return StreamingResponse(
        content,
        media_type=primary_image.content_type,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get(
    "/{job_id}/result",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {
                "image/jpeg": {"schema": {"type": "string", "format": "binary"}},
                "image/png": {"schema": {"type": "string", "format": "binary"}},
                "image/webp": {"schema": {"type": "string", "format": "binary"}},
            }
        }
    },
)
def read_generation_result(
    *, session: SessionDep, current_user: CurrentUser, job_id: uuid.UUID
) -> StreamingResponse:
    job = _readable_job(session=session, current_user=current_user, job_id=job_id)
    if job.status != GenerationStatus.COMPLETED or not job.output_image_key:
        raise HTTPException(status_code=409, detail=t("generation_result_not_ready"))
    try:
        content = get_storage_service().stream(job.output_image_key)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=t("generation_result_not_found")
        ) from None
    return StreamingResponse(
        content,
        media_type=job.output_image_content_type,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


def _readable_job(
    *, session: SessionDep, current_user: CurrentUser, job_id: uuid.UUID
) -> GenerationJob:
    can_read_own = has_permissions(current_user, GENERATIONS_READ_OWN)
    can_read_any = has_permissions(current_user, GENERATIONS_READ_ANY)
    if not can_read_own and not can_read_any:
        raise HTTPException(status_code=403, detail=t("not_enough_permissions"))
    job = session.exec(
        select(GenerationJob)
        .where(GenerationJob.id == job_id)
        .options(
            selectinload(GenerationJob.selected_product).selectinload(Product.images)
        )
    ).first()
    if job is None:
        raise HTTPException(status_code=404, detail=t("generation_not_found"))
    if not can_read_any:
        project = session.get(VisualizationProject, job.project_id)
        if project is None or project.owner_id != current_user.id:
            raise HTTPException(status_code=404, detail=t("generation_not_found"))
    return job


def _job_public(job: GenerationJob) -> GenerationJobPublic:
    output_url = (
        f"{settings.API_V1_STR}/generations/{job.id}/result"
        if job.status == GenerationStatus.COMPLETED and job.output_image_key
        else None
    )
    product = job.selected_product
    primary_image_id = None
    selected_product = None
    if product is not None:
        primary_image_id = next(
            (image.id for image in product.images if image.is_primary), None
        )
        selected_product = GenerationProductSummaryPublic(
            id=product.id,
            name=product.name,
            sku=product.sku,
            width_mm=product.width_mm,
            height_mm=product.height_mm,
            thickness_mm=product.thickness_mm,
            finish=product.finish,
            material=product.material,
            color_family=product.color_family,
            is_active=product.is_active,
            primary_image_id=primary_image_id,
        )
    return GenerationJobPublic.model_validate(
        job,
        update={"output_image_url": output_url, "selected_product": selected_product},
    )


def _build_prompt(
    surface: TargetSurface, product: Product, image: ProductImage
) -> ImageEditPrompt:
    if surface is TargetSurface.FLOOR:
        return build_floor_prompt(product, image)
    return build_wall_prompt(product, image)


def _validate_project_source(
    storage: StorageService, project: VisualizationProject
) -> None:
    try:
        content = bytearray()
        for chunk in storage.stream(project.source_image_key):
            content.extend(chunk)
            if len(content) > storage.max_file_size_bytes:
                raise ValueError("stored room image exceeds size limit")
        dimensions = image_dimensions(bytes(content), project.source_image_content_type)
    except FileNotFoundError, ImageMetadataError, ValueError:
        raise HTTPException(
            status_code=422, detail=t("generation_room_image_invalid")
        ) from None
    if dimensions != (project.source_image_width_px, project.source_image_height_px):
        raise HTTPException(status_code=422, detail=t("generation_room_image_invalid"))
