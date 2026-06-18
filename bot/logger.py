"""Small logging helper with a consistent format."""

import logging
import sys


def get_logger(name: str = "fast-bnb-bot", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:  # already configured
        return logger
    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-5s | %(message)s",
                          datefmt="%H:%M:%S")
    )
    logger.addHandler(handler)
    return logger
