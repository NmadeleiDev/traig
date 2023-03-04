import sqlmodel
from api.helpers.auth import CookieAuthMiddlewareRoute
from fastapi import APIRouter, Request, status
from model import Commit

router = APIRouter(
    prefix="/statistics",
    tags=["Operating code statistics"],
    route_class=CookieAuthMiddlewareRoute,
)


@router.get("/{repo_id}", status_code=status.HTTP_200_OK, response_model=list[Commit])
def get_commits(request: Request, repo_id: int):
    commits = request.state.session.exec(
        sqlmodel.select(Commit).where(
            Commit.repo_id == repo_id,
        )
    ).all()

    return commits
