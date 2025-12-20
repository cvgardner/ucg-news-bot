"""Logging configuration for UCG News Bot"""
import logging
import sys
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for Google Cloud Run structured logging.

    Outputs logs in JSON format compatible with Google Cloud Logging.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add any extra fields that were passed
        if hasattr(record, "extra_fields"):
            log_obj.update(record.extra_fields)

        # Add source location
        log_obj["sourceLocation"] = {
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName
        }

        return json.dumps(log_obj)


def setup_logger(name: str, level: Optional[str] = None, force_json: bool = False) -> logging.Logger:
    """
    Setup and configure a logger with standardized formatting.

    Uses JSON structured logging when running in Google Cloud Run,
    or human-readable format otherwise.

    Args:
        name: Name of the logger (typically __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        force_json: Force JSON output even if not in GCP

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Set log level
    log_level = getattr(logging, level.upper() if level else "INFO")
    logger.setLevel(log_level)

    # Prevent duplicate handlers if logger already exists
    if logger.handlers:
        return logger

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # Detect if running in Google Cloud Run
    is_gcp = os.getenv("K_SERVICE") is not None or force_json

    if is_gcp:
        # Use structured JSON logging for GCP
        formatter = StructuredFormatter()
    else:
        # Use human-readable format for local development
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get an existing logger or create a new one.

    Args:
        name: Name of the logger

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: int, message: str, **context: Any) -> None:
    """
    Log a message with additional structured context fields.

    Context fields will appear as top-level fields in JSON logs,
    and will be appended to the message in text logs.

    Args:
        logger: Logger instance
        level: Log level (logging.INFO, logging.ERROR, etc.)
        message: Log message
        **context: Additional context fields

    Example:
        log_with_context(logger, logging.INFO, "Post fetched",
                        user_id="123", post_id="456", url="https://...")
    """
    # Create a log record with extra fields
    if context:
        # For structured logging, attach context as extra_fields
        extra = {"extra_fields": context}
        # For text logging, append context to message
        if not os.getenv("K_SERVICE"):
            context_str = ", ".join(f"{k}={v}" for k, v in context.items())
            message = f"{message} [{context_str}]"
        logger.log(level, message, extra=extra)
    else:
        logger.log(level, message)
