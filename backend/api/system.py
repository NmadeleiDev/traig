from api.helpers.auth import (
    add_auth_cookie_to_response,
    remove_auth_cookie_from_response,
)
from db import get_session
from fastapi import APIRouter, Depends, Request, Response, status
from model import Account, AccountWrite, Login
from service import system as account_service

router = APIRouter(
    prefix="/system",
    tags=["System"],
)


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=Account)
def signup(
    response: Response,
    request: Request,
    body: AccountWrite,
    session: get_session = Depends(),
):
    account = account_service.create_account(body, session)
    add_auth_cookie_to_response(request, response, account_id=account.id)
    return account


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
)
def login(
    response: Response,
    request: Request,
    body: Login,
    session: get_session = Depends(),
):
    account = account_service.authorize_user(body, session)
    add_auth_cookie_to_response(request, response, account_id=account.id)
    return account


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response):
    remove_auth_cookie_from_response(request, response)
