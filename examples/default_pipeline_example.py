#!/usr/bin/env python3
"""
Default Ingestion Pipeline Example

This script demonstrates how to use the DefaultIngestionPipeline with
both WhatsApp and Telegram ingestors.

The pipeline handles:
1. Loading and initializing all components for both ingestors
2. Tracking state separately for each ingestor
3. Fetching data from each ingestor based on its latest state
4. Processing the data through the appropriate preprocessor
5. Generating embeddings and storing in a vector database

Usage:
  python default_pipeline_example.py [--config-path CONFIG_PATH] [--ingestor-id INGESTOR_ID] [--full] [--verbose]
"""

import os
import sys
import asyncio
import argparse
import logging
from datetime import datetime, timezone

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ici.adapters.loggers import StructuredLogger
from ici.adapters.pipelines import DefaultIngestionPipeline


async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run the Default Ingestion Pipeline")
    parser.add_argument("--config-path", default="config.yaml", help="Path to configuration file")
    parser.add_argument("--ingestor-id", help="Specific ingestor ID to run (optional)")
    parser.add_argument("--full", action="store_true", help="Force a full ingestion run")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    # Set environment variable for config path
    os.environ["ICI_CONFIG_PATH"] = args.config_path
    
    # Setup logging
    logger = StructuredLogger(name="default_pipeline_example")
    
    # Set verbose logging if requested
    if args.verbose:
        # Configure root logger with more detail for debugging
        logging.basicConfig(level=logging.INFO)
        # Enable debug logs for aiohttp specifically
        logging.getLogger('aiohttp').setLevel(logging.DEBUG)
    
    try:
        # Create and initialize the pipeline
        pipeline = DefaultIngestionPipeline()
        await pipeline.initialize()
        
        # Run health check before ingestion
        health_info = await pipeline.healthcheck()
        logger.info({
            "action": "HEALTH_CHECK",
            "message": "Pipeline health check result",
            "data": health_info
        })
        
        if args.ingestor_id:
            # Run ingestion for a specific ingestor
            logger.info({
                "action": "RUN_SPECIFIC_INGESTOR",
                "message": f"Starting ingestion for {args.ingestor_id}",
                "data": {"ingestor_id": args.ingestor_id}
            })
            
            # Check if we should force a fresh start
            if args.full:
                # Reset the state to 0 for a full run
                logger.info({
                    "action": "RESET_STATE",
                    "message": f"Resetting state for {args.ingestor_id} to perform full ingestion"
                })
                pipeline.set_ingestor_state(
                    ingestor_id=args.ingestor_id,
                    last_timestamp=0,
                    additional_metadata={
                        "reset_time": datetime.now(timezone.utc).isoformat(),
                        "reset_reason": "Manual full ingestion requested"
                    }
                )
            
            # Run ingestion for the specific ingestor
            result = await pipeline.run_ingestion(args.ingestor_id)
            
            # Print results
            logger.info({
                "action": "INGESTION_RESULT",
                "message": f"Ingestion result for {args.ingestor_id}",
                "data": {
                    "success": result["success"],
                    "documents_processed": result.get("documents_processed", 0),
                    "errors": result.get("errors", []),
                    "duration": result.get("duration", 0)
                }
            })
            
            # Show the updated state
            state = pipeline.get_ingestor_state(args.ingestor_id)
            logger.info({
                "action": "UPDATED_STATE",
                "message": f"Updated state for {args.ingestor_id}",
                "data": state
            })
            
        else:
            # Run ingestion for all registered ingestors
            logger.info({
                "action": "RUN_ALL_INGESTORS",
                "message": "Starting ingestion for all registered ingestors"
            })
            
            await pipeline.start()
            
            logger.info({
                "action": "INGESTION_COMPLETE",
                "message": "Completed ingestion for all ingestors"
            })
        
        # Clean up resources
        await pipeline.close()
        
    except Exception as e:
        logger.error({
            "action": "PIPELINE_ERROR",
            "message": f"Error running default pipeline: {str(e)}",
            "data": {"error": str(e), "error_type": type(e).__name__}
        })
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 