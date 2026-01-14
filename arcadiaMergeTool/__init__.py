import logging
import os

LOGLEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOGLEVEL, format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL_MERGER', logging.getLevelName(logger.getEffectiveLevel()).upper()))


def getLogger(name: str):
    name = name.replace(".", "_")
    log = logging.getLogger(name)
    log.parent = logger
    log.setLevel(os.environ.get(f"LOG_LEVEL_{name.upper()}", logging.getLevelName(logger.getEffectiveLevel()).upper()))

    return log