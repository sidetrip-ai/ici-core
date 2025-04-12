"""
Default ingestion pipeline implementation supporting multiple ingestor types.

This pipeline implements a unified approach for processing data from
different sources (currently Telegram and WhatsApp) using a component
registry system.
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from ici.core.interfaces import IngestionPipeline
from ici.core.interfaces.embedder import Embedder
from ici.core.interfaces.vector_store import VectorStore
from ici.adapters.ingestors import TelegramIngestor, WhatsAppIngestor, GitHubIngestor
from ici.adapters.preprocessors import TelegramPreprocessor, WhatsAppPreprocessor, GitHubPreprocessor
from ici.adapters.loggers import StructuredLogger
from ici.utils.config import get_component_config, load_config
from ici.core.exceptions import (
    IngestionPipelineError, ConfigurationError, DataFetchError, 
    PreprocessorError, EmbeddingError, VectorStoreError
)
from ici.utils.datetime_utils import from_timestamp, ensure_tz_aware
from ici.utils.state_manager import StateManager


class DefaultIngestionPipeline(IngestionPipeline):
    """
    Pipeline implementation for ingesting data from multiple sources.
    
    This pipeline coordinates the data flow from various ingestors to their
    corresponding preprocessors, and then to a shared embedder and vector store.
    State is tracked separately for each ingestor.
    
    Currently supports:
    - Telegram
    - WhatsApp
    """
    
    def __init__(self, logger_name: str = "default_ingestion_pipeline"):
        """
        Initialize the DefaultIngestionPipeline.
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = StructuredLogger(name=logger_name)
        self._is_initialized = False
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        
        # Components
        self._embedder = None
        self._vector_store = None
        self._state_manager = None
        
        # Ingestor registry - maps ingestor IDs to their components
        self._ingestors = {}
        
        # Configuration
        self._batch_size = 100
        self._schedule_interval_minutes = 60
    
    async def initialize(self) -> None:
        """
        Initialize the pipeline with configuration parameters.
        
        This method loads the various components needed for the pipeline:
        - Ingestors (Telegram, WhatsApp)
        - Preprocessors
        - Embedder
        - Vector Store
        - State Manager
        
        Returns:
            None
            
        Raises:
            IngestionPipelineError: If initialization fails
        """
        if self._is_initialized:
            return
            
        try:
            self.logger.info({
                "action": "PIPELINE_INITIALIZING",
                "message": "Initializing default ingestion pipeline"
            })
            
            # Load configuration
            config = load_config(self._config_path)
            
            # Get pipeline specific config if available
            pipeline_config = get_component_config("pipelines.default", self._config_path)
            if pipeline_config:
                if "batch_size" in pipeline_config:
                    self._batch_size = int(pipeline_config["batch_size"])
                
                if "schedule" in pipeline_config and "interval_minutes" in pipeline_config["schedule"]:
                    self._schedule_interval_minutes = int(pipeline_config["schedule"]["interval_minutes"])
            
            # Initialize shared components
            
            # 1. Embedder - Use the one from config
            embedder_config = get_component_config("embedders.sentence_transformer", self._config_path)
            self._embedder = await self._load_embedder(embedder_config)
            
            # 2. Vector Store - Use ChromaDB from config
            vector_store_config = get_component_config("vector_stores.chroma", self._config_path)
            self._vector_store = await self._load_vector_store(vector_store_config)
            
            # 3. State Manager
            state_manager_config = get_component_config("state_manager", self._config_path)
            db_path = state_manager_config.get("db_path", "./db/sql/ingestor_state.db")
            self._state_manager = StateManager(db_path=db_path)
            self._state_manager.initialize()
            
            # Mark pipeline as initialized before initializing ingestors
            self._is_initialized = True
            
            # Initialize ingestors based on configuration

            # For whatsapp pipeline
            whatsapp_pipeline_config = get_component_config("orchestrator.pipelines.whatsapp", self._config_path)
            if whatsapp_pipeline_config:
                whatsapp_ingestor_config = get_component_config("orchestrator.pipelines.whatsapp.ingestor.whatsapp", self._config_path)
                if whatsapp_ingestor_config:
                    await self._initialize_whatsapp_ingestor(whatsapp_ingestor_config)
            
            # For GitHub pipeline
            github_pipeline_config = get_component_config("orchestrator.pipelines.github", self._config_path)
            if github_pipeline_config:
                github_ingestor_config = get_component_config("orchestrator.pipelines.github.ingestor.github", self._config_path)
                if github_ingestor_config:
                    await self._initialize_github_ingestor(github_ingestor_config)
            
            self.logger.info({
                "action": "PIPELINE_INITIALIZED",
                "message": "Default ingestion pipeline initialized successfully",
                "data": {
                    "batch_size": self._batch_size,
                    "schedule_interval_minutes": self._schedule_interval_minutes,
                    "registered_ingestors": list(self._ingestors.keys())
                }
            })
            
        except Exception as e:
            error_message = f"Failed to initialize default ingestion pipeline: {str(e)}"
            self.logger.error({
                "action": "PIPELINE_INITIALIZATION_ERROR",
                "message": error_message,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise IngestionPipelineError(error_message) from e
    
    async def _initialize_telegram_ingestor(self, config: Dict[str, Any]) -> None:
        """
        Initialize and register the Telegram ingestor and preprocessor.
        
        Args:
            config: Telegram ingestor configuration
            
        Raises:
            ConfigurationError: If initialization fails
        """
        try:
            # Create and initialize Telegram ingestor
            telegram_ingestor = TelegramIngestor()
            await telegram_ingestor.initialize()
            
            # Create and initialize Telegram preprocessor
            telegram_preprocessor = TelegramPreprocessor()
            await telegram_preprocessor.initialize()
            
            # Register the Telegram ingestor with a unique ID
            ingestor_id = "@user/telegram_ingestor"
            self.register_ingestor(
                ingestor_id=ingestor_id,
                ingestor=telegram_ingestor,
                preprocessor=telegram_preprocessor
            )
            
            self.logger.info({
                "action": "TELEGRAM_INGESTOR_REGISTERED",
                "message": f"Registered Telegram ingestor with ID: {ingestor_id}"
            })
            
        except Exception as e:
            error_message = f"Failed to initialize Telegram ingestor: {str(e)}"
            self.logger.error({
                "action": "TELEGRAM_INITIALIZATION_ERROR",
                "message": error_message,
                "data": {"error": str(e)}
            })
            raise ConfigurationError(error_message) from e
    
    async def _initialize_whatsapp_ingestor(self, config: Dict[str, Any]) -> None:
        """
        Initialize and register the WhatsApp ingestor and preprocessor.
        
        Args:
            config: WhatsApp ingestor configuration
            
        Raises:
            ConfigurationError: If initialization fails
        """
        try:
            # Create and initialize WhatsApp ingestor
            whatsapp_ingestor = WhatsAppIngestor()
            await whatsapp_ingestor.initialize()
            
            # Create and initialize WhatsApp preprocessor
            whatsapp_preprocessor = WhatsAppPreprocessor()
            await whatsapp_preprocessor.initialize()
            
            # Register the WhatsApp ingestor with a unique ID
            ingestor_id = "@user/whatsapp_ingestor"
            self.register_ingestor(
                ingestor_id=ingestor_id,
                ingestor=whatsapp_ingestor,
                preprocessor=whatsapp_preprocessor
            )
            
            self.logger.info({
                "action": "WHATSAPP_INGESTOR_REGISTERED",
                "message": f"Registered WhatsApp ingestor with ID: {ingestor_id}"
            })
            
        except Exception as e:
            error_message = f"Failed to initialize WhatsApp ingestor: {str(e)}"
            self.logger.error({
                "action": "WHATSAPP_INITIALIZATION_ERROR",
                "message": error_message,
                "data": {"error": str(e)}
            })
            raise ConfigurationError(error_message) from e
    
    async def _initialize_github_ingestor(self, config: Dict[str, Any]) -> None:
        """
        Initialize and register the GitHub ingestor and preprocessor.
        
        Args:
            config: GitHub ingestor configuration
            
        Raises:
            ConfigurationError: If initialization fails
        """
        try:
            # Create and initialize GitHub ingestor
            github_ingestor = GitHubIngestor()
            await github_ingestor.initialize()
            
            # Create and initialize GitHub preprocessor
            github_preprocessor = GitHubPreprocessor()
            await github_preprocessor.initialize()
            
            # Register the GitHub ingestor with a unique ID
            ingestor_id = "@user/github_ingestor"
            self.register_ingestor(
                ingestor_id=ingestor_id,
                ingestor=github_ingestor,
                preprocessor=github_preprocessor
            )
            
            self.logger.info({
                "action": "GITHUB_INGESTOR_REGISTERED",
                "message": f"Registered GitHub ingestor with ID: {ingestor_id}"
            })
            
        except Exception as e:
            error_message = f"Failed to initialize GitHub ingestor: {str(e)}"
            self.logger.error({
                "action": "GITHUB_INITIALIZATION_ERROR",
                "message": error_message,
                "data": {"error": str(e)}
            })
            raise ConfigurationError(error_message) from e
    
    async def _load_embedder(self, config: Dict[str, Any]) -> Embedder:
        """
        Load embedder component based on configuration.
        
        Args:
            config: Embedder configuration
            
        Returns:
            Embedder: Initialized embedder instance
            
        Raises:
            ConfigurationError: If embedder loading fails
        """
        from ici.adapters.embedders import SentenceTransformerEmbedder
        
        try:
            embedder = SentenceTransformerEmbedder()
            # Initialize the embedder asynchronously with await
            await embedder.initialize()
            return embedder
        except Exception as e:
            error_message = f"Failed to load embedder: {str(e)}"
            self.logger.error({
                "action": "EMBEDDER_LOAD_ERROR",
                "message": error_message,
                "data": {"error": str(e)}
            })
            raise ConfigurationError(error_message) from e
    
    async def _load_vector_store(self, config: Dict[str, Any]) -> VectorStore:
        """
        Load vector store component based on configuration.
        
        Args:
            config: Vector store configuration
            
        Returns:
            VectorStore: Initialized vector store instance
            
        Raises:
            ConfigurationError: If vector store loading fails
        """
        from ici.adapters.vector_stores import ChromaDBStore
        
        try:
            vector_store = ChromaDBStore()
            await vector_store.initialize()
            return vector_store
        except Exception as e:
            error_message = f"Failed to load vector store: {str(e)}"
            self.logger.error({
                "action": "VECTOR_STORE_LOAD_ERROR",
                "message": error_message,
                "data": {"error": str(e)}
            })
            raise ConfigurationError(error_message) from e
    
    def register_ingestor(self, ingestor_id: str, ingestor: Any, preprocessor: Any) -> None:
        """
        Register an ingestor and its preprocessor with the pipeline.
        
        Args:
            ingestor_id: Unique identifier for the ingestor
            ingestor: Ingestor instance
            preprocessor: Preprocessor instance
            
        Raises:
            IngestionPipelineError: If registration fails
        """
        if not self._is_initialized:
            raise IngestionPipelineError("Pipeline not initialized. Call initialize() first.")
        
        try:
            # Check if ingestor already exists
            if ingestor_id in self._ingestors:
                self.logger.info({
                    "action": "PIPELINE_INGESTOR_EXISTS",
                    "message": f"Ingestor {ingestor_id} already registered",
                    "data": {"ingestor_id": ingestor_id}
                })
                return
            
            # Register the ingestor and preprocessor
            self._ingestors[ingestor_id] = {
                "ingestor": ingestor,
                "preprocessor": preprocessor
            }
            
            # Initialize with empty state if needed
            existing_state = self._state_manager.get_state(ingestor_id)
            if existing_state.get("last_timestamp", 0) == 0:
                self._state_manager.set_state(
                    ingestor_id=ingestor_id,
                    last_timestamp=0,
                    additional_metadata={
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
    
    async def run_ingestion(self, ingestor_id: str) -> Dict[str, Any]:
        """
        Execute the full ingestion pipeline for a specific ingestor.
        
        This method orchestrates the full data flow:
        1. Retrieves ingestor state from the database
        2. Fetches data from the ingestor based on state
        3. Preprocesses data into standardized documents
        4. Generates embeddings for documents
        5. Stores documents with vectors in the vector store
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
        
        if ingestor_id not in self._ingestors:
            raise IngestionPipelineError(f"Unknown ingestor ID: {ingestor_id}")
        
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
                "message": f"Starting ingestion for {ingestor_id}",
                "data": {"ingestor_id": ingestor_id}
            })
            
            # Get components for this ingestor
            components = self._ingestors[ingestor_id]
            ingestor = components["ingestor"]
            preprocessor = components["preprocessor"]
            
            # Get ingestor state
            state = self._state_manager.get_state(ingestor_id)
            last_timestamp = state.get("last_timestamp", 0)
            metadata = state.get("additional_metadata", {})
            
            # For WhatsApp ingestor, check authentication if needed
            if isinstance(ingestor, WhatsAppIngestor):
                # Check if WhatsApp is authenticated
                if not await ingestor.is_authenticated():
                    # Get authentication URL
                    auth_url = await ingestor.get_authentication_url()
                    
                    self.logger.info({
                        "action": "AUTHENTICATION_REQUIRED",
                        "message": f"WhatsApp authentication required. Please scan QR code at: {auth_url}",
                        "data": {"auth_url": auth_url}
                    })
                    
                    # Store authentication URL in results
                    results["authentication_required"] = True
                    results["authentication_url"] = auth_url
                    
                    # Wait for authentication (with timeout)
                    auth_timeout = 300  # 5 minutes
                    authenticated = await ingestor.wait_for_authentication(timeout_seconds=auth_timeout)
                    
                    if not authenticated:
                        error_message = f"Authentication timed out after {auth_timeout} seconds"
                        self.logger.warning({
                            "action": "AUTHENTICATION_TIMEOUT",
                            "message": error_message
                        })
                        results["errors"].append(error_message)
                        results["message"] = "Authentication timeout"
                        return self._finalize_results(results, start_time)
            
            # Fetch data based on ingestor type and state
            raw_data = None
            
            # Determine fetch mode based on state
            if last_timestamp == 0:
                # First run - fetch all historical data
                raw_data = await ingestor.fetch_full_data()
            else:
                # Incremental run - fetch new data since last timestamp
                # Convert timestamp to timezone-aware datetime
                last_datetime = datetime.fromtimestamp(last_timestamp, tz=timezone.utc)
                raw_data = await ingestor.fetch_new_data(since=last_datetime)
            
            # Check if data was retrieved
            if not raw_data:
                self.logger.info({
                    "action": "PIPELINE_NO_DATA",
                    "message": "No new data to process"
                })
                results["success"] = True
                results["message"] = "No new data to process"
                return self._finalize_results(results, start_time)
            
            # Check data format based on ingestor type
            if isinstance(ingestor, (TelegramIngestor, WhatsAppIngestor)):
                if not (raw_data.get("messages") or raw_data.get("conversations")):
                    self.logger.info({
                        "action": "PIPELINE_NO_DATA",
                        "message": "No new messages or conversations to process"
                    })
                    results["success"] = True
                    results["message"] = "No new data to process"
                    return self._finalize_results(results, start_time)
            elif isinstance(ingestor, GitHubIngestor):
                if not raw_data.get("repositories"):
                    self.logger.info({
                        "action": "PIPELINE_NO_DATA",
                        "message": "No new GitHub repositories to process"
                    })
                    results["success"] = True
                    results["message"] = "No new data to process"
                    return self._finalize_results(results, start_time)
            
            # Process messages - preprocessor handles the specific ingestor's data format
            documents = await preprocessor.preprocess(raw_data)
            
            if not documents:
                self.logger.info({
                    "action": "PIPELINE_NO_DOCUMENTS",
                    "message": "No documents generated from preprocessing"
                })
                results["success"] = True
                results["message"] = "No documents generated"
                return self._finalize_results(results, start_time)
            
            total_documents = len(documents)
            self.logger.info({
                "action": "PREPROCESSING_COMPLETE",
                "message": f"Generated {total_documents} documents from raw data",
                "data": {"document_count": total_documents}
            })
            
            # Process documents in batches
            total_documents_processed = 0
            latest_timestamp = last_timestamp
            
            # Find messages sorted by timestamp for state tracking
            if isinstance(ingestor, (TelegramIngestor, WhatsAppIngestor)):
                messages = raw_data.get("messages", [])
                if messages:
                    sorted_messages = sorted(messages, key=lambda m: m.get("timestamp", 0))
                    
                    # Get timestamp from latest message
                    latest_message = sorted_messages[-1]
                    # Convert to seconds if needed (WhatsApp uses milliseconds)
                    message_timestamp = latest_message.get("timestamp", 0)
                    if message_timestamp > 1600000000000:  # Likely milliseconds
                        message_timestamp = message_timestamp / 1000
                    
                    if message_timestamp > latest_timestamp:
                        latest_timestamp = message_timestamp
            elif isinstance(ingestor, GitHubIngestor):
                # For GitHub, we'll use the current time as the timestamp
                # since we're reading from a file and don't have real-time updates
                current_time = datetime.now(timezone.utc).timestamp()
                if current_time > latest_timestamp:
                    latest_timestamp = current_time
            
            # Process documents in batches
            for i in range(0, len(documents), self._batch_size):
                batch = documents[i:i + self._batch_size]
                
                try:
                    # Generate embeddings and store documents
                    document_list = []
                    vectors_list = []
                    
                    for doc in batch:
                        # Generate embeddings for the text
                        embedding, _ = await self._embedder.embed(doc["text"])
                        
                        # Add to document and vectors lists
                        document_list.append({
                            "text": doc["text"],
                            "metadata": doc["metadata"]
                        })
                        vectors_list.append(embedding)
                    
                    # Add to vector store
                    self._vector_store.add_documents(documents=document_list, vectors=vectors_list)
                    
                    # Update count
                    total_documents_processed += len(batch)
                    
                except Exception as e:
                    error_message = f"Error processing batch: {str(e)}"
                    self.logger.error({
                        "action": "BATCH_PROCESSING_ERROR",
                        "message": error_message,
                        "data": {"error": str(e), "batch_size": len(batch)}
                    })
                    results["errors"].append(error_message)
            
            # Update state with latest timestamp if newer messages were processed
            if latest_timestamp > last_timestamp and total_documents_processed > 0:
                # Update metadata with processing stats
                new_metadata = metadata.copy()
                new_metadata["last_run"] = datetime.now(timezone.utc).isoformat()
                new_metadata["total_documents_processed"] = metadata.get("total_documents_processed", 0) + total_documents_processed
                
                # Set state with new timestamp and metadata
                self._state_manager.set_state(
                    ingestor_id=ingestor_id,
                    last_timestamp=latest_timestamp,
                    additional_metadata=new_metadata
                )
                
                self.logger.info({
                    "action": "STATE_UPDATED",
                    "message": f"Updated timestamp to {datetime.fromtimestamp(latest_timestamp, tz=timezone.utc).isoformat()}",
                    "data": {
                        "last_timestamp": latest_timestamp,
                        "last_timestamp_iso": datetime.fromtimestamp(latest_timestamp, tz=timezone.utc).isoformat()
                    }
                })
            
            # Set success
            results["success"] = True
            results["documents_processed"] = total_documents_processed
            
            self.logger.info({
                "action": "PIPELINE_RUN_COMPLETE",
                "message": f"Ingestion completed successfully. Processed {total_documents_processed} documents.",
                "data": {"documents_processed": total_documents_processed}
            })
            
            return self._finalize_results(results, start_time)
            
        except Exception as e:
            error_message = f"Ingestion failed for {ingestor_id}: {str(e)}"
            self.logger.error({
                "action": "PIPELINE_RUN_ERROR",
                "message": error_message,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            results["errors"].append(error_message)
            return self._finalize_results(results, start_time)
    
    def _finalize_results(self, results: Dict[str, Any], start_time: datetime) -> Dict[str, Any]:
        """
        Finalize the results dictionary with timing information.
        
        Args:
            results: Results dictionary to finalize
            start_time: Start time of the ingestion run
            
        Returns:
            Dict[str, Any]: Finalized results
        """
        end_time = datetime.now(timezone.utc)
        results["end_time"] = end_time
        results["duration"] = (end_time - start_time).total_seconds()
        return results
    
    def get_ingestor_state(self, ingestor_id: str) -> Dict[str, Any]:
        """
        Get the current state for an ingestor.
        
        Args:
            ingestor_id: Unique identifier for the ingestor
            
        Returns:
            Dict[str, Any]: Current state information
            
        Raises:
            IngestionPipelineError: If getting state fails
        """
        if not self._is_initialized:
            raise IngestionPipelineError("Pipeline not initialized. Call initialize() first.")
        
        try:
            return self._state_manager.get_state(ingestor_id)
        except Exception as e:
            self.logger.error({
                "action": "PIPELINE_GET_STATE_ERROR",
                "message": f"Failed to get ingestor state for {ingestor_id}: {str(e)}",
                "data": {"ingestor_id": ingestor_id, "error": str(e)}
            })
            raise IngestionPipelineError(f"Failed to get ingestor state: {str(e)}") from e
    
    def set_ingestor_state(self, ingestor_id: str, last_timestamp: int, additional_metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Set the state for an ingestor.
        
        Args:
            ingestor_id: Unique identifier for the ingestor
            last_timestamp: Last processed timestamp
            additional_metadata: Additional metadata to store
            
        Raises:
            IngestionPipelineError: If setting state fails
        """
        if not self._is_initialized:
            raise IngestionPipelineError("Pipeline not initialized. Call initialize() first.")
        
        try:
            self._state_manager.set_state(
                ingestor_id=ingestor_id,
                last_timestamp=last_timestamp,
                additional_metadata=additional_metadata or {}
            )
            
            self.logger.info({
                "action": "PIPELINE_STATE_SET",
                "message": f"Set ingestor state for {ingestor_id}",
                "data": {"ingestor_id": ingestor_id}
            })
            
        except Exception as e:
            self.logger.error({
                "action": "PIPELINE_SET_STATE_ERROR",
                "message": f"Failed to set ingestor state for {ingestor_id}: {str(e)}",
                "data": {"ingestor_id": ingestor_id, "error": str(e)}
            })
            raise IngestionPipelineError(f"Failed to set ingestor state: {str(e)}") from e
    
    async def start(self) -> None:
        """
        Start the ingestion process for all registered ingestors.
        
        This method runs ingestion for all registered ingestors in sequence.
        
        Returns:
            None
            
        Raises:
            IngestionPipelineError: If starting the ingestion process fails
        """
        if not self._is_initialized:
            raise IngestionPipelineError("Pipeline not initialized. Call initialize() first.")
        
        if not self._ingestors:
            self.logger.warning({
                "action": "PIPELINE_NO_INGESTORS",
                "message": "No ingestors registered, nothing to run"
            })
            return
        
        self.logger.info({
            "action": "PIPELINE_START",
            "message": f"Starting ingestion for {len(self._ingestors)} registered ingestors"
        })
        
        results = {}
        
        for ingestor_id in self._ingestors.keys():
            try:
                result = await self.run_ingestion(ingestor_id)
                results[ingestor_id] = result
            except Exception as e:
                self.logger.error({
                    "action": "INGESTOR_RUN_ERROR",
                    "message": f"Error running ingestion for {ingestor_id}: {str(e)}",
                    "data": {"ingestor_id": ingestor_id, "error": str(e)}
                })
                results[ingestor_id] = {
                    "success": False,
                    "error": str(e)
                }
        
        self.logger.info({
            "action": "PIPELINE_COMPLETE",
            "message": "Completed ingestion for all registered ingestors",
            "data": {"results": results}
        })
    
    def stop(self) -> None:
        """
        Stop the ingestion process.
        
        This method currently does nothing as we don't have a continuous process.
        
        Returns:
            None
        """
        pass
    
    async def close(self) -> None:
        """
        Close the pipeline and release all resources.
        
        This method closes all components of the pipeline and releases any resources they hold.
        
        Returns:
            None
            
        Raises:
            IngestionPipelineError: If closing the pipeline fails
        """
        try:
            self.logger.info({
                "action": "PIPELINE_CLOSING",
                "message": "Closing default ingestion pipeline"
            })
            
            # Close all ingestors
            for ingestor_id, components in self._ingestors.items():
                ingestor = components["ingestor"]
                if hasattr(ingestor, "close"):
                    try:
                        await ingestor.close()
                    except Exception as e:
                        self.logger.warning({
                            "action": "INGESTOR_CLOSE_ERROR",
                            "message": f"Error closing ingestor {ingestor_id}: {str(e)}",
                            "data": {"ingestor_id": ingestor_id, "error": str(e)}
                        })
            
            # Close other components if needed
            # (Most components don't need explicit cleanup)
            
            self._is_initialized = False
            
            self.logger.info({
                "action": "PIPELINE_CLOSED",
                "message": "Default ingestion pipeline closed successfully"
            })
        except Exception as e:
            error_message = f"Failed to close default ingestion pipeline: {str(e)}"
            self.logger.error({
                "action": "PIPELINE_CLOSE_ERROR",
                "message": error_message,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise IngestionPipelineError(error_message) from e
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Perform a health check on the pipeline and its components.
        
        Returns:
            Dict[str, Any]: Health status information with component statuses
            
        Raises:
            IngestionPipelineError: If the health check fails
        """
        health_info = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {},
            "ingestors": {}
        }
        
        try:
            # Only perform detailed health check if initialized
            if not self._is_initialized:
                health_info["status"] = "not_initialized"
                return health_info
                
            # Check embedder (simple check - no async method typically)
            health_info["components"]["embedder"] = {"status": "ok" if self._embedder else "missing"}
            
            # Check vector store (simple check - no async method typically)
            health_info["components"]["vector_store"] = {"status": "ok" if self._vector_store else "missing"}
            
            # Check state manager
            try:
                # Simple status check - try to access database
                test_id = "_health_check_test"
                self._state_manager.get_state(test_id)
                health_info["components"]["state_manager"] = {"status": "ok"}
            except Exception as e:
                health_info["components"]["state_manager"] = {"status": "error", "message": str(e)}
                health_info["status"] = "degraded"
            
            # Check ingestors
            for ingestor_id, components in self._ingestors.items():
                ingestor = components["ingestor"]
                
                try:
                    if hasattr(ingestor, "healthcheck"):
                        ingestor_health = await ingestor.healthcheck()
                        health_info["ingestors"][ingestor_id] = ingestor_health
                    else:
                        health_info["ingestors"][ingestor_id] = {"status": "ok"}
                except Exception as e:
                    health_info["ingestors"][ingestor_id] = {"status": "error", "message": str(e)}
                    health_info["status"] = "degraded"
            
            return health_info
            
        except Exception as e:
            health_info["status"] = "error"
            health_info["error"] = str(e)
            return health_info 