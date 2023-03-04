import os

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import create_engine


def get_jobs_scheduler() -> BackgroundScheduler:
    if not hasattr(get_jobs_scheduler, "scheduler"):
        postgres_db_name = os.getenv("POSTGRES_DB")
        postgres_host = os.getenv("POSTGRES_HOST")
        postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
        postgres_user = os.getenv("POSTGRES_USER")
        postgres_password = os.getenv("POSTGRES_PASSWORD")

        job_defaults = {"coalesce": True, "max_instances": 1}

        scheduler = BackgroundScheduler(job_defaults=job_defaults)

        engine = create_engine(
            f"postgresql+psycopg2://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db_name}"
        )
        scheduler.add_jobstore(SQLAlchemyJobStore(engine=engine))
        scheduler.start()

        get_jobs_scheduler.scheduler = scheduler

    return get_jobs_scheduler.scheduler
