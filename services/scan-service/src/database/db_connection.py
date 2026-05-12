import os
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import Session, sessionmaker


class DatabaseConnector:
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


_connector = DatabaseConnector()
engine = _connector.get_engine()


def get_db() -> Generator[Session, None, None]:
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
    session = _connector.get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
