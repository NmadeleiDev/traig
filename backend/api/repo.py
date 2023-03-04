import sqlmodel
from api.helpers.auth import CookieAuthMiddlewareRoute
from fastapi import APIRouter, Request, status
from model import Repo, RepoWrite
from service import repo as repo_service

router = APIRouter(
    prefix="/repo",
    tags=["Operating repositories"],
    route_class=CookieAuthMiddlewareRoute,
)


@router.get("", status_code=status.HTTP_200_OK, response_model=list[Repo])
def get_repos(request: Request):
    repos = request.state.session.exec(
        sqlmodel.select(Repo).where(
            Repo.account_id == request.state.account.id,
        )
    ).all()

    return repos


@router.post("", status_code=status.HTTP_200_OK, response_model=Repo)
@router.post("/", include_in_schema=False)
def add_repo(request: Request, body: RepoWrite):
    repo = repo_service.add_repo(body, request.state.account, request.state.session)

    return repo


@router.get(
    "/check/{repo_id}",
    status_code=status.HTTP_200_OK,
)
def check_repo_commits(request: Request, repo_id: int):
    repo_service.check_repo_commits(repo_id, request.state.session)


@router.patch(
    "/{repo_id}",
    status_code=status.HTTP_200_OK,
)
def update_repo(request: Request, body: RepoWrite, repo_id: str):
    repo_service.update_repo(
        repo_id, body, request.state.account, request.state.session
    )


@router.delete(
    "/{repo_id}",
    status_code=status.HTTP_200_OK,
)
def delete_repo(request: Request, repo_id: str):
    repo_service.delete_repo(repo_id, request.state.account, request.state.session)
