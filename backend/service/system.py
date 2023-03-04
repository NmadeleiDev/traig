from hashlib import sha256

from exception import ClientFailure
from model import Account, AccountWrite, Login
from sqlmodel import Session, select


def _make_password_hash(password: str) -> str:
    return sha256(password.encode("utf-8")).hexdigest()


def create_account(account_config: AccountWrite, session: Session):
    present_account = session.exec(
        select(Account).where(Account.email == account_config.email)
    ).first()
    if present_account:
        raise ClientFailure("account already exists")

    account = Account(
        email=account_config.email,
        password=_make_password_hash(account_config.password),
        github_personal_api_token=account_config.github_personal_api_token,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def authorize_user(account: Login, session: Session) -> Account:
    statement = select(Account).where(
        Account.email == account.email,
        Account.password == _make_password_hash(account.password),
    )
    result = session.exec(statement).first()
    if result is None:
        raise ClientFailure("invalid credentials")
    return result
