"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    application = FastAPI(
        title="AI DevOps Configuration Reviewer API",
        version="0.1.0",
        description="Backend service for configuration analysis.",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    application.include_router(health_router)
    application.include_router(auth_router, prefix="/api/v1")

    @application.get("/", tags=["service"])
    async def service_information() -> dict[str, str]:
        return {"service": "ai-devops-configuration-reviewer", "docs": "/docs"}

    return application


app = create_app()
