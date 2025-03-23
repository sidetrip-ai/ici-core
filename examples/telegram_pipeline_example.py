#!/usr/bin/env python3
"""
Telegram Ingestion Pipeline Example

This script demonstrates how to use the TelegramIngestionPipeline to ingest and process
Telegram messages, transform them, generate embeddings, and store them in ChromaDB.

Prerequisites:
1. Set up config.yaml with Telegram API credentials (or use environment variables)
2. Ensure all dependencies are installed (pip install -r requirements.txt)
3. Create a .env file from .env.example and fill in your credentials
"""

import os
import sys
import asyncio
from datetime import datetime
import argparse
import yaml

# Add the parent directory to sys.path to import from ici
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import environment variable loader
try:
    from ici.utils.load_env import load_env
    # Load environment variables from .env file
    load_env()
except ImportError:
    print("Warning: Environment variable loader not found. Environment variables may not be loaded.")

from ici.adapters.pipelines import TelegramIngestionPipeline
from ici.utils.config import get_component_config


async def main():
    """Run the example Telegram ingestion pipeline."""
    parser = argparse.ArgumentParser(description="Telegram Ingestion Pipeline Example")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config file")
    parser.add_argument("--ingestor-id", type=str, default="telegram_example", help="Ingestor ID")
    parser.add_argument("--full-run", action="store_true", help="Perform a full historical run")
    parser.add_argument("--env-file", type=str, help="Path to .env file (default is .env)")
    args = parser.parse_args()
    
    # Try to load environment variables again if env-file is specified
    if args.env_file and 'load_env' in locals():
        load_env(args.env_file)
    
    # Set environment variable for config path
    os.environ["ICI_CONFIG_PATH"] = args.config
    
    # Ensure config file exists
    if not os.path.exists(args.config):
        create_example_config(args.config)
        print(f"Created example config file at {args.config}")
        print("Please edit this file to add your Telegram API credentials before running again.")
        print("Or set the appropriate environment variables in your .env file.")
        return
    
    print(f"Starting Telegram ingestion pipeline example with ingestor ID: {args.ingestor_id}")
    
    # Create and initialize the pipeline
    pipeline = TelegramIngestionPipeline()
    
    try:
        print("Initializing pipeline...")
        await pipeline.initialize()
        
        # Register the ingestor if running for the first time
        ingestor_state = pipeline.get_ingestor_state(args.ingestor_id)
        
        if ingestor_state.get("last_timestamp", 0) == 0 or args.full_run:
            print(f"Registering ingestor: {args.ingestor_id}")
            # Get Telegram config from config file
            telegram_config = get_component_config("ingestors.telegram", args.config) or {}
            
            pipeline.register_ingestor(
                ingestor_id=args.ingestor_id,
                ingestor_config=telegram_config
            )
            
            if args.full_run:
                print("Resetting ingestor state for full historical run")
                pipeline.set_ingestor_state(
                    ingestor_id=args.ingestor_id,
                    state={"last_timestamp": 0, "additional_metadata": {}}
                )
        
        # Run the ingestion process
        print(f"Running ingestion for {args.ingestor_id}...")
        result = pipeline.run_ingestion(args.ingestor_id)
        
        # Print results
        print("\nIngestion Results:")
        print(f"Success: {result['success']}")
        print(f"Documents processed: {result['documents_processed']}")
        
        if result.get("message"):
            print(f"Message: {result['message']}")
            
        if result.get("errors") and len(result["errors"]) > 0:
            print("\nErrors encountered:")
            for error in result["errors"]:
                print(f"- {error}")
        
        # Get updated state and metrics
        print("\nUpdated State:")
        state = pipeline.get_ingestor_state(args.ingestor_id)
        if state.get("last_timestamp", 0) > 0:
            last_date = datetime.fromtimestamp(state["last_timestamp"]).isoformat()
            print(f"Last processed timestamp: {last_date}")
        
        # Get metrics
        print("\nIngestion Metrics:")
        metrics = pipeline.get_ingestion_metrics(args.ingestor_id)
        print(f"Total messages processed: {metrics.get('total_messages_processed', 0)}")
        print(f"Chats processed: {metrics.get('chats_processed', 0)}")
        
        # Check pipeline health
        print("\nChecking pipeline health...")
        health = pipeline.healthcheck()
        print(f"Pipeline healthy: {health.get('healthy', False)}")
        print(f"Health message: {health.get('message', 'Unknown health status')}")
        
        print("\nPipeline example completed successfully.")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def create_example_config(config_path):
    """Create an example configuration file."""
    example_config = {
        "ingestors": {
            "telegram": {
                "api_id": "YOUR_API_ID",
                "api_hash": "YOUR_API_HASH",
                "phone": "YOUR_PHONE_NUMBER",
                "session_file": "telegram_session.session",
                "max_messages": 1000,
            }
        },
        "preprocessors": {
            "telegram": {
                "time_window_minutes": 15,
                "chunk_size": 512,
                "max_messages_per_chunk": 10,
                "include_overlap": True
            }
        },
        "embedders": {
            "sentence_transformer": {
                "model_name": "all-MiniLM-L6-v2",
                "device": "cpu"  # or "cuda" for GPU support
            }
        },
        "vector_stores": {
            "chroma": {
                "collection_name": "telegram_messages",
                "persist_directory": "chroma_db",
                "embedding_function": "sentence_transformer"
            }
        },
        "pipelines": {
            "telegram": {
                "batch_size": 100,
                "schedule": {
                    "interval_minutes": 60
                }
            }
        },
        "state_manager": {
            "db_path": "ingestor_state.db"
        }
    }
    
    with open(config_path, "w") as f:
        yaml.dump(example_config, f, default_flow_style=False)


if __name__ == "__main__":
    asyncio.run(main()) 