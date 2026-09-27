from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, select

from app.models import (
    Brand,
    Category,
    GenerationJob,
    GenerationJobCreate,
    GenerationJobPublic,
    GenerationJobsPublic,
    GenerationJobUpdate,
    GenerationStatus,
    Item,
    Product,
    Role,
    TargetSurface,
    User,
    VisualizationProject,
    VisualizationProjectCreate,
    VisualizationProjectPublic,
    VisualizationProjectsPublic,
)


@pytest.fixture
def vis_session() -> Session:
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    tables = [
        Role.__table__,
        User.__table__,
        Item.__table__,
        Category.__table__,
        Brand.__table__,
        Product.__table__,
        VisualizationProject.__table__,
        GenerationJob.__table__,
    ]
    SQLModel.metadata.create_all(engine, tables=tables)
    with Session(engine) as session:
        yield session
    engine.dispose()


def _make_user(session: Session) -> User:
    role = Role(name=f"staff-{uuid4().hex[:8]}", slug=f"staff-{uuid4().hex[:8]}")
    session.add(role)
    session.commit()
    session.refresh(role)
    user = User(
        email=f"owner-{uuid4().hex[:8]}@example.com",
        hashed_password="hashed",
        role_id=role.id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _make_product(session: Session) -> Product:
    category = Category(
        name=f"Floor {uuid4().hex[:6]}", slug=f"floor-{uuid4().hex[:6]}"
    )
    session.add(category)
    session.commit()
    session.refresh(category)
    product = Product(
        name="Carrara",
        sku=f"SKU-{uuid4().hex[:8]}",
        slug=f"carrara-{uuid4().hex[:8]}",
        category_id=category.id,
    )
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


def _make_project(session: Session, user: User) -> VisualizationProject:
    project = VisualizationProject(
        owner_id=user.id,
        source_image_key="rooms/kitchen.jpg",
        source_image_content_type="image/jpeg",
        source_image_size_bytes=2048,
        source_image_width_px=1024,
        source_image_height_px=768,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def _make_job(
    session: Session, project: VisualizationProject, product: Product
) -> GenerationJob:
    job = GenerationJob(
        project_id=project.id,
        selected_product_id=product.id,
        target_surface=TargetSurface.FLOOR,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def test_visualization_project_exposes_source_room_image_columns() -> None:
    columns = VisualizationProject.__table__.c

    for name in (
        "id",
        "owner_id",
        "source_image_key",
        "source_image_content_type",
        "source_image_size_bytes",
        "source_image_width_px",
        "source_image_height_px",
        "source_image_url",
        "created_at",
        "updated_at",
    ):
        assert name in columns


def test_generation_job_exposes_required_columns() -> None:
    columns = GenerationJob.__table__.c

    for name in (
        "id",
        "project_id",
        "selected_product_id",
        "target_surface",
        "status",
        "provider",
        "provider_model",
        "provider_params",
        "prompt_version",
        "output_image_key",
        "output_image_url",
        "output_image_content_type",
        "output_image_width_px",
        "output_image_height_px",
        "error_code",
        "error_message",
        "retry_count",
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
    ):
        assert name in columns


def test_generation_status_values_are_the_mvp_contract() -> None:
    assert {status.value for status in GenerationStatus} == {
        "PENDING",
        "PROCESSING",
        "COMPLETED",
        "FAILED",
    }
    assert {surface.value for surface in TargetSurface} == {"FLOOR", "WALL"}


def test_generation_job_defaults_to_pending_with_zero_retries(
    vis_session: Session,
) -> None:
    user = _make_user(vis_session)
    product = _make_product(vis_session)
    project = _make_project(vis_session, user)

    job = _make_job(vis_session, project, product)

    assert job.status == GenerationStatus.PENDING.value
    assert job.retry_count == 0
    assert job.started_at is None
    assert job.completed_at is None


def test_project_create_requires_a_source_room_image() -> None:
    with pytest.raises(ValidationError):
        VisualizationProjectCreate(
            source_image_content_type="image/jpeg",
            source_image_size_bytes=2048,
            source_image_width_px=1024,
            source_image_height_px=768,
        )


def test_generation_job_rejects_unknown_surface_and_status() -> None:
    with pytest.raises(ValidationError):
        GenerationJobCreate(
            project_id=uuid4(),
            selected_product_id=uuid4(),
            target_surface="CEILING",
        )

    with pytest.raises(ValidationError):
        GenerationJobUpdate(status="DONE")


def test_user_can_own_multiple_projects_each_with_multiple_jobs(
    vis_session: Session,
) -> None:
    user = _make_user(vis_session)
    product = _make_product(vis_session)
    kitchen = _make_project(vis_session, user)
    bathroom = _make_project(vis_session, user)

    _make_job(vis_session, kitchen, product)
    _make_job(vis_session, kitchen, product)
    _make_job(vis_session, bathroom, product)

    projects = vis_session.exec(
        select(VisualizationProject).where(VisualizationProject.owner_id == user.id)
    ).all()
    assert {project.id for project in projects} == {kitchen.id, bathroom.id}

    project_ids = [project.id for project in projects]
    jobs = vis_session.exec(
        select(GenerationJob).where(GenerationJob.project_id.in_(project_ids))
    ).all()
    assert len(jobs) == 3
    assert len(kitchen.jobs) == 2
    assert len(bathroom.jobs) == 1


def test_history_is_queryable_by_owner_scoped_project(vis_session: Session) -> None:
    owner = _make_user(vis_session)
    other = _make_user(vis_session)
    product = _make_product(vis_session)
    owner_project = _make_project(vis_session, owner)
    other_project = _make_project(vis_session, other)
    owner_job = _make_job(vis_session, owner_project, product)
    _make_job(vis_session, other_project, product)

    owner_projects = vis_session.exec(
        select(VisualizationProject.id).where(VisualizationProject.owner_id == owner.id)
    ).all()
    visible_jobs = vis_session.exec(
        select(GenerationJob).where(GenerationJob.project_id.in_(owner_projects))
    ).all()

    assert [job.id for job in visible_jobs] == [owner_job.id]


def test_deleting_project_cascades_its_generation_jobs(vis_session: Session) -> None:
    user = _make_user(vis_session)
    product = _make_product(vis_session)
    project = _make_project(vis_session, user)
    job = _make_job(vis_session, project, product)

    vis_session.delete(project)
    vis_session.commit()

    assert vis_session.get(GenerationJob, job.id) is None


def test_deleting_user_cascades_projects_and_jobs(vis_session: Session) -> None:
    user = _make_user(vis_session)
    product = _make_product(vis_session)
    project = _make_project(vis_session, user)
    job = _make_job(vis_session, project, product)

    vis_session.delete(user)
    vis_session.commit()

    assert vis_session.get(VisualizationProject, project.id) is None
    assert vis_session.get(GenerationJob, job.id) is None


def test_generation_job_history_indexes_exist() -> None:
    project_indexes = {index.name for index in VisualizationProject.__table__.indexes}
    job_indexes = {index.name for index in GenerationJob.__table__.indexes}

    assert "ix_visualization_project_owner_created" in project_indexes
    assert "ix_generation_job_project_created" in job_indexes
    assert "ix_generation_job_status_created" in job_indexes
    assert "ix_generation_job_selected_product_id" in job_indexes


def test_provider_metadata_and_prompt_version_are_stored(vis_session: Session) -> None:
    user = _make_user(vis_session)
    product = _make_product(vis_session)
    project = _make_project(vis_session, user)

    job = GenerationJob(
        project_id=project.id,
        selected_product_id=product.id,
        target_surface=TargetSurface.WALL,
        provider="openai",
        provider_model="gpt-image-1",
        provider_params={"steps": 20, "guidance": 5.5},
        prompt_version="v1",
    )
    vis_session.add(job)
    vis_session.commit()
    vis_session.refresh(job)

    assert job.target_surface == "WALL"
    assert job.provider == "openai"
    assert job.provider_model == "gpt-image-1"
    assert job.provider_params == {"steps": 20, "guidance": 5.5}
    assert job.prompt_version == "v1"


def test_visualization_schemas_have_create_public_and_list_shapes() -> None:
    project_id = uuid4()
    owner_id = uuid4()
    project = VisualizationProjectPublic(
        id=project_id,
        owner_id=owner_id,
        source_image_key="rooms/room.jpg",
        source_image_content_type="image/jpeg",
        source_image_size_bytes=1024,
        source_image_width_px=640,
        source_image_height_px=480,
    )
    job = GenerationJobPublic(
        id=uuid4(),
        project_id=project_id,
        selected_product_id=uuid4(),
        target_surface=TargetSurface.FLOOR,
    )

    assert (
        VisualizationProjectCreate(
            source_image_key="rooms/room.jpg",
            source_image_content_type="image/jpeg",
            source_image_size_bytes=1024,
            source_image_width_px=640,
            source_image_height_px=480,
        ).source_image_key
        == "rooms/room.jpg"
    )
    assert VisualizationProjectsPublic(data=[project], count=1).data[0].id == project_id
    assert (
        GenerationJobCreate(
            project_id=project_id,
            selected_product_id=uuid4(),
            target_surface=TargetSurface.WALL,
        ).target_surface
        == "WALL"
    )
    assert GenerationJobUpdate(status=GenerationStatus.COMPLETED).status == "COMPLETED"
    assert GenerationJobsPublic(data=[job], count=1).data[0].project_id == project_id
