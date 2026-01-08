from led_system_monitor import main
import os
import logging
import re
import sys
import importlib
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

level = logging.WARNING
if os.getenv("LOG_LEVEL", "").lower() == "debug":
    level = logging.DEBUG
elif os.getenv("LOG_LEVEL", "").lower() == "error":
    level = logging.ERROR
elif os.getenv("LOG_LEVEL", "").lower() == "info":
    level = logging.INFO

logging.basicConfig(
    level=level,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

log = logging.getLogger(__name__)

if __name__ == "__main__":
    log.debug("Calling main")
    main(sys.argv)