"""
WhatsAppIngestOrchestrator implementation for WhatsApp-specific data ingestion.

This orchestrator is specialized for handling only WhatsApp data ingestion,
explicitly avoiding Telegram or other data sources.
"""

import os
import traceback
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from ici.core.interfaces.orchestrator import Orchestrator
from ici.core.interfaces.pipeline import IngestionPipeline
from ici.core.interfaces.vector_store import VectorStore
from ici.core.exceptions import OrchestratorError
from ici.utils.config import get_component_config, load_config
from ici.adapters.loggers.structured_logger import StructuredLogger
from ici.adapters.pipelines.default import DefaultIngestionPipeline
from ici.adapters.vector_stores.chroma import ChromaDBStore
from ici.adapters.embedders.sentence_transformer import SentenceTransformerEmbedder


class WhatsAppIngestOrchestrator(Orchestrator):
    """
    Orchestrator implementation focused solely on WhatsApp data ingestion.
    
    This orchestrator is specialized for managing the WhatsApp ingestion pipeline,
    explicitly avoiding Telegram or other data sources.
    """
    
    def __init__(self, logger_name: str = "whatsapp_ingest_orchestrator"):
        """
        Initialize the WhatsAppIngestOrchestrator.
        
        Args:
            logger_name: Name to use for the logger
        """
        self.logger = StructuredLogger(name=logger_name)
        self._is_initialized = False
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        
        # Component references
        self._pipeline: Optional[IngestionPipeline] = None
        self._vector_store: Optional[VectorStore] = None
        self._embedder = None
        
        # Configuration
        self._config = {}
        
        # Hardcoded values
        self._whatsapp_ingestor_id = "whatsapp_ingestor"
        self._whatsapp_collection = "whatsapp_messages"
    
    async def initialize(self) -> None:
        """
        Initialize the orchestrator with configuration parameters.
        
        Loads orchestrator configuration and initializes ingestion components,
        focusing only on WhatsApp-related components.
        
        Returns:
            None
            
        Raises:
            OrchestratorError: If initialization fails
        """
        try:
            self.logger.info({
                "action": "WHATSAPP_ORCHESTRATOR_INIT_START",
                "message": "Initializing WhatsAppIngestOrchestrator"
            })
            
            # Load orchestrator configuration
            try:
                self._config = get_component_config("orchestrator", self._config_path)
            except Exception as e:
                self.logger.warning({
                    "action": "WHATSAPP_ORCHESTRATOR_CONFIG_WARNING",
                    "message": f"Failed to load orchestrator configuration: {str(e)}",
                    "data": {"error": str(e)}
                })
                self._config = {}
            
            # Initialize embedder
            self._embedder = SentenceTransformerEmbedder(logger_name="whatsapp_orchestrator.embedder")
            await self._embedder.initialize()
            
            # Initialize vector store
            self._vector_store = ChromaDBStore(logger_name="whatsapp_orchestrator.vector_store")
            await self._vector_store.initialize()
            
            self.logger.info({
                "action": "WHATSAPP_ORCHESTRATOR_VECTOR_STORE_INIT",
                "message": "Vector store initialized successfully"
            })
            
            # Initialize ingestion pipeline with the vector store
            self._pipeline = DefaultIngestionPipeline(
                logger_name="whatsapp_orchestrator.pipeline", 
                vector_store=self._vector_store
            )
            await self._pipeline.initialize()
            
            self._is_initialized = True
            
            self.logger.info({
                "action": "WHATSAPP_ORCHESTRATOR_INIT_SUCCESS",
                "message": "WhatsAppIngestOrchestrator initialized successfully"
            })
            
        except Exception as e:
            self.logger.error({
                "action": "WHATSAPP_ORCHESTRATOR_INIT_ERROR",
                "message": f"Failed to initialize orchestrator: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"WhatsAppIngestOrchestrator initialization failed: {str(e)}") from e
    
    async def start_ingestion(self) -> None:
        """
        Start the WhatsApp ingestion pipeline.
        
        This method initiates the WhatsApp-specific ingestion process, which will 
        continue running in the background until stopped.
        
        Returns:
            None
            
        Raises:
            OrchestratorError: If starting ingestion fails
        """
        if not self._is_initialized:
            raise OrchestratorError("WhatsAppIngestOrchestrator must be initialized before starting ingestion")
        
        try:
            self.logger.info({
                "action": "WHATSAPP_ORCHESTRATOR_START_INGESTION",
                "message": "Starting WhatsApp ingestion pipeline"
            })
            
            # Use the WhatsApp-specific start method
            await self._pipeline.start_whatsapp()
            
            self.logger.info({
                "action": "WHATSAPP_ORCHESTRATOR_INGESTION_STARTED",
                "message": "WhatsApp ingestion pipeline started successfully"
            })
        except Exception as e:
            self.logger.error({
                "action": "WHATSAPP_ORCHESTRATOR_START_ERROR",
                "message": f"Failed to start WhatsApp ingestion: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Failed to start WhatsApp ingestion: {str(e)}") from e
    
    def stop_ingestion(self) -> None:
        """
        Stop the ingestion pipeline.
        
        This method halts the ongoing ingestion process.
        
        Returns:
            None
            
        Raises:
            OrchestratorError: If stopping ingestion fails
        """
        if not self._is_initialized:
            raise OrchestratorError("WhatsAppIngestOrchestrator must be initialized before stopping ingestion")
        
        try:
            self.logger.info({
                "action": "WHATSAPP_ORCHESTRATOR_STOP_INGESTION",
                "message": "Stopping ingestion pipeline"
            })
            
            self._pipeline.stop()
            
            self.logger.info({
                "action": "WHATSAPP_ORCHESTRATOR_INGESTION_STOPPED",
                "message": "Ingestion pipeline stopped successfully"
            })
        except Exception as e:
            self.logger.error({
                "action": "WHATSAPP_ORCHESTRATOR_STOP_ERROR",
                "message": f"Failed to stop ingestion: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Failed to stop ingestion: {str(e)}") from e
    
    async def run_manual_ingestion(self, ingestor_id: str) -> Dict[str, Any]:
        """
        Run a manual ingestion for WhatsApp ingestor.
        
        This method triggers a one-time ingestion run for the WhatsApp ingestor.
        It validates that the ingestor_id is WhatsApp-related.
        
        Args:
            ingestor_id: ID of the ingestor to run
            
        Returns:
            Dict[str, Any]: Summary of the ingestion results
            
        Raises:
            OrchestratorError: If manual ingestion fails or non-WhatsApp ingestor is specified
        """
        if not self._is_initialized:
            raise OrchestratorError("WhatsAppIngestOrchestrator must be initialized before running manual ingestion")
        
        # Validate that the ingestor is WhatsApp-related
        if not self._is_whatsapp_ingestor(ingestor_id):
            self.logger.error({
                "action": "WHATSAPP_ORCHESTRATOR_INVALID_INGESTOR",
                "message": f"Invalid ingestor ID: {ingestor_id} is not a WhatsApp ingestor",
                "data": {"ingestor_id": ingestor_id}
            })
            raise OrchestratorError(f"Invalid ingestor ID: {ingestor_id} is not a WhatsApp ingestor")
        
        try:
            self.logger.info({
                "action": "WHATSAPP_ORCHESTRATOR_MANUAL_INGESTION",
                "message": f"Running manual ingestion for {ingestor_id}",
                "data": {"ingestor_id": ingestor_id}
            })
            
            result = await self._pipeline.run_ingestion(ingestor_id)
            
            self.logger.info({
                "action": "WHATSAPP_ORCHESTRATOR_MANUAL_INGESTION_COMPLETE",
                "message": f"Manual ingestion completed for {ingestor_id}",
                "data": {
                    "ingestor_id": ingestor_id,
                    "documents_processed": result.get("documents_processed", 0)
                }
            })
            
            return result
        except Exception as e:
            self.logger.error({
                "action": "WHATSAPP_ORCHESTRATOR_MANUAL_INGESTION_ERROR",
                "message": f"Failed to run manual ingestion for {ingestor_id}: {str(e)}",
                "data": {"ingestor_id": ingestor_id, "error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Failed to run manual ingestion for {ingestor_id}: {str(e)}") from e
    
    def _is_whatsapp_ingestor(self, ingestor_id: str) -> bool:
        """
        Check if an ingestor ID is for a WhatsApp ingestor.
        
        Args:
            ingestor_id: The ingestor ID to check
            
        Returns:
            bool: True if the ingestor is a WhatsApp ingestor, False otherwise
        """
        return "whatsapp" in ingestor_id.lower()
    
    async def get_ingestion_status(self) -> Dict[str, Any]:
        """
        Get the status of WhatsApp ingestion.
        
        Returns:
            Dict[str, Any]: Status information
            
        Raises:
            OrchestratorError: If status retrieval fails
        """
        if not self._is_initialized:
            raise OrchestratorError("WhatsAppIngestOrchestrator must be initialized before getting status")
        
        try:
            # Get all ingestors and filter to WhatsApp only
            all_ingestors = self._pipeline._ingestors
            whatsapp_ingestors = {
                ingestor_id: info 
                for ingestor_id, info in all_ingestors.items() 
                if self._is_whatsapp_ingestor(ingestor_id)
            }
            
            # Get status for WhatsApp ingestors
            status = {
                "active": self._pipeline._scheduler_running,
                "total_whatsapp_ingestors": len(whatsapp_ingestors),
                "ingestors": {}
            }
            
            for ingestor_id in whatsapp_ingestors:
                ingestor_state = self._pipeline.get_ingestor_state(ingestor_id)
                status["ingestors"][ingestor_id] = ingestor_state
            
            return status
            
        except Exception as e:
            self.logger.error({
                "action": "WHATSAPP_ORCHESTRATOR_STATUS_ERROR",
                "message": f"Failed to get ingestion status: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Failed to get ingestion status: {str(e)}") from e
    
    async def close(self) -> None:
        """
        Clean up resources and close the orchestrator.
        
        Returns:
            None
            
        Raises:
            OrchestratorError: If cleanup fails
        """
        try:
            if self._pipeline:
                self.stop_ingestion()
            
            self.logger.info({
                "action": "WHATSAPP_ORCHESTRATOR_CLOSED",
                "message": "WhatsAppIngestOrchestrator closed successfully"
            })
        except Exception as e:
            self.logger.error({
                "action": "WHATSAPP_ORCHESTRATOR_CLOSE_ERROR",
                "message": f"Failed to close orchestrator: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Failed to close WhatsAppIngestOrchestrator: {str(e)}") from e
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Check if the orchestrator and its components are functioning properly.
        
        Returns:
            Dict[str, Any]: Health status information
            
        Raises:
            OrchestratorError: If the health check fails
        """
        health_info = {
            "healthy": False,
            "message": "WhatsAppIngestOrchestrator health check failed",
            "details": {
                "initialized": self._is_initialized
            },
            "components": {}
        }
        
        if not self._is_initialized:
            health_info["message"] = "WhatsAppIngestOrchestrator not initialized"
            return health_info
        
        try:
            # Check embedder
            if self._embedder:
                embedder_health = self._embedder.healthcheck()
                health_info["components"]["embedder"] = embedder_health
                if not embedder_health.get("healthy", False):
                    return health_info
            
            # Check vector store
            if self._vector_store:
                vector_store_health = self._vector_store.healthcheck()
                health_info["components"]["vector_store"] = vector_store_health
                if not vector_store_health.get("healthy", False):
                    return health_info
            
            # Check pipeline
            if self._pipeline:
                pipeline_health = await self._pipeline.healthcheck()
                health_info["components"]["pipeline"] = pipeline_health
                if not pipeline_health.get("healthy", False):
                    return health_info
            
            # Check for WhatsApp ingestors
            all_ingestors = self._pipeline._ingestors if self._pipeline else {}
            whatsapp_ingestors = {
                ingestor_id: info 
                for ingestor_id, info in all_ingestors.items() 
                if self._is_whatsapp_ingestor(ingestor_id)
            }
            
            health_info["details"]["whatsapp_ingestors_count"] = len(whatsapp_ingestors)
            
            if len(whatsapp_ingestors) == 0:
                health_info["message"] = "No WhatsApp ingestors registered"
                return health_info
            
            # All checks passed
            health_info["healthy"] = True
            health_info["message"] = "WhatsAppIngestOrchestrator is healthy"
            
            return health_info
        except Exception as e:
            self.logger.error({
                "action": "WHATSAPP_ORCHESTRATOR_HEALTHCHECK_ERROR",
                "message": f"Health check failed: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            health_info["message"] = f"Health check error: {str(e)}"
            health_info["details"]["error"] = str(e)
            return health_info
    
    # Required by Orchestrator interface but not implemented for this specialized orchestrator
    
    async def process_query(self, source: str, user_id: str, query: str, additional_info: Dict[str, Any]) -> str:
        """Not implemented for WhatsAppIngestOrchestrator."""
        raise NotImplementedError("WhatsAppIngestOrchestrator does not support query processing")
    
    async def configure(self, config: Dict[str, Any]) -> None:
        """Not implemented for WhatsAppIngestOrchestrator."""
        raise NotImplementedError("Dynamic configuration not supported")
    
    def get_rules(self, user_id: str) -> List[Dict[str, Any]]:
        """Not implemented for WhatsAppIngestOrchestrator."""
        raise NotImplementedError("Rule management not supported")
    
    async def build_context(self, user_id: str) -> Dict[str, Any]:
        """Not implemented for WhatsAppIngestOrchestrator."""
        raise NotImplementedError("Context building not supported") 