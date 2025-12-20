import logging
import os

logger = logging.getLogger(__name__)
LOGLEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOGLEVEL, format="%(asctime)s %(message)s")