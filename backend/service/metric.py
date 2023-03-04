import logging

import sqlmodel
from exception import ClientFailure, ServerFailure
from model import (
    ClientMetricsConfig,
    ClientMetricsUpdate,
    MetricTypeEnum,
    MetricUpdate,
    RunConfig,
)
from sqlmodel import Session


def save_metrics_config(metrics: ClientMetricsConfig, ip: str, session: Session):
    run_config = get_run_config_by_client_ip(ip, session)
    logging.debug(
        f"got init for metrics: {metrics.data} from ip={ip}, "
        f"resolved commit_id={run_config.commit_id}"
    )

    run_config.metrics_config = metrics.data
    session.add(run_config)
    session.commit()


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def get_run_config_by_client_ip(ip: str, session: Session) -> RunConfig:
    run_config = session.exec(
        sqlmodel.select(RunConfig).where(RunConfig.client_ip == ip)
    ).first()
    if not run_config:
        raise ServerFailure(f"unknown client ip: {ip}")

    return run_config


def add_metric_update(metrics: ClientMetricsUpdate, ip: str, session: Session):
    run_config = get_run_config_by_client_ip(ip, session)
    logging.debug(
        f"got update for metrics: {metrics.data} from ip={ip}, "
        f"resolved commit_id={run_config.commit_id}"
    )

    if not run_config.metrics_config:
        raise ClientFailure(
            f"trying to update metrics for commit_id={run_config.commit_id} before init. "
            f"Must call /metric/init first."
        )

    # На самом деле хз, нужна ли вообще эта проверка. Мб просто игнорить невалидные значения при подсчете результата.
    for metric_name, metric_value in metrics.data.items():
        if metric_name not in run_config.metrics_config.keys():
            raise ClientFailure(
                f'metric "{metric_name}" was not defined during init, aborting update'
            )

        if run_config.metrics_config[metric_name] in (
            MetricTypeEnum.max,
            MetricTypeEnum.min,
            MetricTypeEnum.mean,
            MetricTypeEnum.median,
        ) and not is_number(metric_value):
            raise ClientFailure(
                f'value for metric "{metric_name}" of type "{run_config.metrics_config[metric_name]}"'
                f' must be a number, but it is "{metric_value}"'
            )

    update = MetricUpdate(commit_id=run_config.commit_id, data=metrics.data)

    session.add(update)
    session.commit()
