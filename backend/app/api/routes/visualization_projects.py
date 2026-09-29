import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep, ensure_permissions
from app.core.config import settings
from app.core.i18n import t
from app.core.rbac import GENERATIONS_CREATE
from app.models import (
    VisualizationProject,
    VisualizationProjectPublic,
    VisualizationProjectsPublic,
)
from app.services.image_metadata import ImageMetadataError, image_dimensions
from app.services.storage import (
    StorageNamespace,
    UploadValidationError,
    get_storage_service,
)

router = APIRouter(prefix="/visualization-projects", tags=["visualization-projects"])
logger = logging.getLogger(__name__)


def _project_public(project: VisualizationProject) -> VisualizationProjectPublic:
    source_image_url = (
        f"{settings.API_V1_STR}/visualization-projects/{project.id}/source-image"
    )
    return VisualizationProjectPublic.model_validate(
        project, update={"source_image_url": source_image_url}
    )


def _owned_project(
    *, session: SessionDep, current_user: CurrentUser, project_id: uuid.UUID
) -> VisualizationProject:
    project = session.exec(
        select(VisualizationProject).where(
            VisualizationProject.id == project_id,
            VisualizationProject.owner_id == current_user.id,
        )
    ).first()
    if project is None:
        raise HTTPException(
            status_code=404, detail=t("visualization_project_not_found")
        )
    return project


@router.post("/", response_model=VisualizationProjectPublic, status_code=201)
def create_visualization_project(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    file: Annotated[UploadFile, File()],
    name: Annotated[str | None, Form(max_length=255)] = None,
) -> VisualizationProjectPublic:
    ensure_permissions(current_user, GENERATIONS_CREATE)
    storage = get_storage_service()
    content = file.file.read(storage.max_file_size_bytes + 1)
    content_type = file.content_type or ""
    try:
        width_px, height_px = image_dimensions(content, content_type)
        stored = storage.upload(
            content=content,
            content_type=content_type,
            namespace=StorageNamespace.ROOM_PHOTOS,
            private=True,
        )
    except (ImageMetadataError, UploadValidationError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    project = VisualizationProject(
        name=name,
        owner_id=current_user.id,
        source_image_key=stored.key,
        source_image_content_type=stored.content_type,
        source_image_size_bytes=stored.size_bytes,
        source_image_width_px=width_px,
        source_image_height_px=height_px,
    )
    session.add(project)
    try:
        session.commit()
        session.refresh(project)
    except Exception as error:
        session.rollback()
        try:
            storage.delete(stored.key)
        except Exception:
            logger.exception(
                "Failed to compensate room image upload for %s", stored.key
            )
        raise HTTPException(
            status_code=500, detail=t("visualization_project_create_failed")
        ) from error
    return _project_public(project)


@router.get("/", response_model=VisualizationProjectsPublic)
def read_visualization_projects(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> VisualizationProjectsPublic:
    owner_filter = VisualizationProject.owner_id == current_user.id
    count = session.exec(
        select(func.count()).select_from(VisualizationProject).where(owner_filter)
    ).one()
    projects = session.exec(
        select(VisualizationProject)
        .where(owner_filter)
        .order_by(
            col(VisualizationProject.created_at).desc(),
            col(VisualizationProject.id).desc(),
        )
        .offset(skip)
        .limit(limit)
    ).all()
    return VisualizationProjectsPublic(
        data=[_project_public(project) for project in projects], count=count
    )


@router.get("/{project_id}", response_model=VisualizationProjectPublic)
def read_visualization_project(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    project_id: uuid.UUID,
) -> VisualizationProjectPublic:
    return _project_public(
        _owned_project(
            session=session, current_user=current_user, project_id=project_id
        )
    )


@router.get(
    "/{project_id}/source-image",
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
def read_visualization_source_image(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    project_id: uuid.UUID,
) -> StreamingResponse:
    project = _owned_project(
        session=session, current_user=current_user, project_id=project_id
    )
    try:
        content = get_storage_service().stream(project.source_image_key)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404, detail=t("visualization_room_image_not_found")
        ) from error
    return StreamingResponse(
        content,
        media_type=project.source_image_content_type,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
