from api import metric, repo, statictics, system
from api.exception import client_failure_handler, server_failure_handler
from api.helpers.response import FailServerResponse
from exception import ClientFailure, ServerFailure
from fastapi import FastAPI, status


def init_api() -> FastAPI:
    app = FastAPI(
        title="Traig Backend",
        description="API docs for Traig Backend",
        version="0.0.1",
        contact={"name": "Gregory Potemkin", "email": "potemkin3940@gmail.com"},
        openapi_url="/openapi.json",
        docs_url="/docs",
        root_path="/",
        responses={
            status.HTTP_400_BAD_REQUEST: {"model": FailServerResponse},
            status.HTTP_401_UNAUTHORIZED: {"model": FailServerResponse},
            status.HTTP_404_NOT_FOUND: {"model": FailServerResponse},
            status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": FailServerResponse},
        },
    )

    app.include_router(system.router)
    app.include_router(repo.router)
    app.include_router(metric.router)
    app.include_router(statictics.router)

    app.exception_handler(ClientFailure)(client_failure_handler)
    app.exception_handler(ServerFailure)(server_failure_handler)

    return app
