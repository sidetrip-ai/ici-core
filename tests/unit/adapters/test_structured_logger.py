"""
Unit tests for the StructuredLogger implementation.
"""

import json
import os
import tempfile
from typing import Dict, Any

import pytest

from ici.adapters.loggers import StructuredLogger


class TestStructuredLogger:
    """Test cases for the StructuredLogger."""

    def test_initialization(self):
        """Test logger initialization."""
        logger = StructuredLogger(name="test_logger")
        assert logger.name == "test_logger"
        assert logger.logger.level == 20  # INFO level

    def test_log_levels(self):
        """Test all log levels work correctly."""
        logger = StructuredLogger(name="test_logger")

        # These should not raise exceptions
        logger.debug({"action": "TEST", "message": "Debug message"})
        logger.info({"action": "TEST", "message": "Info message"})
        logger.warning({"action": "TEST", "message": "Warning message"})
        logger.error({"action": "TEST", "message": "Error message"})
        logger.critical({"action": "TEST", "message": "Critical message"})

    def test_log_to_file(self):
        """Test logging to a file."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Create logger with file output
            logger = StructuredLogger(
                name="test_file_logger",
                level="INFO",
                log_file=tmp_path,
                console_output=False,
            )

            # Log a message
            test_message = "File logging test"
            logger.info({"action": "FILE_TEST", "message": test_message})

            # Verify file contains the log
            with open(tmp_path, "r") as f:
                content = f.read()
                log_data = json.loads(content)
                assert log_data["action"] == "FILE_TEST"
                assert log_data["message"] == test_message
                assert log_data["logger"] == "test_file_logger"

        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_structured_data(self):
        """Test logging with structured data."""
        # Create a temporary file to capture log output
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Create logger
            logger = StructuredLogger(
                name="test_data_logger", log_file=tmp_path, console_output=False
            )

            # Log with structured data
            test_data = {
                "user_id": 123,
                "items": ["apple", "banana"],
                "metadata": {"source": "test"},
            }

            logger.info(
                {
                    "action": "DATA_TEST",
                    "message": "Testing structured data",
                    "data": test_data,
                }
            )

            # Verify the structured data was logged correctly
            with open(tmp_path, "r") as f:
                content = f.read()
                log_data = json.loads(content)
                assert log_data["action"] == "DATA_TEST"
                assert log_data["data"] == test_data

        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_exception_logging(self):
        """Test logging exceptions."""
        # Create a temporary file to capture log output
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Create logger
            logger = StructuredLogger(
                name="test_exception_logger", log_file=tmp_path, console_output=False
            )

            # Create and log an exception
            try:
                raise ValueError("Test exception")
            except ValueError as e:
                logger.error(
                    {
                        "action": "EXCEPTION_TEST",
                        "message": "Testing exception logging",
                        "exception": e,
                    }
                )

            # Verify the exception was logged correctly
            with open(tmp_path, "r") as f:
                content = f.read()
                log_data = json.loads(content)
                assert log_data["action"] == "EXCEPTION_TEST"
                assert "exception" in log_data
                assert log_data["exception"]["type"] == "ValueError"
                assert log_data["exception"]["message"] == "Test exception"
                assert isinstance(log_data["exception"]["traceback"], list)

        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
