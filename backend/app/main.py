"""FastAPI application entry point."""

import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import Response

from app.api.routes.analyses import router as analyses_router
from app.api.routes.auth import router as auth_router
from app.api.routes.configurations import router as configurations_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.limiter import limiter
from app.core.logging import configure_logging
from app.core.metrics import REQUEST_COUNT, REQUEST_DURATION
from app.middleware.security import SecurityHeadersMiddleware

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(
        title="AI DevOps Configuration Reviewer API",
        version="0.1.0",
        description="Backend service for configuration analysis.",
    )

    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    application.add_middleware(SlowAPIMiddleware)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @application.middleware("http")
    async def log_requests(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        path = request.url.path
        status = str(response.status_code)
        REQUEST_COUNT.labels(method=request.method, endpoint=path, status=status).inc()
        REQUEST_DURATION.labels(method=request.method, endpoint=path).observe(duration)
        logger.info(
            "%s %s %s %dms",
            request.method,
            path,
            response.status_code,
            round(duration * 1000),
        )
        return response

    application.include_router(health_router)
    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(configurations_router, prefix="/api/v1")
    application.include_router(analyses_router, prefix="/api/v1")

    @application.get("/", tags=["service"])
    async def service_information() -> dict[str, str]:
        return {"service": "ai-devops-configuration-reviewer", "docs": "/docs"}

    return application


app = create_app()
