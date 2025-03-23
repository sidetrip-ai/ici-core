#!/usr/bin/env python3
"""
Async Telegram Ingestion Pipeline Example

This script demonstrates how to use an asynchronous Telegram ingestion pipeline
that processes messages in real-time with customizable components.

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
import logging
from typing import Dict, Any

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
from ici.utils.config import get_component_config, load_config
from ici.adapters.ingestors.telegram import TelegramIngestor
from ici.adapters.preprocessors.telegram import TelegramPreprocessor
from ici.adapters.embedders.sentence_transformer import SentenceTransformerEmbedder
from ici.adapters.vector_stores.chroma import ChromaDBStore
from ici.utils.state_manager import StateManager
from ici.adapters.loggers import StructuredLogger

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AsyncTelegramIngestionPipeline:
    """
    Async wrapper for the TelegramIngestionPipeline.
    
    This class wraps the TelegramIngestionPipeline to handle asynchronous operations
    from the TelegramIngestor when running in an async context.
    """
    
    def __init__(self, logger_name: str = "async_telegram_pipeline"):
        """Initialize the async pipeline wrapper."""
        self.logger = StructuredLogger(name=logger_name)
        self._ingestor = None
        self._preprocessor = None
        self._embedder = None
        self._vector_store = None
        self._state_manager = None
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        self._is_initialized = False
        
    async def initialize(self):
        """Initialize all components for the pipeline."""
        try:
            self.logger.info({
                "action": "ASYNC_PIPELINE_INIT_START",
                "message": "Initializing async Telegram ingestion pipeline"
            })
            
            # Load pipeline configuration
            pipeline_config = get_component_config("pipelines.telegram", self._config_path)
            
            # Extract pipeline parameters
            self._batch_size = int(pipeline_config.get("batch_size", 100))
            schedule_config = pipeline_config.get("schedule", {})
            self._schedule_interval_minutes = int(schedule_config.get("interval_minutes", 60))
            
            # Initialize state manager
            state_manager_config = get_component_config("state_manager", self._config_path) or {}
            db_path = state_manager_config.get("db_path", "ingestor_state.db")
            
            self._state_manager = StateManager(db_path=db_path)
            self._state_manager.initialize()
            
            # Initialize components
            self._ingestor = TelegramIngestor()
            self._preprocessor = TelegramPreprocessor()
            self._embedder = SentenceTransformerEmbedder()
            self._vector_store = ChromaDBStore()
            
            await self._ingestor.initialize()
            await self._preprocessor.initialize()
            await self._embedder.initialize()
            await self._vector_store.initialize()
            
            self._is_initialized = True
            
            self.logger.info({
                "action": "ASYNC_PIPELINE_INIT_SUCCESS",
                "message": "Async Telegram ingestion pipeline initialized successfully"
            })
            
        except Exception as e:
            self.logger.error({
                "action": "ASYNC_PIPELINE_INIT_ERROR",
                "message": f"Failed to initialize async pipeline: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise
    
    async def run_ingestion(self, ingestor_id: str):
        """
        Run the ingestion process asynchronously.
        
        Args:
            ingestor_id: Unique identifier for the ingestor
            
        Returns:
            Dict: Results of the ingestion run
        """
        if not self._is_initialized:
            raise ValueError("Pipeline not initialized. Call initialize() first.")
        
        start_time = datetime.now()
        results = {
            "success": False,
            "documents_processed": 0,
            "errors": [],
            "start_time": start_time,
            "end_time": None,
            "duration": 0
        }
        
        try:
            self.logger.info({
                "action": "ASYNC_PIPELINE_RUN_START",
                "message": f"Starting async Telegram ingestion for {ingestor_id}",
                "data": {"ingestor_id": ingestor_id}
            })
            
            # Get ingestor state
            state = self._state_manager.get_state(ingestor_id)
            last_timestamp = state.get("last_timestamp", 0)
            metadata = state.get("additional_metadata", {})
            
            # Determine fetch mode based on state
            if last_timestamp == 0:
                # First run - fetch all historical data
                self.logger.info({
                    "action": "ASYNC_PIPELINE_HISTORICAL_FETCH",
                    "message": "First run - fetching all historical data"
                })
                raw_data_result = self._ingestor.fetch_full_data()
                # Handle potential coroutine result
                if asyncio.iscoroutine(raw_data_result):
                    raw_data = await raw_data_result
                else:
                    raw_data = raw_data_result
            else:
                # Incremental run - fetch new data since last timestamp
                last_datetime = datetime.fromtimestamp(last_timestamp)
                self.logger.info({
                    "action": "ASYNC_PIPELINE_INCREMENTAL_FETCH",
                    "message": f"Fetching data since {last_datetime.isoformat()}"
                })
                raw_data_result = self._ingestor.fetch_new_data(since=last_datetime)
                # Handle potential coroutine result
                if asyncio.iscoroutine(raw_data_result):
                    raw_data = await raw_data_result
                else:
                    raw_data = raw_data_result
            
            # Check if data was retrieved
            if not raw_data or not raw_data.get("messages"):
                self.logger.info({
                    "action": "ASYNC_PIPELINE_NO_DATA",
                    "message": "No new data to process"
                })
                results["success"] = True
                results["end_time"] = datetime.now()
                results["duration"] = (results["end_time"] - start_time).total_seconds()
                return results
            
            # Process the data
            messages = raw_data.get("messages", [])
            total_messages = len(messages)
            
            self.logger.info({
                "action": "ASYNC_PIPELINE_DATA_FETCHED",
                "message": f"Fetched {total_messages} messages",
                "data": {"message_count": total_messages}
            })
            
            # Process messages in batches
            total_documents_processed = 0
            
            # Process messages in batches for better memory usage
            for i in range(0, len(messages), self._batch_size):
                batch = messages[i:i+self._batch_size]
                
                # Preprocess batch
                preprocessed_data = await self._preprocessor.process(batch)
                
                # Generate embeddings
                documents_with_embeddings = []
                document_ids = []
                documents_for_store = []
                vectors_for_store = []
                
                for doc in preprocessed_data:
                    text = doc.get("text", "")
                    metadata = doc.get("metadata", {})
                    doc_id = doc.get("id")
                    
                    # Generate embedding
                    embedding_result = await self._embedder.embed(text)
                    embedding, embed_metadata = embedding_result
                    
                    # Store separately for vector store
                    document_ids.append(doc_id)
                    documents_for_store.append({
                        "id": doc_id,
                        "text": text,
                        "metadata": metadata
                    })
                    vectors_for_store.append(embedding)
                    
                    # Keep full data for tracking
                    documents_with_embeddings.append({
                        "id": doc_id,
                        "text": text,
                        "embedding": embedding,
                        "metadata": metadata
                    })
                
                # Store in vector database
                if documents_for_store:
                    store_result = self._vector_store.add_documents(
                        documents=documents_for_store, 
                        vectors=vectors_for_store
                    )
                    total_documents_processed += len(documents_for_store)
                
                # Update state if this batch has newer messages
                batch_timestamp = max([
                    int(datetime.fromisoformat(msg.get("date", "1970-01-01T00:00:00")).timestamp())
                    for msg in batch
                    if msg.get("date")
                ], default=0)
                
                if batch_timestamp > last_timestamp:
                    last_timestamp = batch_timestamp
                    
                    # Update total_messages_processed in metadata
                    metadata["total_messages_processed"] = metadata.get("total_messages_processed", 0) + len(batch)
                    
                    # Update state
                    self._state_manager.set_state(
                        ingestor_id=ingestor_id,
                        last_timestamp=last_timestamp,
                        additional_metadata=metadata
                    )
                
                self.logger.info({
                    "action": "ASYNC_PIPELINE_BATCH_COMPLETE",
                    "message": f"Processed batch {i//self._batch_size + 1}/{(total_messages + self._batch_size - 1)//self._batch_size}",
                    "data": {
                        "batch_size": len(batch),
                        "documents_processed": len(documents_for_store)
                    }
                })
            
            # Update final results
            results["success"] = True
            results["documents_processed"] = total_documents_processed
            
            # Update final metadata with chat statistics
            chat_count = len(set(msg.get("conversation_id") for msg in messages if msg.get("conversation_id")))
            metadata["chats_processed"] = chat_count
            
            self._state_manager.set_state(
                ingestor_id=ingestor_id,
                last_timestamp=last_timestamp,
                additional_metadata=metadata
            )
            
            self.logger.info({
                "action": "ASYNC_PIPELINE_RUN_COMPLETE",
                "message": f"Completed async Telegram ingestion for {ingestor_id}",
                "data": {
                    "ingestor_id": ingestor_id,
                    "documents_processed": total_documents_processed,
                    "success": True
                }
            })
            
        except Exception as e:
            self.logger.error({
                "action": "ASYNC_PIPELINE_RUN_ERROR",
                "message": f"Async Telegram ingestion failed for {ingestor_id}: {str(e)}",
                "data": {
                    "ingestor_id": ingestor_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            })
            results["errors"].append(str(e))
        
        finally:
            results["end_time"] = datetime.now()
            results["duration"] = (results["end_time"] - start_time).total_seconds()
            return results
    
    async def healthcheck(self):
        """Check the health of all pipeline components."""
        health_result = {
            "healthy": False,
            "message": "Async Telegram ingestion pipeline health check failed",
            "details": {
                "initialized": self._is_initialized
            },
            "components": {}
        }
        
        if not self._is_initialized:
            health_result["message"] = "Pipeline not initialized"
            return health_result
        
        try:
            # Check ingestor
            ingestor_health = self._ingestor.healthcheck()
            if asyncio.iscoroutine(ingestor_health):
                ingestor_health = await ingestor_health
            health_result["components"]["ingestor"] = ingestor_health
            
            # Check preprocessor
            preprocessor_health = self._preprocessor.healthcheck()
            health_result["components"]["preprocessor"] = preprocessor_health
            
            # Check embedder
            embedder_health = await self._embedder.healthcheck()
            health_result["components"]["embedder"] = embedder_health
            
            # Check vector store
            vector_store_health = self._vector_store.healthcheck()
            health_result["components"]["vector_store"] = vector_store_health
            
            # Check if all components are healthy
            all_healthy = all([
                ingestor_health.get("healthy", False),
                preprocessor_health.get("healthy", False),
                embedder_health.get("healthy", False),
                vector_store_health.get("healthy", False)
            ])
            
            if all_healthy:
                health_result["healthy"] = True
                health_result["message"] = "All components are healthy"
            else:
                # Determine which components are unhealthy
                unhealthy = []
                
                if not ingestor_health.get("healthy", False):
                    unhealthy.append("ingestor")
                if not preprocessor_health.get("healthy", False):
                    unhealthy.append("preprocessor")
                if not embedder_health.get("healthy", False):
                    unhealthy.append("embedder")
                if not vector_store_health.get("healthy", False):
                    unhealthy.append("vector_store")
                
                health_result["message"] = f"Unhealthy components: {', '.join(unhealthy)}"
                
            return health_result
            
        except Exception as e:
            health_result["message"] = f"Health check error: {str(e)}"
            health_result["details"]["error"] = str(e)
            health_result["details"]["error_type"] = type(e).__name__
            return health_result
    
    def register_ingestor(self, ingestor_id: str, ingestor_config: dict):
        """Register an ingestor with the pipeline."""
        if not self._is_initialized:
            raise ValueError("Pipeline not initialized. Call initialize() first.")
        
        # Check if ingestor already exists
        state = self._state_manager.get_state(ingestor_id)
        
        # Register new ingestor state
        self._state_manager.set_state(
            ingestor_id=ingestor_id,
            last_timestamp=state.get("last_timestamp", 0),
            additional_metadata={
                "config": ingestor_config,
                "registration_time": datetime.now().isoformat()
            }
        )
        
        self.logger.info({
            "action": "ASYNC_PIPELINE_INGESTOR_REGISTERED",
            "message": f"Registered ingestor {ingestor_id}",
            "data": {"ingestor_id": ingestor_id}
        })
    
    def get_ingestor_state(self, ingestor_id: str):
        """Get the current state of an ingestor."""
        if not self._is_initialized:
            raise ValueError("Pipeline not initialized. Call initialize() first.")
        
        return self._state_manager.get_state(ingestor_id)
    
    def set_ingestor_state(self, ingestor_id: str, state: dict):
        """Set the state for an ingestor."""
        if not self._is_initialized:
            raise ValueError("Pipeline not initialized. Call initialize() first.")
        
        return self._state_manager.set_state(
            ingestor_id=ingestor_id,
            last_timestamp=state.get("last_timestamp", 0),
            additional_metadata=state.get("additional_metadata", {})
        )
    
    def get_ingestion_metrics(self, ingestor_id: str):
        """Get metrics for a specific ingestor."""
        if not self._is_initialized:
            raise ValueError("Pipeline not initialized. Call initialize() first.")
        
        state = self._state_manager.get_state(ingestor_id)
        metadata = state.get("additional_metadata", {})
        
        return {
            "total_messages_processed": metadata.get("total_messages_processed", 0),
            "chats_processed": metadata.get("chats_processed", 0),
            "last_timestamp": state.get("last_timestamp", 0),
            "last_run": metadata.get("last_run", None)
        }


async def main():
    """Run the example async Telegram ingestion pipeline."""
    parser = argparse.ArgumentParser(description="Async Telegram Ingestion Pipeline Example")
    parser.add_argument("--config", type=str, default="../config.yaml", help="Path to config file")
    parser.add_argument("--ingestor-id", type=str, default="telegram_example", help="Ingestor ID")
    parser.add_argument("--env-file", type=str, help="Path to .env file (default is .env)")
    args = parser.parse_args()
    
    # Try to load environment variables again if env-file is specified
    if args.env_file and 'load_env' in globals():
        load_env(args.env_file)
    
    # Load configuration
    config_path = os.path.abspath(args.config)
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        return
    
    config = load_config(config_path)

    # Initialize pipeline
    pipeline = TelegramIngestionPipeline(
        logger_name="telegram_example"
    )
    
    # Initialize components
    await pipeline.initialize()
    
    # Run health check
    health_status = await pipeline.healthcheck()
    logger.info(f"Health check results: {health_status}")
    
    if not health_status["healthy"]:
        logger.error("Pipeline is not healthy, exiting")
        return
    
    # Run ingestion once
    try:
        results = await pipeline.run_ingestion(args.ingestor_id)
        logger.info(f"Ingestion results: {results}")
    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
        raise


def create_example_config(config_path):
    """Create an example configuration file."""
    example_config = {
        "ingestors": {
            "telegram": {
                "api_id": "YOUR_API_ID",
                "api_hash": "YOUR_API_HASH",
                "phone_number": "YOUR_PHONE_NUMBER",
                "session_string": "",
                "request_delay": 1.0
            }
        },
        "preprocessors": {
            "telegram": {
                "chunk_size": 1000,
                "chunk_overlap": 100,
                "group_by_conversation": True,
                "minimum_message_length": 10
            }
        },
        "embedders": {
            "sentence_transformer": {
                "model_name": "all-MiniLM-L6-v2",
                "device": "cpu"
            }
        },
        "vector_stores": {
            "chroma": {
                "collection_name": "messages",
                "persist_directory": "data/chroma",
                "embedding_function": "sentence_transformer"
            }
        },
        "pipelines": {
            "telegram": {
                "batch_size": 100,
                "schedule_interval_minutes": 60
            }
        },
        "state_manager": {
            "db_path": "data/state/ingestor_state.db"
        }
    }
    
    # Create directory for state if needed
    os.makedirs("data/state", exist_ok=True)
    os.makedirs("data/chroma", exist_ok=True)
    
    with open(config_path, "w") as f:
        yaml.dump(example_config, f, default_flow_style=False)


if __name__ == "__main__":
    asyncio.run(main()) 