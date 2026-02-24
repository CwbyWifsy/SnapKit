"""SQLite engine and session management."""

from pathlib import Path

from sqlalchemy import create_engine, text
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
    _migrate_sqlite_schema(engine)


def get_session(engine) -> Session:
    """Return a new session bound to *engine*."""
    return sessionmaker(bind=engine)()


def _migrate_sqlite_schema(engine) -> None:
    """Best-effort SQLite column migration for newly added fields."""
    if engine.dialect.name != "sqlite":
        return

    migrations: dict[str, dict[str, str]] = {
        "installed_apps": {
            "custom_name": "TEXT",
            "custom_icon_path": "TEXT",
            "display_icon": "TEXT",
            "uninstall_command": "TEXT",
        }
    }

    with engine.begin() as conn:
        for table_name, columns in migrations.items():
            existing = {
                row[1]
                for row in conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
            }
            for column_name, column_type in columns.items():
                if column_name in existing:
                    continue
                conn.execute(
                    text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
                )
