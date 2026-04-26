import os

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.middleware.cors import CORSMiddleware

from .global_settings import APP_NAME, APP_DESCRIPTION, APP_VERSION
from .routers.api_router import api_router
from .database.models.Base import Base
from .database.db_connection import _connector
from .security.middleware import AutoRefreshMiddleware


def create_app() -> FastAPI:
    app = FastAPI(
        title=APP_NAME,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        docs_url=None,
        redoc_url=None,
    )

    allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    # Automatically refreshes the access token on every request when it is
    # expired but a valid refresh token cookie is present.
    # The client never has to call /refresh manually.
    app.add_middleware(AutoRefreshMiddleware)

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
        from .database.models.User import User  # noqa: F401
        Base.metadata.create_all(bind=_connector.get_engine())