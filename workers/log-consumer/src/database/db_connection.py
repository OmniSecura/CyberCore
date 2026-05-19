import logging
import os
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import Session, sessionmaker

log = logging.getLogger(__name__)


class DatabaseConnector:
    """Same lazy connector pattern used elsewhere in the codebase."""

    def __init__(self) -> None:
        self.connector: str = os.getenv("DB_CONNECTOR", "sqlite").lower()
        self._engine: Engine | None = None
        self._session_factory: sessionmaker | None = None

    def _require_env(self, *names: str) -> dict[str, str]:
        missing = [n for n in names if not os.getenv(n)]
        if missing:
            raise EnvironmentError(
                f"Missing required env vars for connector '{self.connector}': "
                f"{', '.join(missing)}"
            )
        return {n: os.environ[n] for n in names}

    def _build_url(self) -> URL | str:
        if self.connector == "sqlite":
            return f"sqlite:///{os.getenv('SQLITE_PATH', 'database.db')}"

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
        Mirror of log-service's helper. Both processes race on startup so
        either one may be the first to create `log_db`.

        IMPORTANT: URL.set(database=None) does NOT clear the database — None
        is its "unchanged" sentinel. Build a fresh URL from scratch instead.
        """
        if self.connector.startswith("sqlite"):
            return
        try:
            url = self._build_url()
            if isinstance(url, str):
                return
            target_db = url.database
            if not target_db:
                return
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
            log.warning("Could not ensure database exists (%s).", exc)


_connector = DatabaseConnector()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    session = _connector.get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
