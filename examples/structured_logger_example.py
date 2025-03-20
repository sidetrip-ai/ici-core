#!/usr/bin/env python
"""
Example script demonstrating the use of the StructuredLogger implementation.

This script shows how to use the StructuredLogger to create well-structured
log entries with action names, messages, and additional data.
"""

import sys
import os
import time

# Add the parent directory to the path to allow importing the ici package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ici.adapters.loggers import StructuredLogger


def example_function():
    """Example function that demonstrates logging various events."""
    # Create a logger that logs to both console and file
    logger = StructuredLogger(
        name="example",
        level="DEBUG",
        log_file="examples/logs/structured.log",
        console_output=True,
    )

    # Log a simple debug message
    logger.debug(
        {
            "action": "FUNCTION_START",
            "message": "Starting example function",
            "data": {"timestamp": time.time()},
        }
    )

    # Log an info message with additional data
    logger.info(
        {
            "action": "CONFIG_LOADED",
            "message": "Configuration loaded successfully",
            "data": {
                "config_file": "config.json",
                "settings": {"max_connections": 100, "timeout": 30},
            },
        }
    )

    # Log a warning message
    logger.warning(
        {
            "action": "RESOURCE_LOW",
            "message": "System resources are running low",
            "data": {"memory_usage": "85%", "cpu_usage": "78%"},
        }
    )

    # Log an error message with exception
    try:
        # Simulate an error
        result = 1 / 0
    except Exception as e:
        logger.error(
            {
                "action": "CALCULATION_FAILED",
                "message": "Failed to perform calculation",
                "data": {"operation": "division", "parameters": [1, 0]},
                "exception": e,
            }
        )

    # Log a critical message
    logger.critical(
        {
            "action": "SERVICE_UNAVAILABLE",
            "message": "Critical dependency unavailable",
            "data": {"service": "database", "attempts": 5, "retry_in": 60},
        }
    )

    # Log the end of the function
    logger.info(
        {
            "action": "FUNCTION_END",
            "message": "Example function completed",
            "data": {"duration_ms": 123},
        }
    )


def database_example():
    """Example function demonstrating structured logging for database operations."""
    logger = StructuredLogger(name="example.database")

    # Log a database connection
    logger.info(
        {
            "action": "DB_CONNECT",
            "message": "Connected to database",
            "data": {
                "host": "localhost",
                "database": "users",
                "connection_id": "conn-123456",
            },
        }
    )

    # Log a database query
    logger.debug(
        {
            "action": "DB_QUERY",
            "message": "Executing database query",
            "data": {
                "query": "SELECT * FROM users WHERE status = ?",
                "parameters": ["active"],
                "query_id": "q-987654",
            },
        }
    )

    # Log a slow query warning
    logger.warning(
        {
            "action": "DB_SLOW_QUERY",
            "message": "Query execution time exceeded threshold",
            "data": {
                "query_id": "q-987654",
                "execution_time_ms": 1520,
                "threshold_ms": 1000,
            },
        }
    )

    # Log a database disconnect
    logger.info(
        {
            "action": "DB_DISCONNECT",
            "message": "Disconnected from database",
            "data": {"connection_id": "conn-123456", "duration_s": 35},
        }
    )


if __name__ == "__main__":
    # Create the logs directory if it doesn't exist
    os.makedirs("examples/logs", exist_ok=True)

    # Run the examples
    print("Running structured logging examples...")
    example_function()
    database_example()

    print("\nExamples completed. Check logs directory for file output.")
    print("The logs are in JSON format for easy parsing and analysis.")
