import os

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware

from .global_settings import APP_NAME, APP_DESCRIPTION, APP_VERSION, ALLOWED_ORIGINS
from .routers.api_router import api_router
from .database.db_connection import _connector
from .database.models.Base import Base
from .database.models.ScanJob import ScanJob          # noqa: F401 — must be imported so SQLAlchemy registers the relationship
from .database.models.ScanFinding import ScanFinding  # noqa: F401
from .security.http_client import close_clients
from .security.headers_middleware import SecurityHeadersMiddleware
from .security.limiter.rate_limit import limiter, RateLimitExceeded, _rate_limit_exceeded_handler


def create_app() -> FastAPI:
    app = FastAPI(
        title=APP_NAME,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        docs_url=None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # Defense-in-depth response headers — closes the X-Content-Type-Options,
    # X-Frame-Options, Referrer-Policy, Permissions-Policy findings that ZAP
    # raises on every endpoint by default.
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/", include_in_schema=False)
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{APP_NAME} — Swagger UI",
        )

    @app.get("/health", tags=["System"])
    def health():
        return {
            "status": "ok",
            "database": "reachable" if _connector.ping() else "unreachable",
        }

    app.include_router(api_router)

    return app


app = create_app()


@app.on_event("startup")
def on_startup() -> None:
    if os.getenv("DB_CREATE_TABLES", "false").lower() == "true":
        Base.metadata.create_all(bind=_connector.get_engine())


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await close_clients()
