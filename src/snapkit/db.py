"""SQLite engine and session management."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from snapkit.models import Base

DEFAULT_DB_DIR = Path.home() / ".snapkit"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "snapkit.db"


def get_engine(db_path: Path | str | None = None):
    """Create a SQLAlchemy engine. Pass `":memory:"` for testing."""
    if db_path == ":memory:":
        url = "sqlite:///:memory:"
    else:
        path = Path(db_path) if db_path else DEFAULT_DB_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{path}"
    return create_engine(url)


def init_db(engine) -> None:
    """Create all tables."""
    Base.metadata.create_all(engine)


def get_session(engine) -> Session:
    """Return a new session bound to *engine*."""
    return sessionmaker(bind=engine)()
