"""Database engine and session factory."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()
url = settings.database_url
if settings.database_password_file is not None and "@" in url:
    password = settings.read_secret(settings.database_password_file)
    assert password is not None
    url = url.replace("@", f":{password.get_secret_value()}@", 1)

engine = create_engine(url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Generator[Session]:
    """Yield one database session per web request."""
    with SessionLocal() as session:
        yield session
