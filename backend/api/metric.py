from db import local_session
from fastapi import APIRouter, Request, status
from model import ClientMetricsConfig, ClientMetricsUpdate
from service.metric import add_metric_update, save_metrics_config

router = APIRouter(
    prefix="/metric",
    tags=["Operating metrics"],
)


@router.post(
    "/init",
    status_code=status.HTTP_200_OK,
)
def init_metrics_for_session(request: Request, metrics: ClientMetricsConfig):
    with local_session() as session:
        save_metrics_config(metrics, request.client.host, session)


@router.post(
    "/update",
    status_code=status.HTTP_200_OK,
)
def update_metrics_for_session(request: Request, metrics: ClientMetricsUpdate):
    with local_session() as session:
        add_metric_update(metrics, request.client.host, session)
