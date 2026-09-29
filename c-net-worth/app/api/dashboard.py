"""Dashboard route."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import current_user
from app.database.session import get_session
from app.models.entities import User
from app.services.net_worth import latest_balances

router = APIRouter()


@router.get("/")
def dashboard(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(current_user)],
):  # type: ignore[no-untyped-def]
    """Render current combined net worth."""
    balances = latest_balances(session)
    total = sum((item.amount for item in balances), start=Decimal("0"))
    return request.app.state.templates.TemplateResponse(
        request,
        "dashboard.html",
        {"user": user, "balances": balances, "total": total},
    )
