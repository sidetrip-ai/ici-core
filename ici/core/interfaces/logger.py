from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class Logger(ABC):
    """
    Interface for logging functionality in the ICI framework.

    Provides standard methods for logging at different severity levels with a structured format.
    Each log entry should contain: action name, message, and optional data dictionary.
    """

    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the logger with configuration parameters.
        
        This method should be called after the logger instance is created,
        before any other methods are used. Configuration should be loaded from
        a central configuration source (e.g., config.yaml).
        
        Returns:
            None
        
        Raises:
            Exception: If initialization fails for any reason.
        """
        pass

    @abstractmethod
    def debug(self, log_data: Dict[str, Any]) -> None:
        """
        Log a debug message with structured data.

        Args:
            log_data: A dictionary with the structure:
                {
                    "action": "ACTION_NAME",     # The action or event being logged
                    "message": "MESSAGE TEXT",   # The log message
                    "data": {}                   # Optional additional data as a dictionary
                }
        """
        pass

    @abstractmethod
    def info(self, log_data: Dict[str, Any]) -> None:
        """
        Log an info message with structured data.

        Args:
            log_data: A dictionary with the structure:
                {
                    "action": "ACTION_NAME",     # The action or event being logged
                    "message": "MESSAGE TEXT",   # The log message
                    "data": {}                   # Optional additional data as a dictionary
                }
        """
        pass

    @abstractmethod
    def warning(self, log_data: Dict[str, Any]) -> None:
        """
        Log a warning message with structured data.

        Args:
            log_data: A dictionary with the structure:
                {
                    "action": "ACTION_NAME",     # The action or event being logged
                    "message": "MESSAGE TEXT",   # The log message
                    "data": {}                   # Optional additional data as a dictionary
                }
        """
        pass

    @abstractmethod
    def error(self, log_data: Dict[str, Any]) -> None:
        """
        Log an error message with structured data.

        Args:
            log_data: A dictionary with the structure:
                {
                    "action": "ACTION_NAME",     # The action or event being logged
                    "message": "MESSAGE TEXT",   # The log message
                    "data": {},                  # Optional additional data as a dictionary
                    "exception": Exception       # Optional exception object
                }
        """
        pass

    @abstractmethod
    def critical(self, log_data: Dict[str, Any]) -> None:
        """
        Log a critical message with structured data.

        Args:
            log_data: A dictionary with the structure:
                {
                    "action": "ACTION_NAME",     # The action or event being logged
                    "message": "MESSAGE TEXT",   # The log message
                    "data": {},                  # Optional additional data as a dictionary
                    "exception": Exception       # Optional exception object
                }
        """
        pass
