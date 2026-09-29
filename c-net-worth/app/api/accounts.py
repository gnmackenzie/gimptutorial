"""Manual deposit-account entry routes."""

from datetime import date, datetime, UTC
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.dependencies import current_user
from app.database.session import get_session
from app.models.entities import Account, AccountType, User, Valuation, ValuationSource

router = APIRouter(prefix="/accounts")


@router.get("/new")
def new_account(
    request: Request,
    _user: Annotated[User, Depends(current_user)],
):  # type: ignore[no-untyped-def]
    """Render manual account entry."""
    return request.app.state.templates.TemplateResponse(request, "account_form.html", {})


@router.post("")
def create_account(
    _user: Annotated[User, Depends(current_user)],
    session: Annotated[Session, Depends(get_session)],
    account_type: Annotated[AccountType, Form()],
    owner_label: Annotated[str, Form(min_length=1, max_length=120)],
    institution_name: Annotated[str, Form(min_length=1, max_length=160)],
    account_name: Annotated[str, Form(min_length=1, max_length=160)],
    balance: Annotated[Decimal, Form(ge=0)],
    maturity_date: Annotated[date | None, Form()] = None,
) -> RedirectResponse:
    """Create an account and its opening valuation."""
    if account_type == AccountType.TERM_DEPOSIT and maturity_date is None:
        raise ValueError("A term deposit requires a maturity date")
    now = datetime.now(UTC)
    account = Account(
        account_type=account_type.value,
        owner_label=owner_label.strip(),
        institution_name=institution_name.strip(),
        account_name=account_name.strip(),
        currency="AUD",
        maturity_date=maturity_date,
    )
    account.valuations.append(
        Valuation(
            amount=balance,
            currency="AUD",
            valuation_time=now,
            received_time=now,
            source=ValuationSource.MANUAL.value,
        )
    )
    session.add(account)
    session.commit()
    return RedirectResponse("/", status_code=303)
