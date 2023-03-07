import datetime
from enum import Enum
from typing import Optional

import pydantic
import sqlmodel
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


class SQLBase(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)

    created_at: datetime.datetime = sqlmodel.Field(
        sa_column=sqlmodel.Column(
            sqlmodel.DateTime(timezone=True),
            nullable=False,
            server_default=sqlmodel.func.now(),
        )
    )


class Account(SQLBase, table=True):
    email: pydantic.EmailStr
    password: str
    github_personal_api_token: str

    repos: list["Repo"] = Relationship(
        back_populates="account", sa_relationship_kwargs={"cascade": "delete"}
    )


class AccountWrite(SQLModel):
    email: pydantic.EmailStr
    password: str
    github_personal_api_token: str


class Login(pydantic.BaseModel):
    email: pydantic.EmailStr
    password: str


class Repo(SQLBase, table=True):
    owner: str
    name: str

    account: Account = Relationship(
        back_populates="repos", sa_relationship_kwargs={"cascade": "delete"}
    )
    commits: list["Commit"] = Relationship(
        back_populates="repo", sa_relationship_kwargs={"cascade": "delete"}
    )
    account_id: int = sqlmodel.Field(foreign_key="account.id")

    # reporting_docker_services_names: list[str] = Field(default=['traigsession'], nullable=False, description="Названия сервисов, описанных в docker-compose.traig.yml, из которых будут поступать обновления метрик")
    reporting_docker_services_name: str = Field(default="traigsession", nullable=False)

    traig_compose_file_path_from_repo_root: str = Field(
        default="docker-compose.traig.yml", nullable=False
    )


class RepoWrite(pydantic.BaseModel):
    owner: str
    name: str


class Commit(SQLBase, table=True):
    __table_args__ = (
        UniqueConstraint("ref", "repo_id", name="repo_id_ref_constraint"),
    )
    ref: str
    committed_datetime: datetime.datetime
    message: str

    repo: Repo = Relationship(
        back_populates="commits", sa_relationship_kwargs={"cascade": "delete"}
    )
    repo_id: int = sqlmodel.Field(foreign_key="repo.id")

    processed: Optional[bool] = sqlmodel.Field(default=False)
    run_ok: Optional[bool] = sqlmodel.Field(default=None)
    json_run_result: Optional[dict] = sqlmodel.Field(
        sa_column=sqlmodel.Column(sqlmodel.JSON(), nullable=True)
    )
    run_error: Optional[str] = sqlmodel.Field(default=None)
    container_stdout: Optional[str] = sqlmodel.Field(default=None)
    container_stderr: Optional[str] = sqlmodel.Field(default=None)


class MetricUpdate(SQLBase, table=True):
    commit_id: int = Field(foreign_key="commit.id")

    data: Optional[dict] = sqlmodel.Field(
        sa_column=sqlmodel.Column(sqlmodel.JSON(), nullable=True)
    )


class MetricTypeEnum(str, Enum):
    value = "value"  # simply store latest value assigned
    max = "max"  # return maximum
    min = "min"  # return minimum
    sum = "sum"  # return sum
    mean = "mean"  # return mean
    mode = "mode"  # return mode
    median = "median"  # return mode
    count = "count"  # return number of updates of the metric (actual update values does not matter)


class ClientMetricsConfig(pydantic.BaseModel):
    data: dict[str, MetricTypeEnum]


class ClientMetricsUpdate(pydantic.BaseModel):
    data: dict[str, int | float | str]


class RunConfig(SQLBase, table=True):
    client_ip: str = Field(unique=True, nullable=False)
    commit_id: int = Field(foreign_key="commit.id")

    metrics_config: Optional[dict[str, MetricTypeEnum]] = sqlmodel.Field(
        sa_column=sqlmodel.Column(sqlmodel.JSON(), nullable=True)
    )


# for name, item in list(globals().items()):
#     if not isinstance(item, pydantic.main.ModelMetaclass):
#         continue
#     item.update_forward_refs()
