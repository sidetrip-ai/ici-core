#!/usr/bin/env python
"""
Example script demonstrating Telegram ingestion pipeline.

This script:
1. Loads configuration from config.yaml
2. Initializes the Telegram ingestion pipeline
3. Registers an ingestor ID if not already registered
4. Runs a single ingestion

Usage:
    python scheduled_telegram_pipeline_example.py [--register]
"""

import os
import sys
import argparse
import asyncio

from ici.adapters.pipelines.telegram import TelegramIngestionPipeline
from ici.adapters.loggers import StructuredLogger
from ici.core.exceptions import IngestionPipelineError

# Set up logger
logger = StructuredLogger(name="telegram_example")

async def initialize_pipeline() -> TelegramIngestionPipeline:
    """
    Initialize the Telegram ingestion pipeline.
    
    Returns:
        TelegramIngestionPipeline: The initialized pipeline
    """
    pipeline = TelegramIngestionPipeline(logger_name="telegram_example")
    
    logger.info({
        "action": "PIPELINE_INIT_START",
        "message": "Initializing Telegram ingestion pipeline"
    })
    
    await pipeline.initialize()
    
    logger.info({
        "action": "PIPELINE_INIT_COMPLETE",
        "message": "Telegram ingestion pipeline initialized successfully"
    })
    
    return pipeline

async def register_ingestor(pipeline: TelegramIngestionPipeline, ingestor_id: str) -> None:
    """
    Register an ingestor with the pipeline if it doesn't exist.
    
    Args:
        pipeline: The initialized pipeline
        ingestor_id: ID for the ingestor to register
    """
    # Check if ingestor already exists
    existing_state = pipeline.get_ingestor_state(ingestor_id)
    if existing_state.get("last_timestamp", 0) > 0:
        logger.info({
            "action": "INGESTOR_ALREADY_REGISTERED",
            "message": f"Ingestor {ingestor_id} is already registered",
            "data": {"ingestor_id": ingestor_id}
        })
        return
    
    # Register ingestor
    logger.info({
        "action": "INGESTOR_REGISTERING",
        "message": f"Registering ingestor {ingestor_id}",
        "data": {"ingestor_id": ingestor_id}
    })
    
    pipeline.register_ingestor(
        ingestor_id=ingestor_id,
        ingestor_config={}  # No special config needed
    )
    
    logger.info({
        "action": "INGESTOR_REGISTERED",
        "message": f"Ingestor {ingestor_id} registered successfully",
        "data": {"ingestor_id": ingestor_id}
    })

async def run_ingestion(pipeline: TelegramIngestionPipeline) -> None:
    """
    Run a single ingestion.
    
    Args:
        pipeline: The initialized pipeline
    """
    logger.info({
        "action": "INGESTION_START",
        "message": "Starting ingestion"
    })
    
    # Use the now-async start method directly
    result = await pipeline.start()
    
    logger.info({
        "action": "INGESTION_COMPLETE",
        "message": "Ingestion complete",
        "data": {
            "success": result.get("success", False),
            "documents_processed": result.get("documents_processed", 0),
            "duration": result.get("duration", 0)
        }
    })

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Telegram ingestion pipeline example")
    parser.add_argument("--register", action="store_true", help="Register the ingestor if not already registered")
    
    args = parser.parse_args()
    
    try:
        # Initialize the pipeline
        pipeline = await initialize_pipeline()
        
        # Register ingestor if requested
        if args.register:
            await register_ingestor(pipeline, "telegram_ingestor")
        
        # Run ingestion
        await run_ingestion(pipeline)
        
    except IngestionPipelineError as e:
        logger.error({
            "action": "PIPELINE_ERROR",
            "message": f"Pipeline error: {str(e)}",
            "data": {"error": str(e)}
        })
        sys.exit(1)
    except Exception as e:
        logger.error({
            "action": "UNEXPECTED_ERROR",
            "message": f"Unexpected error: {str(e)}",
            "data": {"error": str(e), "error_type": type(e).__name__}
        })
        sys.exit(1)

if __name__ == "__main__":
    # Ensure ICI_CONFIG_PATH is set
    if not os.environ.get("ICI_CONFIG_PATH"):
        os.environ["ICI_CONFIG_PATH"] = os.path.join(os.getcwd(), "config.yaml")
    
    # Run the main async function
    asyncio.run(main()) 