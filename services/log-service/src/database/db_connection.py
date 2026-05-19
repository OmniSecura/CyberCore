import logging
import os
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import Session, sessionmaker

log = logging.getLogger(__name__)


class DatabaseConnector:
    """
    Factory for SQLAlchemy engines and sessions.

    Configuration is done entirely through environment variables.
    The engine is created lazily on first use, not at import time,
    so missing env vars don't crash the process during startup.
    """

    def __init__(self) -> None:
        self.connector: str = os.getenv("DB_CONNECTOR", "sqlite").lower()
        self._engine: Engine | None = None
        self._session_factory: sessionmaker | None = None

    def _require_env(self, *names: str) -> dict[str, str]:
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

        if self.connector in {"mysql", "msql"}:
            env = self._require_env("AUTH_USERNAME", "AUTH_PASSWORD", "MYSQL_HOST")
            return URL.create(
                drivername="mysql+pymysql",
                username=env["AUTH_USERNAME"],
                password=env["AUTH_PASSWORD"],
                host=env["MYSQL_HOST"],
                port=int(os.getenv("MYSQL_PORT", "3306")),
                database=os.getenv("MYSQL_DB", "log_db"),
            )

        if self.connector in {"postgres", "postgresql"}:
            env = self._require_env("AUTH_USERNAME", "AUTH_PASSWORD", "POSTGRES_HOST")
            return URL.create(
                drivername="postgresql+psycopg",
                username=env["AUTH_USERNAME"],
                password=env["AUTH_PASSWORD"],
                host=env["POSTGRES_HOST"],
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                database=os.getenv("POSTGRES_DB", "log_db"),
            )

        raise ValueError(f"Unsupported DB_CONNECTOR: '{self.connector}'")

    def get_engine(self) -> Engine:
        if self._engine is not None:
            return self._engine

        is_sqlite = self.connector.startswith("sqlite")

        self._engine = create_engine(
            self._build_url(),
            pool_pre_ping=True,
            pool_size=5 if not is_sqlite else 1,
            max_overflow=10 if not is_sqlite else 0,
            pool_timeout=30,
            pool_recycle=3600,
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
        )
        return self._engine

    def get_session_factory(self) -> sessionmaker:
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.get_engine(),
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
        return self._session_factory

    def ping(self) -> bool:
        try:
            with self.get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def ensure_database_exists(self) -> None:
        """
        Self-heal for environments where the `01_databases.sql` init script
        couldn't run (e.g. when log_db was added AFTER the MySQL volume was
        first initialised — Docker's init scripts run only on a fresh volume).

        We open a server-level connection with NO database selected, issue a
        single CREATE DATABASE IF NOT EXISTS, then close. Safe on every boot:
        a no-op when the database already exists.

        Only runs for the MySQL/PostgreSQL connectors — pointless for SQLite.
        """
        if self.connector.startswith("sqlite"):
            return

        try:
            url = self._build_url()
            if isinstance(url, str):
                return  # SQLite fallback path — nothing to create.

            target_db = url.database
            if not target_db:
                return

            # IMPORTANT: URL.set(database=None) does NOT clear the database —
            # None is its "unchanged" sentinel. Build a fresh URL instead so
            # the connection lands at the server level, not at log_db itself
            # (which is the very thing we're trying to create).
            server_url = URL.create(
                drivername=url.drivername,
                username=url.username,
                password=url.password,
                host=url.host,
                port=url.port,
            )

            engine = create_engine(server_url, pool_pre_ping=True)
            try:
                with engine.connect() as conn:
                    conn.execute(text(
                        f"CREATE DATABASE IF NOT EXISTS `{target_db}` "
                        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    ))
                    conn.commit()
                log.info("Verified database '%s' exists.", target_db)
            finally:
                engine.dispose()
        except Exception as exc:
            # Don't crash the whole service — surface the error and let the
            # later table-creation step fail loudly with the same root cause.
            log.warning("Could not ensure database exists (%s).", exc)


_connector = DatabaseConnector()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy session."""
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
    """Context manager for use outside of FastAPI (scripts, workers, tests)."""
    session = _connector.get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
