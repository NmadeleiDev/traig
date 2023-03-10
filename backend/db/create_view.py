import logging

import sqlmodel
from model import Commit, Repo
from sqlalchemy import text, or_
from sqlmodel import Session


def create_metrics_view(repo: Repo, session: Session):
    successfully_processed_commits = session.exec(
        sqlmodel.select(Commit).where(
            or_(*[Commit.branch_id == b.id for b in repo.branches]), Commit.processed == True, Commit.run_ok == True
        )
    )

    all_metric_keys = set([])
    for commit in successfully_processed_commits:
        all_metric_keys.update(commit.json_run_result.keys())

    if len(all_metric_keys) == 0:
        logging.debug(f"no metrics found for repo_id={repo.id}")
        return

    json_metric_to_field = [
        f"json_run_result::json->'{m}' as {m}" for m in all_metric_keys
    ]

    branch_filters = ' or '.join([f'branch_id = {b.id}' for b in repo.branches])

    stmt = text(
        f"""create or replace view repo_{repo.id} as select
                    branch_id,
                    sha,
                    message,
                    committed_datetime,
        """
        + ", ".join(json_metric_to_field)
        + f"""
                      from commit where ({branch_filters}) and processed is true and run_ok is true"""
    )

    with session.connection().engine.connect() as conn:
        with conn.begin():
            conn.execute(stmt)
