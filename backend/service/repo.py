import logging
import os
from datetime import datetime

import sqlmodel
from apscheduler.triggers.interval import IntervalTrigger
from celery import chain, chord
from sqlalchemy import or_

from db import local_session
from exception import ClientFailure
from git.github import GithubClient
from model import Account, Commit, Repo, RepoWrite, RunConfig, Branch
from scheduler import get_jobs_scheduler
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session
from tasks.tasks import (
    create_result_metrics_view,
    download_commit,
    execute_compose_in_commit_repo,
)


def add_check_commits_job_if_not_present(repo_id: int, account_id: int):
    job_id = f"check_repo_commits__repo={repo_id}_acc={account_id}"

    if get_jobs_scheduler().get_job(job_id) is not None:
        return

    get_jobs_scheduler().add_job(
            check_repo_commits,
            args=(repo_id,),
            trigger=IntervalTrigger(minutes=5),
            id=job_id,
            replace_existing=True,
            next_run_time=datetime.now(),
        )


def add_repo(body: RepoWrite, account: Account, session: Session):
    repo = Repo(**body.dict(), account_id=account.id)
    session.add(repo)
    session.commit()
    session.refresh(repo)

    if os.getenv("DEV_MODE", "0") == "1":
        check_repo_commits(repo.id)
    else:
        add_check_commits_job_if_not_present(repo.id, account.id)

    return repo


def check_repo_commits(repo_id: int, session: Session = None):
    if session is not None:
        _check_repo_commits(repo_id, session)
    else:
        with local_session() as valid_session:
            _check_repo_commits(repo_id, valid_session)


def _check_repo_commits(repo_id: int, session: Session):
    # TODO: предусмотреть одновременный вызов этой функции из разный мест - тогда вызовется
    #  одновременный прогон контейнров, что нехорошо
    repo = session.get(Repo, repo_id)

    if os.getenv("DEV_MODE", "0") == "0":
        add_check_commits_job_if_not_present(repo.id, repo.account_id)

    git_client = GithubClient(repo.account.github_personal_api_token)

    branches = git_client.get_repo_branches(repo)

    for branch in branches:
        branch_found = session.exec(sqlmodel.select(Branch).where(
            Branch.repo_id == repo.id, Branch.sha == branch.sha)).first()
        if branch_found is None:
            session.add(branch)
            session.commit()
            session.refresh(branch)
        else:
            branch = branch_found

        commits = git_client.get_branch_commits(branch)

        for commit in commits:
            session.exec(
                insert(Commit)
                .values(
                    **commit.dict(
                        exclude={
                            "id",
                        }
                    )
                )
                # .on_conflict_do_nothing(index_elements=["sha", "branch_id"])
                .on_conflict_do_nothing(index_elements=Commit.__table_args__[0].columns)
            )
        session.commit()

    not_processed_commits = session.exec(
        sqlmodel.select(Commit).where(
            or_(*[Commit.branch_id == b.id for b in repo.branches]), Commit.processed == False
        )
    ).all()

    not_processed_commits = [
        c
        for c in not_processed_commits
        if session.exec(
            sqlmodel.select(RunConfig).where(RunConfig.commit_id == c.id)
        ).all() == []
    ]

    logging.debug(
        f"not_processed_commits: {[(x.id, x.message) for x in not_processed_commits]}"
    )

    if len(not_processed_commits) > 0:
        chord(
            chain(
                download_commit.s(repo.account.id, not_processed_commit.id),
                execute_compose_in_commit_repo.s(not_processed_commit.id),
            )
            for not_processed_commit in not_processed_commits
        )(create_result_metrics_view.s(repo_id))


def update_repo(
    repo_id: str, repo_update: RepoWrite, account: Account, session: Session
):
    repo = session.exec(
        sqlmodel.select(Repo).where(
            Repo.id == repo_id,
            Repo.account_id == account.id,
        )
    ).first()

    for key, value in repo_update.dict(exclude_unset=True, exclude={"filters"}).items():
        setattr(repo, key, value)

    session.add(repo)
    session.commit()


def delete_repo(repo_id: str, account: Account, session: Session):
    repo = session.exec(
        sqlmodel.select(Repo).where(Repo.id == repo_id, Repo.account_id == account.id)
    ).first()
    if repo is None:
        raise ClientFailure("no repo with such ID")

    session.delete(repo)
    session.commit()
