#!/usr/bin/env python3
"""
WhatsApp Ingest Script

This script initializes and runs the WhatsAppIngestOrchestrator to process
WhatsApp data sources. It runs continuously in the background until interrupted.
"""

import os
import sys
import asyncio
import signal
import logging
from datetime import datetime

# Add the project root to Python path if needed
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ici.adapters.orchestrators import WhatsAppIngestOrchestrator
from ici.adapters.loggers import StructuredLogger

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"logs/whatsapp-ingest-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log")
    ]
)

logger = logging.getLogger("whatsapp-ingest")

# Global reference to orchestrator for clean shutdown
orchestrator = None

async def run_whatsapp_ingestion():
    """Initialize and run the WhatsApp ingestion orchestrator."""
    global orchestrator
    
    logger.info("Starting WhatsApp ingest process")
    
    try:
        # Create and initialize the orchestrator
        orchestrator = WhatsAppIngestOrchestrator()
        await orchestrator.initialize()
        
        # Start WhatsApp ingestion
        await orchestrator.start_ingestion()
        
        logger.info("WhatsApp ingestion started successfully")
        
        # Keep the script running
        while True:
            await asyncio.sleep(60)  # Check every minute
            
            # Optional: Add health check or status report here
            health = await orchestrator.healthcheck()
            if not health.get("healthy", False):
                logger.warning(f"WhatsApp orchestrator health check failed: {health.get('message', 'Unknown error')}")
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error in WhatsApp ingestion: {str(e)}", exc_info=True)
    finally:
        # Clean shutdown
        if orchestrator:
            try:
                orchestrator.stop_ingestion()
                await orchestrator.close()
                logger.info("WhatsApp ingestion stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping WhatsApp ingestion: {str(e)}", exc_info=True)

def handle_signal(sig, frame):
    """Handle termination signals for clean shutdown."""
    logger.info(f"Received signal {sig}, initiating shutdown...")
    # Signal the event loop to stop
    if asyncio.get_event_loop().is_running():
        asyncio.get_event_loop().stop()

if __name__ == "__main__":
    # Register signal handlers for clean shutdown
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Run the async main function
    try:
        asyncio.run(run_whatsapp_ingestion())
    except KeyboardInterrupt:
        logger.info("Process terminated by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
        sys.exit(1) 