import logging
import os
from datetime import datetime, timedelta
from typing import Callable, Optional

import jwt
import sqlmodel
from db import local_session
from exception import ClientFailure
from fastapi import Request, Response
from fastapi.routing import APIRoute
from model import Account

AUTH_TOKEN_COOKIE_NAME = "traig_client"
SERVER_JWT_SECRET = "TBNJYuTcR90W019n0N2RjIzaycG0NZlzQXLJB3/q9Q4="


def get_account_from_request(
    request: Request, session: sqlmodel.Session
) -> Optional[Account]:
    token = request.cookies.get(AUTH_TOKEN_COOKIE_NAME)
    if not token:
        return
    try:
        jwtoken = jwt.decode(token, SERVER_JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return
    account_id = int(jwtoken.get("account_id"))
    if not account_id:
        return
    return session.get(Account, account_id)


class CookieAuthMiddlewareRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            with local_session() as session:
                account = get_account_from_request(request=request, session=session)
                if not account:
                    raise ClientFailure("Account not found")
                request.state.account = account
                request.state.session = session

                response = await original_route_handler(request)
                return response

        return custom_route_handler


def add_auth_cookie_to_response(
    request: Request,
    response: Response,
    account_id: int,
):
    expr_timestamp = datetime.now() + timedelta(days=2)
    jwtoken = jwt.encode(
        {
            "exp": expr_timestamp,
            "account_id": str(account_id),
        },
        SERVER_JWT_SECRET,
    )

    dev_mode = os.environ["DEV_MODE"] == "1"

    domain = request.base_url.hostname
    if dev_mode:
        pass
    elif domain.endswith(".traig.space") or domain == "traig.space":
        pass
    else:
        logging.debug(f"Not setting auth cookie as domain is not traig.*: {domain}")
        return

    response.set_cookie(
        AUTH_TOKEN_COOKIE_NAME,
        jwtoken,
        domain=domain,
        httponly=True,
        secure=not dev_mode,
        samesite="lax",
        max_age=int(timedelta(days=3).total_seconds()),
    )


def remove_auth_cookie_from_response(request: Request, response: Response):
    dev_mode = os.environ["DEV_MODE"] == "1"

    domain = request.base_url.hostname
    if dev_mode:
        pass

    response.set_cookie(
        AUTH_TOKEN_COOKIE_NAME,
        "",
        domain=domain,
        httponly=True,
        secure=not dev_mode,
        samesite="lax",
        max_age=0,
    )
