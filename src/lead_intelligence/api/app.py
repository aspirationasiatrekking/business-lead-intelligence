from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from src.lead_intelligence.api.admin import router as admin_router
from src.lead_intelligence.api.auth import (
    AuthConfig,
    LoginLimiter,
    register_auth_errors,
    require_user,
)
from src.lead_intelligence.api.auth import (
    router as auth_router,
)
from src.lead_intelligence.api.dependencies import build_runtime_engine
from src.lead_intelligence.api.errors import register_error_handlers
from src.lead_intelligence.api.exports import router as exports_router
from src.lead_intelligence.api.jobs import router as jobs_router
from src.lead_intelligence.api.schemas import (
    CountryResponse,
    HealthResponse,
    ReadinessResponse,
)
from src.lead_intelligence.database.session import create_session_factory
from src.lead_intelligence.utils.country_utils import get_country_options


def create_app(
    *,
    engine_factory: Callable[[], Engine] = build_runtime_engine,
    auth_config: AuthConfig | None = None,
) -> FastAPI:
    """Create the HTTP application without connecting at import time."""

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        engine = engine_factory()
        try:
            application.state.engine = engine
            application.state.session_factory = create_session_factory(engine)
            yield
        finally:
            engine.dispose()

    application = FastAPI(
        title="Business Lead Intelligence",
        version="0.1.0",
        lifespan=lifespan,
        debug=False,
    )

    application.state.auth_config = auth_config or AuthConfig.load()
    application.state.login_limiter = LoginLimiter()

    @application.middleware("http")
    async def prevent_sensitive_caching(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @application.get("/health", tags=["System"])
    def health() -> HealthResponse:
        return HealthResponse()

    @application.get(
        "/ready",
        tags=["System"],
        responses={503: {"model": ReadinessResponse}},
    )
    def readiness(request: Request, response: Response) -> ReadinessResponse:
        try:
            with request.app.state.engine.connect() as connection:
                role = connection.execute(text("SELECT current_user")).scalar_one()
                ready = role == "bli_app"
        except (SQLAlchemyError, RuntimeError):
            ready = False

        if not ready:
            response.status_code = 503
            return ReadinessResponse(status="unavailable")
        return ReadinessResponse(status="ready")

    @application.get("/api/v1/countries", tags=["Reference data"])
    def countries() -> list[CountryResponse]:
        return [CountryResponse(**option) for option in get_country_options()]

    register_error_handlers(application)
    register_auth_errors(application)
    application.include_router(auth_router)
    application.include_router(admin_router)
    application.include_router(jobs_router, dependencies=[Depends(require_user)])
    application.include_router(exports_router, dependencies=[Depends(require_user)])
    return application


app = create_app()
