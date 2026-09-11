"""Create and configure the FastAPI application."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from music_to_mp3.web.database import initialise_database
from music_to_mp3.web.jobs import clean_expired_downloads
from music_to_mp3.web.routes import router
from music_to_mp3.web.settings import get_settings


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Initialise persistent storage during application startup.

    Args:
        application: FastAPI application being started.

    Yields:
        Control to the running ASGI server.
    """

    del application
    settings = get_settings()
    settings.data_root.mkdir(parents=True, exist_ok=True)
    settings.download_root.mkdir(parents=True, exist_ok=True)
    initialise_database()
    clean_expired_downloads()
    yield


app = FastAPI(
    title="Music Export",
    version="2.0.0",
    lifespan=lifespan,
)
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")
app.include_router(router)
