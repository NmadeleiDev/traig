import logging

from api import init_api
from db import init_db


def init_logging():
    logging.basicConfig(
        format="%(asctime)s %(levelname)s ~ %(funcName)s: %(message)s",
        datefmt="%m/%d/%Y %H:%M:%S%z :",
        level=logging.DEBUG,
    )


def init_fastapi():
    init_logging()
    init_db()
    return init_api()
