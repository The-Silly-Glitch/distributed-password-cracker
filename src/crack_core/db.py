import os
import logging
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from crack_core.models import Base

logger = logging.getLogger("crack_core.db")

DEFAULT_PG_URL = os.environ.get(
    "DATABASE_URL", 
    "postgresql+psycopg2://cracker:cracker_secret@localhost:5432/cracker_db"
)
DEFAULT_SQLITE_URL = "sqlite:///cracker.db"

_engine = None
_SessionFactory = None


def get_engine(db_url: Optional[str] = None):
    global _engine, _SessionFactory
    if _engine is not None and db_url is None:
        return _engine

    target_url = db_url or DEFAULT_PG_URL
    try:
        # Test connecting to Postgres
        engine = create_engine(target_url, pool_pre_ping=True)
        with engine.connect() as conn:
            pass
        logger.info(f"Database connected using: {target_url}")
        _engine = engine
    except Exception as e:
        logger.warning(f"Could not connect to {target_url}: {e}. Falling back to SQLite.")
        _engine = create_engine(DEFAULT_SQLITE_URL, connect_args={"check_same_thread": False})

    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def init_db(engine=None):
    """Initialize database tables."""
    eng = engine or get_engine()
    Base.metadata.create_all(bind=eng)
    return eng


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Provide a transactional database session."""
    if _SessionFactory is None:
        get_engine()
    session: Session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
