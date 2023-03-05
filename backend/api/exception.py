import logging

from api.helpers.response import FailServerResponse
from exception import ClientFailure, ServerFailure
from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


async def client_failure_handler(request: Request, exc: ClientFailure):
    message = exc.args and exc.args[0] or "Unknown error"
    logging.debug(f"returning client failure: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder(FailServerResponse(message=message)),
    )


async def server_failure_handler(request: Request, exc: ServerFailure):
    message = exc.args and exc.args[0] or "Unknown error"
    logging.debug(f"returning server failure: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder(FailServerResponse(message=message)),
    )
