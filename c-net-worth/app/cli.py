"""Administrative command-line functions."""

import argparse
import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.models import Account, User, Valuation  # noqa: F401


def init_db() -> None:
    """Create database tables for the initial release."""
    Base.metadata.create_all(engine)


def create_user(username: str) -> None:
    """Create a distinct local dashboard user.

    Args:
        username: Unique login name.
    """
    display_name = input("Display name: ").strip()
    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation or len(password) < 12:
        raise SystemExit("Passwords must match and contain at least 12 characters")
    with SessionLocal() as session:
        if session.scalar(select(User).where(User.username == username)) is not None:
            raise SystemExit("Username already exists")
        session.add(
            User(
                username=username,
                display_name=display_name,
                password_hash=hash_password(password),
            )
        )
        session.commit()


def main() -> None:
    """Dispatch an administrative command."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init-db")
    create = subparsers.add_parser("create-user")
    create.add_argument("username")
    args = parser.parse_args()
    if args.command == "init-db":
        init_db()
    elif args.command == "create-user":
        create_user(args.username)


if __name__ == "__main__":
    main()
