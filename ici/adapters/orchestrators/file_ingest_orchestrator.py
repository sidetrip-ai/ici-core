"""
FileIngestOrchestrator implementation for processing chat files.

This orchestrator periodically scans for unprocessed telegram chat files,
preprocesses them, generates embeddings, and stores them in a vector database.
"""

import os
import asyncio
import traceback
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from ici.core.interfaces.orchestrator import Orchestrator
from ici.core.exceptions import OrchestratorError
from ici.adapters.loggers.structured_logger import StructuredLogger
from ici.adapters.storage.telegram.enhanced_file_manager import EnhancedFileManager
from ici.adapters.preprocessors.telegram import TelegramPreprocessor
from ici.adapters.embedders.sentence_transformer import SentenceTransformerEmbedder
from ici.adapters.vector_stores.chroma import ChromaDBStore


class FileIngestOrchestrator(Orchestrator):
    """
    Orchestrator for processing unprocessed Telegram chat files.
    
    This orchestrator periodically scans for unprocessed Telegram chat files,
    preprocesses them, embeds the content, and stores them in a vector database.
    """
    
    def __init__(self, logger_name: str = "file_ingest_orchestrator"):
        """
        Initialize the FileIngestOrchestrator.
        
        Args:
            logger_name: Name to use for the logger
        """
        self.logger = StructuredLogger(name=logger_name)
        self._is_initialized = False
        
        # Component references
        self._file_manager = None
        self._preprocessor = None
        self._embedder = None
        self._vector_store = None
        
        # Processing control
        self._processing_task = None
        self._should_continue = False
        
        # Hardcoded parameters
        self._check_interval_seconds = 300  # 5 minutes
        self._processing_batch_size = 10
        self._vector_store_collection = "telegram_chats"
        self._retry_count = 3
    
    async def initialize(self) -> None:
        """
        Initialize the orchestrator with all required components.
        
        Returns:
            None
            
        Raises:
            OrchestratorError: If initialization fails
        """
        try:
            self.logger.info({
                "action": "FILE_ORCHESTRATOR_INIT_START",
                "message": "Initializing FileIngestOrchestrator"
            })
            
            # Initialize file manager
            self._file_manager = EnhancedFileManager(
                logger=StructuredLogger(name=f"{self.logger.name}.file_manager")
            )
            
            # Initialize preprocessor
            self._preprocessor = TelegramPreprocessor(
                logger_name=f"{self.logger.name}.preprocessor"
            )
            await self._preprocessor.initialize()
            
            # Initialize embedder
            self._embedder = SentenceTransformerEmbedder(
                logger_name=f"{self.logger.name}.embedder"
            )
            await self._embedder.initialize()
            
            # Initialize vector store
            self._vector_store = ChromaDBStore(
                logger_name=f"{self.logger.name}.vector_store"
            )
            await self._vector_store.initialize()
            
            self._is_initialized = True
            
            self.logger.info({
                "action": "FILE_ORCHESTRATOR_INIT_SUCCESS",
                "message": "FileIngestOrchestrator initialized successfully"
            })
            
        except Exception as e:
            self.logger.error({
                "action": "FILE_ORCHESTRATOR_INIT_ERROR",
                "message": f"Failed to initialize orchestrator: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"FileIngestOrchestrator initialization failed: {str(e)}") from e
    
    async def start_processing(self) -> None:
        """
        Start the periodic file processing.
        
        This method initiates a background task that periodically checks for 
        and processes unprocessed files.
        
        Returns:
            None
            
        Raises:
            OrchestratorError: If starting processing fails
        """
        if not self._is_initialized:
            raise OrchestratorError("FileIngestOrchestrator must be initialized before starting processing")
        
        if self._processing_task is not None:
            self.logger.warning({
                "action": "FILE_ORCHESTRATOR_ALREADY_RUNNING",
                "message": "File processing is already running"
            })
            return
        
        try:
            self._should_continue = True
            self._processing_task = asyncio.create_task(self._periodic_processing())
            
            self.logger.info({
                "action": "FILE_ORCHESTRATOR_PROCESSING_STARTED",
                "message": "Started periodic file processing",
                "data": {
                    "check_interval_seconds": self._check_interval_seconds,
                    "batch_size": self._processing_batch_size
                }
            })
        except Exception as e:
            self._should_continue = False
            self.logger.error({
                "action": "FILE_ORCHESTRATOR_START_ERROR",
                "message": f"Failed to start file processing: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Failed to start file processing: {str(e)}") from e
    
    async def stop_processing(self) -> None:
        """
        Stop the periodic file processing.
        
        This method halts the background processing task.
        
        Returns:
            None
            
        Raises:
            OrchestratorError: If stopping processing fails
        """
        if not self._processing_task:
            self.logger.warning({
                "action": "FILE_ORCHESTRATOR_NOT_RUNNING",
                "message": "File processing is not running"
            })
            return
        
        try:
            self._should_continue = False
            
            # Wait for the task to complete
            if not self._processing_task.done():
                self._processing_task.cancel()
                try:
                    await self._processing_task
                except asyncio.CancelledError:
                    pass
            
            self._processing_task = None
            
            self.logger.info({
                "action": "FILE_ORCHESTRATOR_PROCESSING_STOPPED",
                "message": "Stopped periodic file processing"
            })
        except Exception as e:
            self.logger.error({
                "action": "FILE_ORCHESTRATOR_STOP_ERROR",
                "message": f"Failed to stop file processing: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Failed to stop file processing: {str(e)}") from e
    
    async def _periodic_processing(self) -> None:
        """
        Periodically process unprocessed files.
        
        This method runs in the background and periodically checks for and
        processes unprocessed files.
        """
        while self._should_continue:
            try:
                # Process a batch of files
                await self.process_files()
                
                # Wait for the next check
                await asyncio.sleep(self._check_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error({
                    "action": "FILE_ORCHESTRATOR_PERIODIC_ERROR",
                    "message": f"Error in periodic processing: {str(e)}",
                    "data": {"error": str(e), "error_type": type(e).__name__}
                })
                # Continue with next iteration after error
                await asyncio.sleep(self._check_interval_seconds)
    
    async def process_files(self) -> Dict[str, Any]:
        """
        Process a batch of unprocessed files.
        
        This method identifies unprocessed files, processes them, and updates
        their status.
        
        Returns:
            Dict[str, Any]: Summary of the processing results
        """
        if not self._is_initialized:
            raise OrchestratorError("FileIngestOrchestrator must be initialized before processing files")
        
        start_time = datetime.now()
        results = {
            "start_time": start_time,
            "files_processed": 0,
            "files_failed": 0,
            "files_attempted": 0,
            "details": {}
        }
        
        try:
            # Get list of unprocessed files
            unprocessed_files = self._file_manager.list_conversations(processed=False)
            batch_size = min(len(unprocessed_files), self._processing_batch_size)
            files_to_process = unprocessed_files[:batch_size]
            
            self.logger.info({
                "action": "FILE_ORCHESTRATOR_PROCESSING_BATCH",
                "message": f"Processing batch of {len(files_to_process)} files",
                "data": {
                    "total_unprocessed": len(unprocessed_files),
                    "batch_size": batch_size
                }
            })

            if len(files_to_process) == 0:
                self.logger.info({
                    "action": "FILE_ORCHESTRATOR_NO_FILES_TO_PROCESS",
                    "message": "No files to process"
                })
                print("--------------------------------")
                print("No files to process")
                print("--------------------------------")
            
            # Process each file
            for file_id in files_to_process:
                results["files_attempted"] += 1
                
                try:
                    await self.process_file(file_id)
                    results["files_processed"] += 1
                    results["details"][file_id] = "success"
                except Exception as e:
                    results["files_failed"] += 1
                    results["details"][file_id] = f"error: {str(e)}"
                    self.logger.error({
                        "action": "FILE_ORCHESTRATOR_FILE_PROCESSING_ERROR",
                        "message": f"Error processing file {file_id}: {str(e)}",
                        "data": {"file_id": file_id, "error": str(e)}
                    })
                    # Continue with next file
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            results["end_time"] = end_time
            results["duration"] = duration
            
            self.logger.info({
                "action": "FILE_ORCHESTRATOR_BATCH_COMPLETE",
                "message": f"Completed processing batch of files",
                "data": {
                    "files_processed": results["files_processed"],
                    "files_failed": results["files_failed"],
                    "duration_seconds": duration
                }
            })
            
            return results
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            results["end_time"] = end_time
            results["duration"] = duration
            results["error"] = str(e)
            
            self.logger.error({
                "action": "FILE_ORCHESTRATOR_BATCH_ERROR",
                "message": f"Error processing batch of files: {str(e)}",
                "data": {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_seconds": duration
                }
            })
            
            return results
    
    async def process_file(self, file_id: str) -> None:
        """
        Process a single file with the all-or-nothing approach.
        
        Args:
            file_id: ID of the file to process
            
        Raises:
            Exception: If any step of processing fails
        """
        self.logger.info({
            "action": "FILE_ORCHESTRATOR_PROCESSING_FILE",
            "message": f"Processing file {file_id}",
            "data": {"file_id": file_id}
        })
        
        # All-or-nothing approach - any exception will propagate and prevent marking as processed
        
        # 1. Load the file
        conversation = self._file_manager.load_conversation(file_id, require_unprocessed=True)

        print("--------------------------------")
        print(conversation)
        print("--------------------------------")
        
        # 2. Preprocess the data
        # Extract messages from conversation - per schema, messages is a dict of message_id -> message_data
        messages_dict = conversation.get("messages", {})
        print("--------------------------------")
        print(messages_dict)
        print("--------------------------------")
        if not messages_dict:
            raise ValueError(f"No messages found in conversation {file_id}")
            
        # Convert the dict of messages to a list of message objects with conversation_id
        messages_list = []
        for msg_id, msg_data in messages_dict.items():
            # Create a proper message object with all required fields
            msg_obj = {
                "id": msg_id,
                "conversation_id": file_id,
                **msg_data  # Include all message data fields
            }
            messages_list.append(msg_obj)

        print("--------------------------------")
        print(messages_list)
        print("--------------------------------")

        import time;
        time.sleep(10)
            
        if not messages_list:
            raise ValueError(f"No valid messages found in conversation {file_id} after conversion")
            
        processed_docs = await self._preprocessor.process(messages_list)
        
        if not processed_docs:
            raise ValueError(f"Preprocessing yielded no documents for conversation {file_id}")
            
        self.logger.info({
            "action": "FILE_ORCHESTRATOR_PREPROCESSING_COMPLETE",
            "message": f"Preprocessed file {file_id}",
            "data": {"file_id": file_id, "document_count": len(processed_docs)}
        })
        
        # 3. Generate embeddings for each document
        documents_with_embeddings = []
        
        for doc in processed_docs:
            # Get the text and metadata
            text = doc.get("text", "")
            metadata = doc.get("metadata", {})
            
            # Add file ID to metadata
            metadata["source_file_id"] = file_id
            metadata["processing_time"] = datetime.now().isoformat()
            
            # Generate embedding
            embedding, _ = await self._embedder.embed(text)
            
            # Create document with embedding
            documents_with_embeddings.append({
                "text": text,
                "metadata": metadata,
                "vector": embedding
            })
        
        self.logger.info({
            "action": "FILE_ORCHESTRATOR_EMBEDDING_COMPLETE",
            "message": f"Generated embeddings for file {file_id}",
            "data": {"file_id": file_id, "document_count": len(documents_with_embeddings)}
        })
        
        # 4. Store documents in vector store
        await self._vector_store.store_documents(
            documents_with_embeddings, 
            collection_name=self._vector_store_collection
        )
        
        self.logger.info({
            "action": "FILE_ORCHESTRATOR_STORAGE_COMPLETE",
            "message": f"Stored documents from file {file_id} in vector store",
            "data": {
                "file_id": file_id,
                "document_count": len(documents_with_embeddings),
                "collection": self._vector_store_collection
            }
        })
        
        # 5. Mark file as processed
        self._file_manager.mark_as_processed(file_id)
        
        self.logger.info({
            "action": "FILE_ORCHESTRATOR_FILE_COMPLETE",
            "message": f"Successfully processed file {file_id}",
            "data": {"file_id": file_id}
        })
    
    async def close(self) -> None:
        """
        Clean up resources and stop processing.
        
        Returns:
            None
            
        Raises:
            OrchestratorError: If closing fails
        """
        try:
            # Stop processing if running
            if self._processing_task is not None:
                await self.stop_processing()
            
            # Close vector store if initialized
            if self._vector_store is not None:
                await self._vector_store.close()
            
            self.logger.info({
                "action": "FILE_ORCHESTRATOR_CLOSED",
                "message": "FileIngestOrchestrator closed successfully"
            })
        except Exception as e:
            self.logger.error({
                "action": "FILE_ORCHESTRATOR_CLOSE_ERROR",
                "message": f"Failed to close orchestrator: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Failed to close orchestrator: {str(e)}") from e
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Check the health of the orchestrator and its components.
        
        Returns:
            Dict[str, Any]: Health status information
            
        Raises:
            OrchestratorError: If the health check encounters an error
        """
        health_result = {
            "healthy": False,
            "message": "FileIngestOrchestrator health check failed",
            "details": {
                "initialized": self._is_initialized,
                "processing_active": self._processing_task is not None and not self._processing_task.done(),
                "components": {}
            }
        }
        
        try:
            if not self._is_initialized:
                health_result["message"] = "FileIngestOrchestrator not initialized"
                return health_result
            
            # Check file manager
            try:
                stats = self._file_manager.get_conversation_stats()
                health_result["details"]["components"]["file_manager"] = {
                    "healthy": True,
                    "unprocessed_count": stats.get("unprocessed_count", 0)
                }
            except Exception as e:
                health_result["details"]["components"]["file_manager"] = {
                    "healthy": False,
                    "error": str(e)
                }
                return health_result
            
            # Check preprocessor
            try:
                preprocessor_health = await self._preprocessor.healthcheck()
                health_result["details"]["components"]["preprocessor"] = preprocessor_health
                
                if not preprocessor_health.get("healthy", False):
                    return health_result
            except Exception as e:
                health_result["details"]["components"]["preprocessor"] = {
                    "healthy": False,
                    "error": str(e)
                }
                return health_result
            
            # Check embedder
            try:
                embedder_health = self._embedder.healthcheck()
                health_result["details"]["components"]["embedder"] = embedder_health
                
                if not embedder_health.get("healthy", False):
                    return health_result
            except Exception as e:
                health_result["details"]["components"]["embedder"] = {
                    "healthy": False,
                    "error": str(e)
                }
                return health_result
            
            # Check vector store
            try:
                vector_store_health = self._vector_store.healthcheck()
                health_result["details"]["components"]["vector_store"] = vector_store_health
                
                if not vector_store_health.get("healthy", False):
                    return health_result
            except Exception as e:
                health_result["details"]["components"]["vector_store"] = {
                    "healthy": False,
                    "error": str(e)
                }
                return health_result
            
            # All checks passed
            health_result["healthy"] = True
            health_result["message"] = "FileIngestOrchestrator is healthy"
            
            return health_result
            
        except Exception as e:
            self.logger.error({
                "action": "FILE_ORCHESTRATOR_HEALTHCHECK_ERROR",
                "message": f"Failed to perform health check: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            health_result["message"] = f"Health check error: {str(e)}"
            return health_result
    
    # Required by the Orchestrator interface but not implemented for this specialized orchestrator
    
    async def process_query(self, source: str, user_id: str, query: str, additional_info: Dict[str, Any]) -> str:
        """Not implemented for FileIngestOrchestrator."""
        raise NotImplementedError("FileIngestOrchestrator does not support query processing")
    
    async def configure(self, config: Dict[str, Any]) -> None:
        """Not implemented for FileIngestOrchestrator."""
        raise NotImplementedError("FileIngestOrchestrator does not support dynamic configuration")
    
    def get_rules(self, user_id: str) -> List[Dict[str, Any]]:
        """Not implemented for FileIngestOrchestrator."""
        raise NotImplementedError("FileIngestOrchestrator does not support rules")
    
    async def build_context(self, user_id: str) -> Dict[str, Any]:
        """Not implemented for FileIngestOrchestrator."""
        raise NotImplementedError("FileIngestOrchestrator does not support context building") 