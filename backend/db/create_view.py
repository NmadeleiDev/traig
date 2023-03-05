import logging

import sqlmodel
from sqlmodel import Session
from sqlalchemy import text

from model import Repo, Commit


def create_metrics_view(repo: Repo, session: Session):
    successfully_processed_commits = session.exec(
        sqlmodel.select(Commit)
        .where(Commit.repo_id == repo.id, Commit.processed == True, Commit.run_ok == True))

    all_metric_keys = set([])
    for commit in successfully_processed_commits:
        all_metric_keys.update(commit.json_run_result.keys())

    if len(all_metric_keys) == 0:
        logging.debug(f'no metrics found for repo_id={repo.id}')
        return

    json_metric_to_field = [
        f"json_run_result::json->'{m}' as {m}" for m in all_metric_keys
    ]

    stmt = text(f"""create or replace view repo_{repo.id} as select
                          ref,
                          message,
                          committed_datetime,
                          """ + ', '.join(json_metric_to_field) + f"""
                      from commit where repo_id = {repo.id} and processed is true and run_ok is true""")

    with session.connection().engine.connect() as conn:
        with conn.begin():
            conn.execute(stmt)
