import os

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.middleware.cors import CORSMiddleware

from .global_settings import APP_NAME, APP_DESCRIPTION, APP_VERSION
from .routers.api_router import api_router
from .database.models.Base import Base
from .database.db_connection import _connector
from .security.headers_middleware import SecurityHeadersMiddleware

def create_app() -> FastAPI:
    app = FastAPI(
        title=APP_NAME,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        docs_url=None,
        redoc_url=None,
    )

    allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000, http://localhost:4173").split(",")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

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
        from .database.models.User import User                          # noqa: F401
        from .database.models.Organization import Organization          # noqa: F401
        from .database.models.OrganizationUsers import OrganizationUser # noqa: F401
        from .database.models.OrganizationRole import OrganizationRole # noqa: F401
        from .database.models.OrganizationInvites import OrganizationInvite # noqa: F401
        from .database.models.OrganizationOwnershipTransfer import OrganizationOwnershipTransfer # noqa: F401
        Base.metadata.create_all(bind=_connector.get_engine())