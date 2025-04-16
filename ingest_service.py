"""
Standalone service for data ingestion.

This script runs a standalone ingestion service using 
the specialized IngestOrchestrator and IngestController.
"""

import asyncio
import os
import signal
import sys
import traceback

from ici.adapters.controller.ingest_controller import IngestController
from ici.adapters.loggers.structured_logger import StructuredLogger

logger = StructuredLogger(name="ingest_service")

async def main():
    """
    Main entry point for the ingestion service.
    
    Initializes and starts the IngestController with an IngestOrchestrator
    to run ingestion in the background.
    """
    # Set up signal handlers
    def signal_handler(sig, frame):
        logger.info({"action": "SHUTDOWN_SIGNAL", "message": f"Received signal {sig}"})
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    controller = None
    
    try:
        logger.info({"action": "INGEST_SERVICE_START", "message": "Starting ingestion service"})
        
        # Create and initialize controller
        controller = IngestController(logger_name="ingest_service.controller")
        
        await controller.initialize()
        
        # Start the background ingestion process
        await controller.start()
        
        logger.info({
            "action": "INGEST_SERVICE_STARTED",
            "message": "Ingestion service started successfully"
        })
        
        # Keep the service running
        while True:
            await asyncio.sleep(60)
    
    except KeyboardInterrupt:
        logger.info({"action": "KEYBOARD_INTERRUPT", "message": "Service stopped by user"})
    except Exception as e:
        logger.critical({
            "action": "FATAL_ERROR",
            "message": f"Fatal error in ingestion service: {str(e)}",
            "traceback": traceback.format_exc()
        })
    finally:
        # Clean up
        if controller and controller._is_running:
            logger.info({"action": "INGEST_SERVICE_SHUTDOWN", "message": "Shutting down ingestion service"})
            await controller.stop()

if __name__ == "__main__":
    asyncio.run(main()) 