"""Centralized logging configuration utilities."""

import logging
from pathlib import Path
from typing import Optional


def setup_logging(debug: bool = False, log_file: Optional[Path] = None) -> None:
    """Configure console/file logging for benchmark runs.

    Args:
        debug: If True, emit DEBUG logs to console.
        log_file: Optional path for a full DEBUG log file.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Reset existing handlers so setup can be called more than once.
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    console_level = logging.DEBUG if debug else logging.INFO
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(console_handler)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root_logger.addHandler(file_handler)
