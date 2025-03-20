#!/usr/bin/env python
"""
Test script for Telegram session validation and generation.

This script demonstrates the use of the TelegramIngestor with its
built-in session validation and generation capabilities.
"""

import os
import sys
import asyncio
import argparse

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ici.adapters.ingestors.telegram import TelegramIngestor
from ici.adapters.loggers import StructuredLogger


async def main():
    """Test the TelegramIngestor with session handling."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test Telegram session handling")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    args = parser.parse_args()
    
    # Set environment variable for config path
    os.environ["ICI_CONFIG_PATH"] = args.config
    
    # Ensure config file exists
    if not os.path.exists(args.config):
        print(f"Config file not found: {args.config}")
        print(f"Please copy config.example.yaml to {args.config} and update with your credentials.")
        return
    
    # Create logger
    logger = StructuredLogger(name="telegram_test")
    logger.info({
        "action": "TEST_START",
        "message": "Starting Telegram session test"
    })
    
    # Create ingestor
    ingestor = TelegramIngestor(logger_name="telegram_test")
    
    try:
        # Initialize ingestor (this will validate or generate the session)
        await ingestor.initialize()
        
        # Run health check
        health_result = ingestor.healthcheck()
        
        # Check if health_result is a coroutine (async context)
        if asyncio.iscoroutine(health_result):
            logger.info({
                "action": "HEALTH_CHECK_ASYNC",
                "message": "Health check returned coroutine - awaiting result"
            })
            health = await health_result
        else:
            health = health_result
        
        if health["healthy"]:
            print(f"\n✅ Connection successful! Logged in as: {health['details'].get('name', 'Unknown')}")
            logger.info({
                "action": "HEALTH_CHECK_SUCCESS",
                "message": "Telegram connection is healthy",
                "data": health
            })
        else:
            print(f"\n❌ Connection failed: {health['message']}")
            logger.error({
                "action": "HEALTH_CHECK_FAILED",
                "message": "Telegram connection is not healthy",
                "data": health
            })
    
    except Exception as e:
        logger.error({
            "action": "TEST_ERROR",
            "message": f"Test failed: {str(e)}",
            "data": {
                "exception": str(e),
                "exception_type": type(e).__name__
            }
        })
        print(f"\n❌ Error: {str(e)}")
    
    finally:
        # Clean up
        if ingestor._client and ingestor._is_connected:
            await ingestor._disconnect()
        
        logger.info({
            "action": "TEST_COMPLETE",
            "message": "Telegram session test completed"
        })


if __name__ == "__main__":
    asyncio.run(main()) 