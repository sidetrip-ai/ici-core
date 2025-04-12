"""
Structured Logger implementation providing well-formatted logs.

This implementation uses Python's built-in logging module to generate structured logs
that include action name, message, source information, and additional data.
"""

import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict, Optional

class StructuredLogger:
    """Simple structured logger implementation."""
    
    def __init__(self, name: str = "ici"):
        """Initialize the logger."""
        self.name = name
        self.logger = logging.getLogger(name)
        
        # Set up basic configuration if no handlers exist
        if not self.logger.handlers:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                stream=sys.stdout
            )
    
    def _log(self, level: int, message: str, **kwargs) -> None:
        """Internal logging method."""
        if isinstance(message, dict):
            message = json.dumps(message)
        self.logger.log(level, message, **kwargs)
    
    def debug(self, message: Any) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, message)
    
    def info(self, message: Any) -> None:
        """Log info message."""
        self._log(logging.INFO, message)
    
    def warning(self, message: Any) -> None:
        """Log warning message."""
        self._log(logging.WARNING, message)
    
    def error(self, message: Any) -> None:
        """Log error message."""
        self._log(logging.ERROR, message)
    
    def critical(self, message: Any) -> None:
        """Log critical message."""
        self._log(logging.CRITICAL, message)
