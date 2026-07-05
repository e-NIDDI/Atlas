"""Logging configuration for Jarvis."""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from jarvis.config import config


def setup_logger(
    name: str = "jarvis",
    log_dir: Optional[Path] = None,
    level: str = "INFO"
) -> logging.Logger:
    """
    Set up and configure the Jarvis logger.
    
    Args:
        name: Logger name
        log_dir: Directory for log files
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    if log_dir is None:
        log_dir = config.log_dir
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Prevent adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_formatter = logging.Formatter(
        '%(levelname)-8s | %(message)s'
    )
    
    # Console handler (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler for general logs
    log_file = log_dir / f"jarvis_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Error file handler (errors only)
    error_file = log_dir / f"jarvis_errors_{datetime.now().strftime('%Y%m%d')}.log"
    error_handler = logging.FileHandler(error_file, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)
    
    return logger


# Global logger instance
logger = setup_logger()