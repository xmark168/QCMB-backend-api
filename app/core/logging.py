import logging
from uvicorn.config import LOGGING_CONFIG

def init_logging() -> None:
    logging.config.dictConfig(LOGGING_CONFIG)