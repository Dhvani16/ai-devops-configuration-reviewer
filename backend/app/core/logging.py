"""Logging configuration that avoids emitting credentials or request bodies."""

import logging


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
