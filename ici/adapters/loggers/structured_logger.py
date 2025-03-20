"""
Structured Logger implementation providing well-formatted logs.

This implementation uses Python's built-in logging module to generate structured logs
that include action name, message, source information, and additional data.
"""

import logging
import sys
import os
import json
import inspect
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from logtail import LogtailHandler

from ici.core.interfaces import Logger
from ici.core.exceptions import LoggerError


class StructuredLogger(Logger):
    """
    Implementation of the Logger interface that provides structured logging.

    Features:
    - Structured log format with action, message, and data
    - Source information including function name, module, and line number
    - Timestamp and log level
    - Exception handling with traceback
    - Console and file outputs
    - Color-coded logs (red for errors, white for info, grey for debug, yellow for warnings)
    """

    # Log level mapping
    _LEVEL_MAP = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    
    # ANSI color codes for terminal output
    _COLORS = {
        "DEBUG": "\033[90m",     # Grey
        "INFO": "\033[37m",      # White
        "WARNING": "\033[93m",   # Yellow
        "ERROR": "\033[91m",     # Red
        "CRITICAL": "\033[91m",  # Red
        "RESET": "\033[0m"       # Reset to default
    }

    def __init__(
        self,
        name: str = "ici",
        level: str = "INFO",
        log_file: Optional[str] = None,
        console_output: bool = True,
    ):
        """
        Initialize the StructuredLogger.

        Args:
            name: The logger name
            level: The log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional path to log file
            console_output: Whether to output logs to console
        """
        try:
            # Create logger
            handler = LogtailHandler(
                source_token='$SOURCE_TOKEN', 
                host='https://$INGESTING_HOST',
            )
            self.logger = logging.getLogger(name)
            self.logger.setLevel(self._LEVEL_MAP.get(level.upper(), logging.WARNING))

            # Clear existing handlers
            self.logger.handlers = []
            # self.logger.addHandler(handler)

            # Create formatter with minimal formatting since we'll format in the log methods
            formatter = logging.Formatter("%(message)s")

            # Add console handler if requested
            if console_output:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)

            # Add file handler if log_file is provided
            if log_file:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)

            self.name = name

        except Exception as e:
            error_msg = f"Failed to initialize logger: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise LoggerError(error_msg) from e
    
    async def initialize(self) -> None:
        """
        Initialize the logger with configuration parameters.
        
        This method is implemented to satisfy the Logger interface requirements.
        For StructuredLogger, most initialization happens in the constructor,
        so this method serves as a hook for any async initialization steps.
        
        Returns:
            None
        
        Raises:
            LoggerError: If initialization fails for any reason.
        """
        try:
            self.info({
                "action": "LOGGER_INITIALIZE",
                "message": f"Logger '{self.name}' initialized",
                "data": {
                    "logger_type": "StructuredLogger",
                    "log_level": self.logger.level
                }
            })
            return None
        except Exception as e:
            error_msg = f"Failed to initialize logger: {str(e)}"
            print(error_msg, file=sys.stderr)
            raise LoggerError(error_msg) from e

    def _format_log(self, log_data: Dict[str, Any], level: str) -> str:
        """
        Format the log data as a structured string.

        Args:
            log_data: The log data dictionary
            level: The log level name

        Returns:
            str: The formatted log string
        """
        try:
            # Extract and validate required fields
            action = log_data.get("action", "UNDEFINED")
            message = log_data.get("message", "")
            data = log_data.get("data", {})

            # Get source information (caller's frame)
            frame = (
                inspect.currentframe().f_back.f_back
            )  # Skip the logger method and this _format_log method
            function_name = frame.f_code.co_name
            module_name = frame.f_globals.get("__name__", "unknown")
            line_number = frame.f_lineno
            source = f"{module_name}.{function_name}:{line_number}"

            # Create structured log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": level,
                "source": source,
                "action": action,
                "message": message,
                "logger": self.name,
            }

            # Add data if present
            if data:
                log_entry["data"] = data

            # Add exception if present
            exception = log_data.get("exception")
            if exception and level in ("ERROR", "CRITICAL"):
                log_entry["exception"] = {
                    "type": type(exception).__name__,
                    "message": str(exception),
                    "traceback": traceback.format_exc().split("\n"),
                }

            # Convert to JSON
            json_str = json.dumps(log_entry)
            
            # Add color codes for console output
            if sys.stdout.isatty():  # Only add colors when outputting to a terminal
                color_code = self._COLORS.get(level, "")
                reset_code = self._COLORS["RESET"]
                return f"{color_code}{json_str}{reset_code}"
            return json_str

        except Exception as e:
            # Fallback if formatting fails
            error = f"ERROR formatting log: {str(e)}"
            print(error, file=sys.stderr)
            return json.dumps(
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "ERROR",
                    "message": error,
                    "original_message": str(log_data),
                }
            )

    def debug(self, log_data: Dict[str, Any]) -> None:
        """Log a debug message with structured data."""
        self.logger.debug(self._format_log(log_data, "DEBUG"))

    def info(self, log_data: Dict[str, Any]) -> None:
        """Log an info message with structured data."""
        self.logger.info(self._format_log(log_data, "INFO"))

    def warning(self, log_data: Dict[str, Any]) -> None:
        """Log a warning message with structured data."""
        self.logger.warning(self._format_log(log_data, "WARNING"))

    def error(self, log_data: Dict[str, Any]) -> None:
        """Log an error message with structured data."""
        self.logger.error(self._format_log(log_data, "ERROR"))

    def critical(self, log_data: Dict[str, Any]) -> None:
        """Log a critical message with structured data."""
        self.logger.critical(self._format_log(log_data, "CRITICAL"))
