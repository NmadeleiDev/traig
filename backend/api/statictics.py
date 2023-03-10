import sqlmodel
from sqlalchemy import or_

from api.helpers.auth import CookieAuthMiddlewareRoute
from fastapi import APIRouter, Request, status
from model import Commit, Repo

router = APIRouter(
    prefix="/statistics",
    tags=["Operating code statistics"],
    route_class=CookieAuthMiddlewareRoute,
)


@router.get("/{repo_id}", status_code=status.HTTP_200_OK, response_model=list[Commit])
def get_commits(request: Request, repo_id: int):
    repo = request.state.session.get(Repo, repo_id)
    commits = request.state.session.exec(
        sqlmodel.select(Commit).where(
            or_(*[Commit.branch_id == b.id for b in repo.branches]),
        )
    ).all()

    for c in commits:
        _ = c.branch

    return commits
