"""
IngestOrchestrator implementation that focuses solely on data ingestion.

This orchestrator is a specialized version that only handles ingestion workflows,
allowing for cleaner separation of concerns between ingestion and querying.
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


class IngestOrchestrator(Orchestrator):
    """
    Orchestrator implementation focused solely on data ingestion operations.
    
    This orchestrator is specialized for managing the ingestion pipeline
    and its components, providing a clean separation from query-related operations.
    """
    
    def __init__(self, logger_name: str = "ingest_orchestrator"):
        """
        Initialize the IngestOrchestrator.
        
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
    
    async def initialize(self) -> None:
        """
        Initialize the orchestrator with configuration parameters.
        
        Loads orchestrator configuration and initializes ingestion components.
        
        Returns:
            None
            
        Raises:
            OrchestratorError: If initialization fails
        """
        try:
            self.logger.info({
                "action": "INGEST_ORCHESTRATOR_INIT_START",
                "message": "Initializing IngestOrchestrator"
            })
            
            # Load orchestrator configuration
            try:
                self._config = get_component_config("orchestrator", self._config_path)
            except Exception as e:
                self.logger.warning({
                    "action": "INGEST_ORCHESTRATOR_CONFIG_WARNING",
                    "message": f"Failed to load orchestrator configuration: {str(e)}",
                    "data": {"error": str(e)}
                })
                self._config = {}
            
            # Initialize embedder
            self._embedder = SentenceTransformerEmbedder(logger_name="ingest_orchestrator.embedder")
            await self._embedder.initialize()
            
            # Initialize vector store
            self._vector_store = ChromaDBStore(logger_name="ingest_orchestrator.vector_store")
            await self._vector_store.initialize()
            
            self.logger.info({
                "action": "INGEST_ORCHESTRATOR_VECTOR_STORE_INIT",
                "message": "Vector store initialized successfully"
            })
            
            # Initialize ingestion pipeline with the vector store
            self._pipeline = DefaultIngestionPipeline(
                logger_name="ingest_orchestrator.pipeline", 
                vector_store=self._vector_store
            )
            await self._pipeline.initialize()
            
            self._is_initialized = True
            
            self.logger.info({
                "action": "INGEST_ORCHESTRATOR_INIT_SUCCESS",
                "message": "IngestOrchestrator initialized successfully"
            })
            
        except Exception as e:
            self.logger.error({
                "action": "INGEST_ORCHESTRATOR_INIT_ERROR",
                "message": f"Failed to initialize orchestrator: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"IngestOrchestrator initialization failed: {str(e)}") from e
    
    async def start_ingestion(self) -> None:
        """
        Start the ingestion pipeline.
        
        This method initiates the ingestion process, which will continue running
        in the background until stopped.
        
        Returns:
            None
            
        Raises:
            OrchestratorError: If starting ingestion fails
        """
        if not self._is_initialized:
            raise OrchestratorError("IngestOrchestrator must be initialized before starting ingestion")
        
        try:
            self.logger.info({
                "action": "INGEST_ORCHESTRATOR_START_INGESTION",
                "message": "Starting ingestion pipeline"
            })
            
            await self._pipeline.start()
            
            self.logger.info({
                "action": "INGEST_ORCHESTRATOR_INGESTION_STARTED",
                "message": "Ingestion pipeline started successfully"
            })
        except Exception as e:
            self.logger.error({
                "action": "INGEST_ORCHESTRATOR_START_ERROR",
                "message": f"Failed to start ingestion: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Failed to start ingestion: {str(e)}") from e
    
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
            raise OrchestratorError("IngestOrchestrator must be initialized before stopping ingestion")
        
        try:
            self.logger.info({
                "action": "INGEST_ORCHESTRATOR_STOP_INGESTION",
                "message": "Stopping ingestion pipeline"
            })
            
            self._pipeline.stop()
            
            self.logger.info({
                "action": "INGEST_ORCHESTRATOR_INGESTION_STOPPED",
                "message": "Ingestion pipeline stopped successfully"
            })
        except Exception as e:
            self.logger.error({
                "action": "INGEST_ORCHESTRATOR_STOP_ERROR",
                "message": f"Failed to stop ingestion: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Failed to stop ingestion: {str(e)}") from e
    
    async def run_manual_ingestion(self, ingestor_id: str) -> Dict[str, Any]:
        """
        Run a manual ingestion for a specific ingestor.
        
        This method triggers a one-time ingestion run for the specified ingestor.
        
        Args:
            ingestor_id: ID of the ingestor to run
            
        Returns:
            Dict[str, Any]: Summary of the ingestion results
            
        Raises:
            OrchestratorError: If manual ingestion fails
        """
        if not self._is_initialized:
            raise OrchestratorError("IngestOrchestrator must be initialized before running manual ingestion")
        
        try:
            self.logger.info({
                "action": "INGEST_ORCHESTRATOR_MANUAL_INGESTION",
                "message": f"Running manual ingestion for {ingestor_id}",
                "data": {"ingestor_id": ingestor_id}
            })
            
            results = await self._pipeline.run_ingestion(ingestor_id)
            
            self.logger.info({
                "action": "INGEST_ORCHESTRATOR_MANUAL_INGESTION_COMPLETE",
                "message": f"Manual ingestion complete for {ingestor_id}",
                "data": {
                    "ingestor_id": ingestor_id,
                    "documents_processed": results.get("documents_processed", 0)
                }
            })
            
            return results
        except Exception as e:
            self.logger.error({
                "action": "INGEST_ORCHESTRATOR_MANUAL_INGESTION_ERROR",
                "message": f"Failed to run manual ingestion: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__, "ingestor_id": ingestor_id}
            })
            raise OrchestratorError(f"Failed to run manual ingestion for {ingestor_id}: {str(e)}") from e
    
    async def get_ingestion_status(self) -> Dict[str, Any]:
        """
        Get the current status of the ingestion pipeline.
        
        Returns:
            Dict[str, Any]: Status information about the ingestion pipeline
            
        Raises:
            OrchestratorError: If retrieving status fails
        """
        if not self._is_initialized:
            raise OrchestratorError("IngestOrchestrator must be initialized before getting status")
        
        try:
            status = {
                "is_running": False,  # This would need to be tracked by the pipeline
                "ingestors": {}
            }
            
            # Get status for each registered ingestor
            for ingestor_id in self._pipeline._ingestors:
                state = self._pipeline.get_ingestor_state(ingestor_id)
                status["ingestors"][ingestor_id] = {
                    "last_timestamp": state.get("last_timestamp"),
                    "additional_metadata": state.get("additional_metadata", {})
                }
            
            return status
        except Exception as e:
            self.logger.error({
                "action": "INGEST_ORCHESTRATOR_STATUS_ERROR",
                "message": f"Failed to get ingestion status: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Failed to get ingestion status: {str(e)}") from e
    
    async def close(self) -> None:
        """
        Clean up resources used by the orchestrator.
        
        Returns:
            None
            
        Raises:
            OrchestratorError: If cleanup fails
        """
        try:
            self.logger.info({
                "action": "INGEST_ORCHESTRATOR_CLOSE",
                "message": "Closing IngestOrchestrator resources"
            })
            
            # Stop the pipeline if it's running
            if self._pipeline and self._is_initialized:
                self._pipeline.stop()
                await self._pipeline.close()
            
            self.logger.info({
                "action": "INGEST_ORCHESTRATOR_CLOSED",
                "message": "IngestOrchestrator resources closed successfully"
            })
        except Exception as e:
            self.logger.error({
                "action": "INGEST_ORCHESTRATOR_CLOSE_ERROR",
                "message": f"Failed to close resources: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Failed to close IngestOrchestrator resources: {str(e)}") from e
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Check the health of the ingestion orchestrator and its components.
        
        Returns:
            Dict[str, Any]: Health status information
            
        Raises:
            OrchestratorError: If health check fails
        """
        if not self._is_initialized:
            return {
                "healthy": False,
                "message": "IngestOrchestrator not initialized",
                "components": {}
            }
        
        try:
            components = {}
            overall_healthy = True
            
            # Check pipeline health
            pipeline_health = await self._pipeline.healthcheck()
            components["pipeline"] = pipeline_health
            if not pipeline_health.get("healthy", False):
                overall_healthy = False
            
            # Check vector store health
            vector_store_health = await self._vector_store.healthcheck()
            components["vector_store"] = vector_store_health
            if not vector_store_health.get("healthy", False):
                overall_healthy = False
            
            return {
                "healthy": overall_healthy,
                "message": "OK" if overall_healthy else "One or more components are unhealthy",
                "components": components
            }
        except Exception as e:
            self.logger.error({
                "action": "INGEST_ORCHESTRATOR_HEALTHCHECK_ERROR",
                "message": f"Healthcheck failed: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            return {
                "healthy": False,
                "message": f"Healthcheck failed: {str(e)}",
                "components": {}
            }
    
    # The following methods are required by the Orchestrator interface but aren't used
    # in the specialized IngestOrchestrator
    
    async def process_query(self, source: str, user_id: str, query: str, additional_info: Dict[str, Any]) -> str:
        """Not implemented for IngestOrchestrator"""
        raise NotImplementedError("IngestOrchestrator does not implement process_query")
    
    async def configure(self, config: Dict[str, Any]) -> None:
        """Not fully implemented for IngestOrchestrator"""
        self._config.update(config)
    
    def get_rules(self, user_id: str) -> List[Dict[str, Any]]:
        """Not implemented for IngestOrchestrator"""
        raise NotImplementedError("IngestOrchestrator does not implement get_rules")
    
    async def build_context(self, user_id: str) -> Dict[str, Any]:
        """Not implemented for IngestOrchestrator"""
        raise NotImplementedError("IngestOrchestrator does not implement build_context") 