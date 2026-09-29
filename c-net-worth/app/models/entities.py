"""Persistent entities for users, accounts and valuations."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class AccountType(StrEnum):
    """Supported financial account categories."""

    TRANSACTION = "TRANSACTION"
    SAVINGS = "SAVINGS"
    TERM_DEPOSIT = "TERM_DEPOSIT"
    SHARE_PORTFOLIO = "SHARE_PORTFOLIO"
    SUPERANNUATION = "SUPERANNUATION"


class ValuationSource(StrEnum):
    """Origins of an account valuation."""

    MANUAL = "MANUAL"
    MQTT = "MQTT"
    FUND_WEBSITE = "FUND_WEBSITE"


class User(Base):
    """Local dashboard user with a distinct login."""

    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Account(Base):
    """Financial account owned individually or jointly."""

    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_type: Mapped[str] = mapped_column(String(40), index=True)
    owner_label: Mapped[str] = mapped_column(String(120))
    institution_name: Mapped[str] = mapped_column(String(160))
    account_name: Mapped[str] = mapped_column(String(160))
    external_reference: Mapped[str | None] = mapped_column(String(160), unique=True)
    currency: Mapped[str] = mapped_column(String(3), default="AUD")
    maturity_date: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    valuations: Mapped[list["Valuation"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )


class Valuation(Base):
    """Immutable point-in-time account valuation."""

    __tablename__ = "valuations"
    __table_args__ = (
        UniqueConstraint("source", "source_reference", name="uq_source_reference"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    currency: Mapped[str] = mapped_column(String(3), default="AUD")
    valuation_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    received_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(30))
    source_reference: Mapped[str | None] = mapped_column(String(200))
    raw_payload_hash: Mapped[str | None] = mapped_column(String(64))
    account: Mapped[Account] = relationship(back_populates="valuations")
