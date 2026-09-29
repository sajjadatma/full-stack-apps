from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import case, func
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.core.rbac import (
    GENERATIONS_READ_ANY,
    GENERATIONS_READ_OWN,
    PRODUCTS_READ,
    PRODUCTS_READ_ANY,
    has_permissions,
)
from app.models import (
    DashboardGenerationMetrics,
    DashboardProductMetrics,
    DashboardSummaryPublic,
    GenerationJob,
    GenerationStatus,
    Product,
    VisualizationProject,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary/", response_model=DashboardSummaryPublic)
def read_dashboard_summary(
    *, session: SessionDep, current_user: CurrentUser
) -> DashboardSummaryPublic:
    product_metrics = None
    if has_permissions(
        current_user, PRODUCTS_READ_ANY, PRODUCTS_READ, require_all=False
    ):
        can_read_any_products = has_permissions(current_user, PRODUCTS_READ_ANY)
        product_statement = select(
            func.count(Product.id),
            func.count(case((Product.is_active.is_(True), Product.id))),
            func.count(
                case(
                    (
                        Product.is_active.is_(True)
                        & (Product.stock_quantity > 0)
                        & Product.low_stock_threshold.is_not(None)
                        & (Product.stock_quantity <= Product.low_stock_threshold),
                        Product.id,
                    )
                )
            ),
        )
        if not can_read_any_products:
            product_statement = product_statement.where(Product.is_active.is_(True))
        total_products, active_products, low_stock_products = session.exec(
            product_statement
        ).one()
        product_metrics = DashboardProductMetrics(
            total_products=total_products,
            active_products=active_products,
            low_stock_products=low_stock_products,
        )

    generation_metrics = None
    can_read_any_generations = has_permissions(current_user, GENERATIONS_READ_ANY)
    can_read_own_generations = has_permissions(current_user, GENERATIONS_READ_OWN)
    if can_read_any_generations or can_read_own_generations:
        generation_statement = select(GenerationJob.status, func.count()).select_from(
            GenerationJob
        )
        if not can_read_any_generations:
            generation_statement = generation_statement.join(
                VisualizationProject,
                GenerationJob.project_id == VisualizationProject.id,
            ).where(VisualizationProject.owner_id == current_user.id)
        generation_rows = session.exec(
            generation_statement.group_by(GenerationJob.status)
        ).all()
        counts = {status.value.lower(): 0 for status in GenerationStatus}
        for status, count in generation_rows:
            counts[str(status).lower()] = count
        generation_metrics = DashboardGenerationMetrics(
            total=sum(counts.values()),
            pending=counts[GenerationStatus.PENDING.value.lower()],
            processing=counts[GenerationStatus.PROCESSING.value.lower()],
            completed=counts[GenerationStatus.COMPLETED.value.lower()],
            failed=counts[GenerationStatus.FAILED.value.lower()],
        )

    return DashboardSummaryPublic(
        products=product_metrics,
        generations=generation_metrics,
    )
