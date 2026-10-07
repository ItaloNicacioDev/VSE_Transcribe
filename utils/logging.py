"""Logging utilities for VSE_Transcribe.

Provides consistent logging across the addon with Blender integration.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import bpy


# Module-level logger
_logger: logging.Logger | None = None


def get_logger(name: str = "VSE_Transcribe") -> logging.Logger:
    """Get or create the module logger.

    Args:
        name: Logger name (default: "VSE_Transcribe").

    Returns:
        Configured logger instance.
    """
    global _logger
    if _logger is None:
        _logger = logging.getLogger(name)
        _logger.setLevel(logging.DEBUG)

        # Avoid duplicate handlers
        if not _logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                "[%(name)s] %(levelname)s: %(message)s"
            )
            handler.setFormatter(formatter)
            _logger.addHandler(handler)

    return _logger


def set_log_level(level: int | str) -> None:
    """Set the log level for the VSE_Transcribe logger.

    Args:
        level: Logging level (e.g., logging.DEBUG, "INFO", "WARNING").
    """
    logger = get_logger()
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)


def log_info(message: str) -> None:
    """Log an info message."""
    get_logger().info(message)


def log_warning(message: str) -> None:
    """Log a warning message."""
    get_logger().warning(message)


def log_error(message: str) -> None:
    """Log an error message."""
    get_logger().error(message)


def log_debug(message: str) -> None:
    """Log a debug message."""
    get_logger().debug(message)


def log_exception(message: str) -> None:
    """Log an exception with traceback."""
    get_logger().exception(message)


# Blender-specific reporting (when bpy is available)
def report_info(message: str) -> None:
    """Report info via Blender's report system if available, else log."""
    log_info(message)
    try:
        import bpy
        # Can't call self.report() from here, but can print to console
        print(f"[VSE_Transcribe] INFO: {message}")
    except ImportError:
        pass


def report_warning(message: str) -> None:
    """Report warning via Blender's report system if available, else log."""
    log_warning(message)
    try:
        import bpy
        print(f"[VSE_Transcribe] WARNING: {message}")
    except ImportError:
        pass


def report_error(message: str) -> None:
    """Report error via Blender's report system if available, else log."""
    log_error(message)
    try:
        import bpy
        print(f"[VSE_Transcribe] ERROR: {message}")
    except ImportError:
        pass


class OperatorLogger:
    """Context manager for operator logging with Blender report integration.

    Usage:
        def execute(self, context):
            with OperatorLogger(self) as log:
                log.info("Starting...")
                log.warning("Something odd")
                log.error("Failed!")
    """

    def __init__(self, operator: "bpy.types.Operator | None" = None):
        self.operator = operator
        self.logger = get_logger()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.error(f"Operator failed: {exc_val}")
        return False

    def info(self, message: str) -> None:
        self.logger.info(message)
        if self.operator:
            self.operator.report({"INFO"}, message)

    def warning(self, message: str) -> None:
        self.logger.warning(message)
        if self.operator:
            self.operator.report({"WARNING"}, message)

    def error(self, message: str) -> None:
        self.logger.error(message)
        if self.operator:
            self.operator.report({"ERROR"}, message)

    def debug(self, message: str) -> None:
        self.logger.debug(message)