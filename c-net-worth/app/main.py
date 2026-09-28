"""FastAPI application factory and ASGI entry point."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.api import accounts, auth, dashboard
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_directory, settings.log_retention_days)

app = FastAPI(title="Couples Net Worth", docs_url=None, redoc_url=None)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    https_only=settings.session_cookie_secure,
    same_site="strict",
    max_age=8 * 60 * 60,
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.state.templates = Jinja2Templates(directory="app/templates")
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(accounts.router)


@app.get("/health", include_in_schema=False)
def health() -> JSONResponse:
    """Return a minimal container health response."""
    return JSONResponse({"status": "ok"})
