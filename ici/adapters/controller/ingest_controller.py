"""
Controller for managing background data ingestion.

This module provides a controller for initializing and running the
specialized IngestOrchestrator in the background without exposing API endpoints.
"""

import asyncio
import os
import traceback
from typing import Optional

from ici.adapters.orchestrators.ingest_orchestrator import IngestOrchestrator
from ici.adapters.loggers.structured_logger import StructuredLogger
from ici.core.exceptions import OrchestratorError


class IngestController:
    """
    Controller for managing background data ingestion.
    
    This controller initializes and starts the IngestOrchestrator
    to run data ingestion in the background.
    """
    
    def __init__(self, orchestrator: Optional[IngestOrchestrator] = None, logger_name: str = "ingest_controller"):
        """
        Initialize the IngestController.
        
        Args:
            orchestrator: Optional existing IngestOrchestrator instance to use
            logger_name: Name to use for the logger
        """
        self.logger = StructuredLogger(name=logger_name)
        self._orchestrator = orchestrator
        self._is_running = False
    
    async def initialize(self) -> None:
        """
        Initialize the controller and its components.
        
        Returns:
            None
            
        Raises:
            Exception: If initialization fails
        """
        try:
            self.logger.info({
                "action": "INGEST_CONTROLLER_INIT_START",
                "message": "Initializing IngestController"
            })
            
            # Initialize orchestrator if not provided
            if self._orchestrator is None:
                self._orchestrator = IngestOrchestrator(logger_name="ingest_controller.orchestrator")
                await self._orchestrator.initialize()
            
            self.logger.info({
                "action": "INGEST_CONTROLLER_INIT_SUCCESS",
                "message": "IngestController initialized successfully"
            })
        except Exception as e:
            self.logger.error({
                "action": "INGEST_CONTROLLER_INIT_ERROR",
                "message": f"Failed to initialize controller: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise
    
    async def start(self) -> None:
        """
        Start the background ingestion process.
        
        Returns:
            None
            
        Raises:
            Exception: If ingestion start fails
        """
        if self._is_running:
            return
        
        try:
            self.logger.info({
                "action": "INGEST_CONTROLLER_START",
                "message": "Starting background ingestion process"
            })
            
            # Start the ingestion process
            await self._orchestrator.start_ingestion()
            
            self._is_running = True
            
            self.logger.info({
                "action": "INGEST_CONTROLLER_STARTED",
                "message": "Background ingestion process started"
            })
        except Exception as e:
            self.logger.error({
                "action": "INGEST_CONTROLLER_START_ERROR",
                "message": f"Failed to start ingestion: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise
    
    async def stop(self) -> None:
        """
        Stop the background ingestion process.
        
        Returns:
            None
            
        Raises:
            Exception: If ingestion stop fails
        """
        if not self._is_running:
            return
        
        try:
            self.logger.info({
                "action": "INGEST_CONTROLLER_STOP",
                "message": "Stopping background ingestion process"
            })
            
            # Stop orchestrator components
            try:
                self._orchestrator.stop_ingestion()
                await self._orchestrator.close()
            except Exception as e:
                self.logger.warning({
                    "action": "INGEST_CONTROLLER_ORCHESTRATOR_STOP_WARNING",
                    "message": f"Error stopping orchestrator: {str(e)}",
                    "data": {"error": str(e)}
                })
            
            self._is_running = False
            
            self.logger.info({
                "action": "INGEST_CONTROLLER_STOPPED",
                "message": "Background ingestion process stopped"
            })
        except Exception as e:
            self.logger.error({
                "action": "INGEST_CONTROLLER_STOP_ERROR",
                "message": f"Failed to stop ingestion: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise
    
    async def healthcheck(self) -> dict:
        """
        Check the health of the ingestion process.
        
        Returns:
            dict: Health status information
        """
        try:
            if self._orchestrator:
                return await self._orchestrator.healthcheck()
            else:
                return {
                    "healthy": False,
                    "message": "Orchestrator not initialized"
                }
        except Exception as e:
            self.logger.error({
                "action": "INGEST_CONTROLLER_HEALTH_ERROR",
                "message": f"Health check failed: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            return {
                "healthy": False,
                "message": f"Health check failed: {str(e)}"
            } 