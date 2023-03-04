import contextlib
import os

from model import *


def get_dsn():
    db_name = os.getenv("POSTGRES_DB")
    host = os.getenv("POSTGRES_HOST")
    port = int(os.getenv("POSTGRES_PORT"))
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    return f'postgresql://{user}:{password}@{host}:{port}/{db_name or ""}'


engine = sqlmodel.create_engine(get_dsn(), pool_size=30, max_overflow=20, echo=True)


def init_db():
    sqlmodel.SQLModel.metadata.create_all(engine)


def get_session() -> sqlmodel.Session:
    with sqlmodel.Session(engine) as session:
        yield session


@contextlib.contextmanager
def local_session() -> sqlmodel.Session:
    with sqlmodel.Session(engine) as session:
        yield session
