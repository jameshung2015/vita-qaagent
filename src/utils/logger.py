"""Logging configuration."""

import logging
import sys
from pathlib import Path
from datetime import datetime


def setup_logger(
    name: str = "qaagent",
    level: int = logging.INFO,
    log_dir: str = "outputs/logs",
    console: bool = True,
) -> logging.Logger:
    """
    Setup logger with file and console handlers.

    Args:
        name: Logger name
        level: Logging level
        log_dir: Directory for log files
        console: Whether to add console handler

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )
    simple_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )

    # File handler
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_handler = logging.FileHandler(
        log_path / f"{name}_{timestamp}.log",
        encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)

    return logger
