"""Login and logout routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.database.session import get_session
from app.models.entities import User

router = APIRouter()


@router.get("/login")
def login_form(request: Request):  # type: ignore[no-untyped-def]
    """Render the login form."""
    return request.app.state.templates.TemplateResponse(request, "login.html", {})


@router.post("/login")
def login(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    session: Annotated[Session, Depends(get_session)],
):  # type: ignore[no-untyped-def]
    """Authenticate a local dashboard user."""
    user = session.scalar(select(User).where(User.username == username))
    if user is None or not user.is_active or not verify_password(user.password_hash, password):
        return request.app.state.templates.TemplateResponse(
            request, "login.html", {"error": "Invalid username or password"}, status_code=401
        )
    request.session.clear()
    request.session["user_id"] = user.id
    return RedirectResponse("/", status_code=303)


@router.post("/logout")
def logout(request: Request) -> RedirectResponse:
    """Clear the signed session."""
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
