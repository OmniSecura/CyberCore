import os
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


# ── Base model ────────────────────────────────────────────────────────────────

# class Base(DeclarativeBase):
#     """Shared declarative base — all ORM models inherit from this."""
#     pass


# ── Connector ─────────────────────────────────────────────────────────────────

class DatabaseConnector:
    """
    Factory for SQLAlchemy engines and sessions.

    Configuration is done entirely through environment variables.
    The engine is created lazily on first use, not at import time,
    so missing env vars don't crash the process during startup.

    Supported connectors (set via DB_CONNECTOR):
        sqlite          File-based SQLite (path via SQLITE_PATH, default: database.db)
        sqlite-local    Same as sqlite but uses SQLITE_LOCAL_PATH (default: local.db)
        mysql / msql    MySQL via PyMySQL
        postgres /
        postgresql      PostgreSQL via psycopg3

    Credentials (MySQL / PostgreSQL):
        AUTH_USERNAME   Database username
        AUTH_PASSWORD   Database password
        MYSQL_HOST / POSTGRES_HOST
        MYSQL_PORT / POSTGRES_PORT  (defaults: 3306 / 5432)
        MYSQL_DB   / POSTGRES_DB    (default: "database")
    """

    def __init__(self) -> None:
        self.connector: str = os.getenv("DB_CONNECTOR", "sqlite").lower()
        self._engine: Engine | None = None
        self._session_factory: sessionmaker | None = None

    # ── Internal builders ─────────────────────────────────────────────────────

    def _require_env(self, *names: str) -> dict[str, str]:
        """Return {name: value} for each env var, raise clearly if any are missing."""
        missing = [n for n in names if not os.getenv(n)]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variable(s) for "
                f"connector '{self.connector}': {', '.join(missing)}"
            )
        return {n: os.environ[n] for n in names}

    def _build_url(self) -> URL | str:
        if self.connector == "sqlite":
            path = os.getenv("SQLITE_PATH", "database.db")
            return f"sqlite:///{path}"

        if self.connector == "sqlite-local":
            path = os.getenv("SQLITE_LOCAL_PATH", "local.db")
            return f"sqlite:///{path}"

        if self.connector in {"mysql", "msql"}:
            env = self._require_env("AUTH_USERNAME", "AUTH_PASSWORD", "MYSQL_HOST")
            return URL.create(
                drivername="mysql+pymysql",
                username=env["AUTH_USERNAME"],
                password=env["AUTH_PASSWORD"],
                host=env["MYSQL_HOST"],
                port=int(os.getenv("MYSQL_PORT", "3306")),
                database=os.getenv("MYSQL_DB", "database"),
            )

        if self.connector in {"postgres", "postgresql"}:
            env = self._require_env("AUTH_USERNAME", "AUTH_PASSWORD", "POSTGRES_HOST")
            return URL.create(
                drivername="postgresql+psycopg",
                username=env["AUTH_USERNAME"],
                password=env["AUTH_PASSWORD"],
                host=env["POSTGRES_HOST"],
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                database=os.getenv("POSTGRES_DB", "database"),
            )

        raise ValueError(f"Unsupported DB_CONNECTOR: '{self.connector}'")

    # ── Public API ────────────────────────────────────────────────────────────

    def get_engine(self) -> Engine:
        if self._engine is not None:
            return self._engine

        is_sqlite = self.connector.startswith("sqlite")

        self._engine = create_engine(
            self._build_url(),
            # Verify connections are alive before handing them out of the pool.
            pool_pre_ping=True,
            # SQLite doesn't benefit from a pool — use StaticPool instead.
            poolclass=None if not is_sqlite else None,
            # Keep a small number of persistent connections ready.
            pool_size=5 if not is_sqlite else 1,
            # Allow bursting beyond pool_size under load.
            max_overflow=10 if not is_sqlite else 0,
            # Drop a connection if it has been checked out for more than 30 min.
            pool_timeout=30,
            # Recycle connections older than 1 hour to avoid stale TCP issues.
            pool_recycle=3600,
            # Echo SQL to stdout — reads from env so you toggle it without code changes.
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
        )
        return self._engine

    def get_session_factory(self) -> sessionmaker:
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.get_engine(),
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,  # avoids extra SELECT after commit
            )
        return self._session_factory

    def ping(self) -> bool:
        """Return True if the database is reachable, False otherwise."""
        try:
            with self.get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False


# ── Module-level singletons ───────────────────────────────────────────────────
# Nothing is actually connected here — the engine is built on first use.

_connector = DatabaseConnector()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a SQLAlchemy session.

    Usage:
        @router.get("/")
        def my_route(db: Session = Depends(get_db)):
            ...
    """
    session = _connector.get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    Context manager for use outside of FastAPI (scripts, workers, tests).

    Usage:
        with db_session() as db:
            db.add(some_model)
    """
    session = _connector.get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()