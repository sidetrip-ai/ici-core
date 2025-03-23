"""
Telegram ingestion pipeline implementation.

This module provides an IngestionPipeline implementation for Telegram data,
orchestrating the flow from TelegramIngestor to TelegramPreprocessor to
SentenceTransformerEmbedder to ChromaDBStore, with state management.
"""

import os
import json
import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

# from apscheduler.schedulers.background import BackgroundScheduler
# from apscheduler.triggers.interval import IntervalTrigger
import asyncio

from ici.core.interfaces.pipeline import IngestionPipeline
from ici.adapters.ingestors.telegram import TelegramIngestor
from ici.adapters.preprocessors import TelegramPreprocessor
from ici.adapters.embedders.sentence_transformer import SentenceTransformerEmbedder
from ici.adapters.vector_stores import ChromaDBStore
from ici.adapters.loggers import StructuredLogger
from ici.utils.config import get_component_config
from ici.utils.state_manager import StateManager
from ici.core.exceptions import IngestionPipelineError
from ici.utils.datetime_utils import from_timestamp, ensure_tz_aware, from_isoformat


class TelegramIngestionPipeline(IngestionPipeline):
    """
    Pipeline implementation for ingesting Telegram data.
    
    This pipeline coordinates the data flow from TelegramIngestor to TelegramPreprocessor
    to SentenceTransformerEmbedder to ChromaDBStore, with state tracking via SQLite.
    """
    
    def __init__(self, logger_name: str = "telegram_ingestion_pipeline"):
        """
        Initialize the TelegramIngestionPipeline.
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = StructuredLogger(name=logger_name)
        self._is_initialized = False
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        
        # Components
        self._ingestor = None
        self._preprocessor = None
        self._embedder = None
        self._vector_store = None
        self._state_manager = None
        
        # Configuration
        self._batch_size = 100
        self._schedule_interval_minutes = 60
    
    async def initialize(self) -> None:
        """
        Initialize the ingestion pipeline and its components.
        
        This method loads configuration from config.yaml and initializes
        all pipeline components (ingestor, preprocessor, embedder, vector store, state manager).
        
        Returns:
            None
            
        Raises:
            IngestionPipelineError: If initialization fails
        """
        try:
            self.logger.info({
                "action": "PIPELINE_INIT_START",
                "message": "Initializing Telegram ingestion pipeline"
            })
            
            # Load pipeline configuration
            try:
                pipeline_config = get_component_config("pipelines.telegram", self._config_path)
                
                # Extract pipeline parameters
                self._batch_size = int(pipeline_config.get("batch_size", 100))
                schedule_config = pipeline_config.get("schedule", {})
                self._schedule_interval_minutes = int(schedule_config.get("interval_minutes", 60))
                
                self.logger.info({
                    "action": "PIPELINE_CONFIG_LOADED",
                    "message": "Loaded pipeline configuration",
                    "data": {
                        "batch_size": self._batch_size,
                        "schedule_interval_minutes": self._schedule_interval_minutes
                    }
                })
                
            except Exception as e:
                # Use defaults if configuration loading fails
                self.logger.warning({
                    "action": "PIPELINE_CONFIG_ERROR",
                    "message": f"Failed to load pipeline configuration: {str(e)}. Using defaults.",
                    "data": {"error": str(e)}
                })
            
            # Initialize state manager
            state_manager_config = get_component_config("state_manager", self._config_path) or {}
            db_path = state_manager_config.get("db_path", "ingestor_state.db")
            
            self._state_manager = StateManager(db_path=db_path)
            self._state_manager.initialize()
            
            self.logger.info({
                "action": "PIPELINE_STATE_MANAGER_INIT",
                "message": "Initialized state manager",
                "data": {"db_path": db_path}
            })
            
            # Initialize components
            self._ingestor = TelegramIngestor()
            self._preprocessor = TelegramPreprocessor()
            self._embedder = SentenceTransformerEmbedder()
            self._vector_store = ChromaDBStore()
            
            await self._ingestor.initialize()
            await self._preprocessor.initialize()
            await self._embedder.initialize()
            await self._vector_store.initialize()
            
            self.logger.info({
                "action": "PIPELINE_COMPONENTS_INIT",
                "message": "Initialized all pipeline components"
            })
            
            self._is_initialized = True
            
            self.logger.info({
                "action": "PIPELINE_INIT_SUCCESS",
                "message": "Telegram ingestion pipeline initialized successfully"
            })
            
        except Exception as e:
            self.logger.error({
                "action": "PIPELINE_INIT_ERROR",
                "message": f"Failed to initialize Telegram ingestion pipeline: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise IngestionPipelineError(f"Pipeline initialization failed: {str(e)}") from e
    
    async def run_ingestion(self, ingestor_id: str) -> Dict[str, Any]:
        """
        Execute the full ingestion pipeline for Telegram data.
        
        This method orchestrates the full data flow:
        1. Retrieves ingestor state from the database
        2. Fetches messages from Telegram based on state
        3. Preprocesses messages into standardized documents
        4. Generates embeddings for documents
        5. Stores documents with vectors in ChromaDB
        6. Updates ingestor state
        
        Args:
            ingestor_id: Unique identifier for the ingestor
            
        Returns:
            Dict[str, Any]: Summary of the ingestion run
            
        Raises:
            IngestionPipelineError: If the ingestion process fails
        """
        if not self._is_initialized:
            raise IngestionPipelineError("Pipeline not initialized. Call initialize() first.")
        
        start_time = datetime.now(timezone.utc)
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
                "action": "PIPELINE_RUN_START",
                "message": f"Starting Telegram ingestion for {ingestor_id}",
                "data": {"ingestor_id": ingestor_id}
            })
            
            # Get ingestor state
            state = self._state_manager.get_state(ingestor_id)
            last_timestamp = state.get("last_timestamp", 0)
            metadata = state.get("additional_metadata", {})
            
            # Determine fetch mode based on state
            if last_timestamp == 0:
                # First run - fetch all historical data
                raw_data = await self._ingestor.fetch_full_data()
            else:
                # Incremental run - fetch new data since last timestamp
                # Convert timestamp to timezone-aware datetime
                last_datetime = from_timestamp(last_timestamp)
                raw_data = await self._ingestor.fetch_new_data(since=last_datetime)
            
            # Check if data was retrieved
            if not raw_data or not raw_data.get("messages"):
                self.logger.info({
                    "action": "PIPELINE_NO_DATA",
                    "message": "No new data to process"
                })
                results["success"] = True
                results["message"] = "No new data to process"
                return self._finalize_results(results, start_time)
            
            # Process messages in batches
            messages = raw_data.get("messages", [])
            total_messages = len(messages)
            
            self.logger.info({
                "action": "PIPELINE_DATA_FETCHED",
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
                
                # Generate embeddings and prepare for storage
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
                    documents_for_store.append({
                        "id": doc_id,
                        "text": text,
                        "metadata": metadata
                    })
                    vectors_for_store.append(embedding)
                
                # Store in vector database
                if documents_for_store:
                    self._vector_store.add_documents(
                        documents=documents_for_store,
                        vectors=vectors_for_store
                    )
                    total_documents_processed += len(documents_for_store)
                
                # Update state if this batch has newer messages
                batch_timestamp = max([
                    int(from_isoformat(msg.get("date", "1970-01-01T00:00:00")).timestamp())
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
                    "action": "PIPELINE_BATCH_COMPLETE",
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
                "action": "PIPELINE_RUN_COMPLETE",
                "message": f"Completed Telegram ingestion for {ingestor_id}",
                "data": {
                    "ingestor_id": ingestor_id,
                    "documents_processed": total_documents_processed,
                    "success": True
                }
            })
            
        except Exception as e:
            self.logger.error({
                "action": "PIPELINE_RUN_ERROR",
                "message": f"Telegram ingestion failed for {ingestor_id}: {str(e)}",
                "data": {
                    "ingestor_id": ingestor_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            })
            results["errors"].append(str(e))
        
        return self._finalize_results(results, start_time)
    
    async def start(self) -> Dict[str, Any]:
        """
        Asynchronously start a single ingestion run.
        
        This method performs a single ingestion run following the async-first pattern.
        
        Returns:
            Dict[str, Any]: Summary of the ingestion run
            
        Raises:
            IngestionPipelineError: If the ingestion fails
        """
        if not self._is_initialized:
            raise IngestionPipelineError("Pipeline not initialized. Call initialize() first.")
        
        try:
            ingestor_id = "telegram_ingestor"
            
            self.logger.info({
                "action": "PIPELINE_INGESTION_START",
                "message": "Starting a single ingestion run",
                "data": {"ingestor_id": ingestor_id}
            })
            
            # Run ingestion asynchronously
            result = await self.run_ingestion(ingestor_id)
            
            self.logger.info({
                "action": "PIPELINE_INGESTION_COMPLETE",
                "message": "Completed single ingestion run",
                "data": {
                    "success": result.get("success", False),
                    "documents_processed": result.get("documents_processed", 0),
                    "duration": result.get("duration", 0)
                }
            })
            
            return result
            
        except Exception as e:
            self.logger.error({
                "action": "PIPELINE_INGESTION_ERROR",
                "message": f"Failed to run ingestion: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise IngestionPipelineError(f"Failed to run ingestion: {str(e)}") from e
    
    def register_ingestor(self, ingestor_id: str, ingestor_config: Dict[str, Any]) -> None:
        """
        Register an ingestor with the pipeline.
        
        Args:
            ingestor_id: Unique identifier for the ingestor
            ingestor_config: Configuration for the ingestor
            
        Raises:
            IngestionPipelineError: If registration fails
        """
        if not self._is_initialized:
            raise IngestionPipelineError("Pipeline not initialized. Call initialize() first.")
        
        try:
            # Check if ingestor already exists
            existing_state = self._state_manager.get_state(ingestor_id)
            if existing_state.get("last_timestamp", 0) > 0:
                self.logger.info({
                    "action": "PIPELINE_INGESTOR_EXISTS",
                    "message": f"Ingestor {ingestor_id} already registered",
                    "data": {"ingestor_id": ingestor_id}
                })
                return
            
            # Initialize with empty state
            self._state_manager.set_state(
                ingestor_id=ingestor_id,
                last_timestamp=0,
                additional_metadata={
                    "config": ingestor_config,
                    "registration_date": datetime.now().isoformat(),
                    "total_messages_processed": 0,
                    "processing_status": "registered"
                }
            )
            
            self.logger.info({
                "action": "PIPELINE_INGESTOR_REGISTERED",
                "message": f"Registered ingestor {ingestor_id}",
                "data": {"ingestor_id": ingestor_id}
            })
            
        except Exception as e:
            self.logger.error({
                "action": "PIPELINE_INGESTOR_REGISTRATION_ERROR",
                "message": f"Failed to register ingestor {ingestor_id}: {str(e)}",
                "data": {"ingestor_id": ingestor_id, "error": str(e)}
            })
            raise IngestionPipelineError(f"Ingestor registration failed: {str(e)}") from e
    
    def get_ingestor_state(self, ingestor_id: str) -> Dict[str, Any]:
        """
        Retrieve the current state for an ingestor.
        
        Args:
            ingestor_id: Unique identifier for the ingestor
            
        Returns:
            Dict[str, Any]: Current state information
            
        Raises:
            IngestionPipelineError: If state retrieval fails
        """
        if not self._is_initialized:
            raise IngestionPipelineError("Pipeline not initialized. Call initialize() first.")
        
        try:
            return self._state_manager.get_state(ingestor_id)
        except Exception as e:
            self.logger.error({
                "action": "PIPELINE_GET_STATE_ERROR",
                "message": f"Failed to retrieve state for ingestor {ingestor_id}: {str(e)}",
                "data": {"ingestor_id": ingestor_id, "error": str(e)}
            })
            raise IngestionPipelineError(f"State retrieval failed: {str(e)}") from e
    
    def set_ingestor_state(self, ingestor_id: str, state: Dict[str, Any]) -> None:
        """
        Update the state for an ingestor.
        
        Args:
            ingestor_id: Unique identifier for the ingestor
            state: New state information
            
        Raises:
            IngestionPipelineError: If state update fails
        """
        if not self._is_initialized:
            raise IngestionPipelineError("Pipeline not initialized. Call initialize() first.")
        
        try:
            last_timestamp = state.get("last_timestamp", 0)
            additional_metadata = state.get("additional_metadata", {})
            
            self._state_manager.set_state(
                ingestor_id=ingestor_id,
                last_timestamp=last_timestamp,
                additional_metadata=additional_metadata
            )
            
            self.logger.info({
                "action": "PIPELINE_SET_STATE",
                "message": f"Updated state for ingestor {ingestor_id}",
                "data": {
                    "ingestor_id": ingestor_id,
                    "last_timestamp": last_timestamp
                }
            })
            
        except Exception as e:
            self.logger.error({
                "action": "PIPELINE_SET_STATE_ERROR",
                "message": f"Failed to update state for ingestor {ingestor_id}: {str(e)}",
                "data": {"ingestor_id": ingestor_id, "error": str(e)}
            })
            raise IngestionPipelineError(f"State update failed: {str(e)}") from e
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Check if the ingestion pipeline and all its components are properly configured and functioning.
        
        Returns:
            Dict[str, Any]: Health status information
            
        Raises:
            IngestionPipelineError: If the health check itself encounters an error
        """
        health_result = {
            "healthy": False,
            "message": "Telegram ingestion pipeline health check failed",
            "details": {
                "initialized": self._is_initialized
            },
            "components": {}
        }
        
        try:
            if not self._is_initialized:
                health_result["message"] = "Pipeline not initialized"
                return health_result
            
            # Check all components
            component_healths = {}
            
            # Check ingestor
            ingestor_health = await self._ingestor.healthcheck()
            component_healths["ingestor"] = ingestor_health
            
            # Check preprocessor - now with await
            preprocessor_health = await self._preprocessor.healthcheck()
            component_healths["preprocessor"] = preprocessor_health
            
            # Check embedder
            embedder_health = await self._embedder.healthcheck()
            component_healths["embedder"] = embedder_health
            
            # Check vector store - needs await if async
            try:
                # Try to use as async if available
                vector_store_health = await self._vector_store.healthcheck()
            except (TypeError, AttributeError):
                # Fall back to sync if not async
                vector_store_health = self._vector_store.healthcheck()
            
            component_healths["vector_store"] = vector_store_health
            
            # Check if all components are healthy
            all_healthy = all([
                ingestor_health.get("healthy", False),
                preprocessor_health.get("healthy", False),
                embedder_health.get("healthy", False),
                vector_store_health.get("healthy", False)
            ])
            
            health_result["healthy"] = all_healthy
            health_result["message"] = "All components are healthy" if all_healthy else "One or more components are unhealthy"
            health_result["details"]["components"] = component_healths
            
            return health_result
            
        except Exception as e:
            health_result["message"] = f"Health check error: {str(e)}"
            health_result["details"]["error"] = str(e)
            health_result["details"]["error_type"] = type(e).__name__
            return health_result
    
    def get_ingestion_metrics(self, ingestor_id: str) -> Dict[str, Any]:
        """
        Get metrics for an ingestor.
        
        Args:
            ingestor_id: Unique identifier for the ingestor
            
        Returns:
            Dict[str, Any]: Metrics information
        """
        if not self._is_initialized:
            raise IngestionPipelineError("Pipeline not initialized. Call initialize() first.")
        
        try:
            state = self._state_manager.get_state(ingestor_id)
            last_timestamp = state.get("last_timestamp", 0)
            metadata = state.get("additional_metadata", {})
            
            metrics = {
                "ingestor_id": ingestor_id,
                "last_run_timestamp": last_timestamp,
                "last_run_date": datetime.fromtimestamp(last_timestamp).isoformat() if last_timestamp else None,
                "total_messages_processed": metadata.get("total_messages_processed", 0),
                "chats_processed": len(metadata.get("chats_processed", [])),
                "chat_ids": metadata.get("chats_processed", []),
                "earliest_message_date": metadata.get("earliest_message_date"),
                "latest_message_date": metadata.get("latest_message_date"),
                "status": metadata.get("processing_status", "unknown")
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error({
                "action": "PIPELINE_METRICS_ERROR",
                "message": f"Failed to get metrics for ingestor {ingestor_id}: {str(e)}",
                "data": {"ingestor_id": ingestor_id, "error": str(e)}
            })
            raise IngestionPipelineError(f"Failed to get metrics: {str(e)}") from e
    
    def _finalize_results(self, results: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
        """
        Finalize the results dictionary with timing information.
        
        Args:
            results: Current results dictionary
            start_time: Start time of the ingestion run
            
        Returns:
            Dict[str, Any]: Updated results dictionary
        """
        end_time = datetime.now(timezone.utc)
        results["end_time"] = end_time
        results["duration"] = (end_time - start_time).total_seconds()
        return results
    
    def stop(self) -> None:
        """
        Stop the ingestion process.
        
        This method is a no-op since we're not using a scheduler anymore, but
        it's kept for API compatibility.
        """
        self.logger.info({
            "action": "PIPELINE_STOP_NOOP",
            "message": "Stop called, but no scheduler is running (single run mode)"
        }) 