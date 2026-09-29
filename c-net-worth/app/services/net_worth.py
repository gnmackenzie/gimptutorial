"""Net-worth aggregation queries."""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.entities import Account, Valuation


@dataclass(frozen=True, slots=True)
class AccountBalance:
    """Account and its latest recorded balance."""

    account: Account
    amount: Decimal


def latest_balances(session: Session) -> list[AccountBalance]:
    """Return the latest valuation of each active account.

    Args:
        session: Active database session.

    Returns:
        Active accounts paired with their latest balance.
    """
    latest: Select[tuple[int, object]] = (
        select(Valuation.account_id, func.max(Valuation.valuation_time).label("when"))
        .group_by(Valuation.account_id)
        .subquery()
    )
    rows = session.execute(
        select(Account, Valuation.amount)
        .join(latest, latest.c.account_id == Account.id)
        .join(
            Valuation,
            (Valuation.account_id == latest.c.account_id)
            & (Valuation.valuation_time == latest.c.when),
        )
        .where(Account.is_active.is_(True))
        .order_by(Account.account_type, Account.account_name)
    ).all()
    return [AccountBalance(account=row[0], amount=row[1]) for row in rows]
