#!/usr/bin/env python3
"""
Example script to run Telegram ingestion with debug mode enabled.
This will fetch just one message and print detailed diagnostics about it.
"""

import os
import asyncio
import logging
import yaml
from datetime import datetime, timedelta

from ici.adapters.ingestors.telegram import TelegramIngestor
from ici.adapters.pipelines.telegram import TelegramIngestionPipeline
from ici.adapters.storage.memory import InMemoryStorage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("telegram_debug")

async def run_debug():
    """Run a single ingestion with debug mode enabled"""
    
    # Load configuration
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    telegram_config = config.get('telegram', {})
    
    # Create storage
    storage = InMemoryStorage(logger=logger)
    
    # Create ingestor with short timeframe
    now = datetime.now()
    start_date = now - timedelta(days=3)  # Last 3 days
    
    ingestor = TelegramIngestor(
        api_id=telegram_config.get('api_id'),
        api_hash=telegram_config.get('api_hash'),
        phone=telegram_config.get('phone'),
        session_name="telegram_debug",
        conversation_ids=telegram_config.get('conversation_ids', []),
        start_date=start_date,
        end_date=now,
        logger=logger
    )
    
    # Create pipeline
    pipeline = TelegramIngestionPipeline(
        ingestors={ingestor.id: ingestor},
        storage=storage,
        interval_seconds=3600,  # Not used in debug mode
        logger=logger
    )
    
    try:
        # Run with debug flag
        logger.info("Starting debug ingestion...")
        result = await pipeline.start(ingestor_id=ingestor.id, debug_first_message=True)
        
        logger.info(f"Debug ingestion complete: {result}")
    finally:
        # Always disconnect the ingestor
        await ingestor.disconnect()
        logger.info("Disconnected from Telegram")

if __name__ == "__main__":
    asyncio.run(run_debug()) 