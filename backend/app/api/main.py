from fastapi import APIRouter

from app.api.routes import (
    brands,
    categories,
    items,
    login,
    private,
    products,
    roles,
    users,
    utils,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(categories.router)
api_router.include_router(brands.router)
api_router.include_router(products.router)
api_router.include_router(products.image_router)


if settings.FASTAPI_ENV == "development":
    api_router.include_router(private.router)
