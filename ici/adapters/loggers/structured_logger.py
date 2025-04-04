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
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from logtail import LogtailHandler

from ici.core.interfaces import Logger
from ici.core.exceptions import LoggerError
from ici.utils.config import get_component_config


class DateTimeEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that can handle datetime objects.
    
    This encoder converts datetime objects to ISO 8601 format strings,
    which are standard for JSON and easily parsed by most systems.
    """
    def default(self, obj):
        if isinstance(obj, datetime):
            # Convert datetime to ISO format with timezone info
            return obj.isoformat()
        # Let the base class handle other types or raise TypeError
        return super().default(obj)


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
        self.name = name
        self.level = level
        self.log_file = log_file
        self.console_output = console_output
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        self._is_initialized = False
        
        self.initialize()
    
    def initialize(self) -> None:
        """
        Initialize the logger with configuration parameters.
        
        This method loads logger configuration from config.yaml and reconfigures
        the logger accordingly.
        
        Returns:
            None
        
        Raises:
            LoggerError: If initialization fails for any reason.
        """
        try:
            # Load logger configuration from new path
            logger_config = get_component_config("loggers.structured_logger", self._config_path) or {}
            
            # Get configuration values with defaults from constructor
            self.level = logger_config.get("level", self.level)
            self.log_file = logger_config.get("log_file", self.log_file)
            self.console_output = logger_config.get("console_output", self.console_output)
            
            # Special handling for betterstack integration
            self.use_betterstack = logger_config.get("use_betterstack", False)
            self.source_token = os.environ.get("SOURCE_TOKEN", logger_config.get("source_token", ""))
            self.host = os.environ.get("INGESTION_HOST", logger_config.get("host", ""))
            
            # Reconfigure the logger
            self.logger = logging.getLogger(self.name)
            self.logger.setLevel(self._LEVEL_MAP.get(self.level.upper(), logging.INFO))
            
            # Clear existing handlers
            self.logger.handlers = []
            
            # Create formatter with minimal formatting since we'll format in the log methods
            formatter = logging.Formatter("%(message)s")
            
            # Add betterstack handler if configured
            if self.use_betterstack and self.source_token and self.host:
                try:
                    handler = LogtailHandler(
                        source_token=self.source_token,
                        host=f"https://{self.host}",
                    )
                    self.logger.addHandler(handler)
                except Exception as e:
                    print(f"Failed to initialize Betterstack logger: {str(e)}", file=sys.stderr)
            
            # Add console handler if requested
            if self.console_output:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setFormatter(formatter)
                self.logger.addHandler(console_handler)
            
            # Add file handler if log_file is provided
            if self.log_file:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(os.path.abspath(self.log_file)), exist_ok=True)
                file_handler = logging.FileHandler(self.log_file)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            
            self._is_initialized = True
            
            self.info({
                "action": "LOGGER_INITIALIZE",
                "message": f"Logger '{self.name}' initialized with configuration",
                "data": {
                    "logger_type": "StructuredLogger",
                    "log_level": self.level,
                    "console_output": self.console_output,
                    "log_file": self.log_file,
                    "use_betterstack": self.use_betterstack
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

            # Convert to JSON using custom encoder for datetime objects
            json_str = json.dumps(log_entry, cls=DateTimeEncoder)
            
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
            print(f"Original log data: {log_data}", file=sys.stderr)
            return json.dumps(
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "ERROR",
                    "message": error,
                    "original_message": str(log_data),
                },
                cls=DateTimeEncoder  # Use custom encoder even in error case
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
