"""
DefaultOrchestrator implementation for the Orchestrator interface.

This module provides an implementation of the Orchestrator interface
that coordinates the processing of queries through validation,
vector search, prompt building, and response generation.
Supports both Telegram and WhatsApp data sources.
"""

import os
import time
from typing import Dict, Any, List, Optional, Tuple
import asyncio
import traceback
import json

from ici.core.interfaces.orchestrator import Orchestrator
from ici.core.interfaces.validator import Validator
from ici.core.interfaces.prompt_builder import PromptBuilder
from ici.core.interfaces.generator import Generator
from ici.core.interfaces.vector_store import VectorStore
from ici.core.interfaces.pipeline import IngestionPipeline
from ici.core.interfaces.chat_history_manager import ChatHistoryManager
from ici.core.interfaces.user_id_generator import UserIDGenerator
from ici.core.exceptions import (
    OrchestratorError, ValidationError, VectorStoreError, 
    PromptBuilderError, GenerationError, EmbeddingError,
    ChatHistoryError, ChatIDError, UserIDError
)
from ici.utils.config import get_component_config, load_config
from ici.core.interfaces.embedder import Embedder
from ici.adapters.loggers.structured_logger import StructuredLogger
from ici.adapters.validators.rule_based import RuleBasedValidator
from ici.adapters.prompt_builders.basic_prompt_builder import BasicPromptBuilder
from ici.adapters.vector_stores.chroma import ChromaDBStore
from ici.adapters.embedders.sentence_transformer import SentenceTransformerEmbedder
from ici.adapters.pipelines.default import DefaultIngestionPipeline
from ici.adapters.generators import create_generator
from ici.adapters.chat import JSONChatHistoryManager
from ici.adapters.user_id import DefaultUserIDGenerator


class DefaultOrchestrator(Orchestrator):
    """
    Orchestrator implementation for processing queries from various sources.
    
    Coordinates the flow from validation to generation for messages.
    Supports multi-turn conversations with chat history functionality.
    Works with multiple data sources through DefaultIngestionPipeline.
    """
    
    def __init__(self, logger_name: str = "orchestrator"):
        """
        Initialize the DefaultOrchestrator.
        
        Args:
            logger_name: Name to use for the logger
        """
        self.logger = StructuredLogger(name=logger_name)
        self._is_initialized = False
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        
        # Component references (will be initialized in initialize())
        self._validator: Optional[Validator] = None
        self._vector_store: Optional[VectorStore] = None
        self._prompt_builder: Optional[PromptBuilder] = None
        self._generator: Optional[Generator] = None
        self._pipeline: Optional[IngestionPipeline] = None
        self._embedder: Optional[Embedder] = None
        
        # Chat-specific components
        self._chat_history_manager: Optional[ChatHistoryManager] = None
        self._user_id_generator: Optional[UserIDGenerator] = None
        
        # Chat session mappings (user_id → current chat_id)
        self._active_chats: Dict[str, str] = {}
        
        # Special commands
        self._commands = {
            "/new": self._handle_new_chat_command,
            "/help": self._handle_help_command
        }
        
        # Default configuration
        self._num_results = 3  # Default number of documents to retrieve
        self._similarity_threshold = 0.0  # Default threshold for relevance
        self._config = {}  # Will be loaded from config file
        self._rules_source = "config"  # Default rules source
        self._error_messages = {
            "validation_failed": "Sorry, I cannot process your request due to security restrictions.",
            "no_documents": "I don't have information on that topic yet.",
            "generation_failed": "Sorry, I'm having trouble generating a response right now."
        }
    
    async def initialize(self) -> None:
        """
        Initialize the orchestrator with configuration parameters.
        
        Loads orchestrator configuration and initializes all components.
        
        Returns:
            None
            
        Raises:
            OrchestratorError: If initialization fails
        """
        try:
            self.logger.info({
                "action": "ORCHESTRATOR_INIT_START",
                "message": "Initializing DefaultOrchestrator"
            })
            
            # Load orchestrator configuration
            try:
                self._config = get_component_config("orchestrator", self._config_path)
            except Exception as e:
                self.logger.warning({
                    "action": "ORCHESTRATOR_CONFIG_WARNING",
                    "message": f"Failed to load orchestrator configuration: {str(e)}",
                    "data": {"error": str(e)}
                })
                self._config = {}
            
            # Extract configuration values with defaults
            self._num_results = self._config.get("num_results", self._num_results)
            self._similarity_threshold = self._config.get("similarity_threshold", self._similarity_threshold)
            self._rules_source = self._config.get("rules_source", self._rules_source)
            
            # Update error messages if provided
            if "error_messages" in self._config:
                self._error_messages.update(self._config.get("error_messages", {}))
            
            # Initialize components
            await self._initialize_components()
            
            # Initialize chat components
            await self._initialize_chat_components()
            
            self._is_initialized = True
            
            # Start the pipeline if configured to do so
            pipeline_config = self._config.get("pipeline", {})
            auto_start = pipeline_config.get("auto_start", True)
            
            if auto_start and self._pipeline:
                try:
                    print("Initializing pipeline components...")
                    await self._pipeline.start()
                    print("Pipeline initialized successfully")
                    self.logger.info({
                        "action": "ORCHESTRATOR_PIPELINE_STARTED",
                        "message": "Pipeline started successfully"
                    })
                except Exception as e:
                    self.logger.error({
                        "action": "ORCHESTRATOR_PIPELINE_ERROR",
                        "message": f"Failed to start pipeline: {str(e)}",
                        "data": {"error": str(e), "error_type": type(e).__name__}
                    })
            
            self.logger.info({
                "action": "ORCHESTRATOR_INIT_SUCCESS",
                "message": "DefaultOrchestrator initialized successfully",
                "data": {
                    "num_results": self._num_results,
                    "similarity_threshold": self._similarity_threshold
                }
            })
            
        except Exception as e:
            self.logger.error({
                "action": "ORCHESTRATOR_INIT_ERROR",
                "message": f"Failed to initialize orchestrator: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Orchestrator initialization failed: {str(e)}") from e 