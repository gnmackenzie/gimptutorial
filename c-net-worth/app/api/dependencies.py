"""Shared web dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.models.entities import User


def current_user(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> User:
    """Resolve the signed-in user or reject the request."""
    user_id = request.session.get("user_id")
    user = session.get(User, user_id) if isinstance(user_id, int) else None
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user
