"""
QueryOrchestrator implementation that focuses solely on query processing.

This orchestrator is a specialized version that only handles query workflows,
allowing for cleaner separation of concerns between querying and ingestion.
"""

import os
import time
from typing import Dict, Any, List, Optional, Tuple
import asyncio
import traceback
import json
import re

from ici.core.interfaces.orchestrator import Orchestrator
from ici.core.interfaces.validator import Validator
from ici.core.interfaces.prompt_builder import PromptBuilder
from ici.core.interfaces.generator import Generator
from ici.core.interfaces.vector_store import VectorStore
from ici.core.exceptions import (
    OrchestratorError, ValidationError, VectorStoreError, 
    PromptBuilderError, GenerationError, EmbeddingError
)
from ici.utils.config import get_component_config, load_config
from ici.core.interfaces.embedder import Embedder
from ici.adapters.loggers.structured_logger import StructuredLogger
from ici.adapters.validators.rule_based import RuleBasedValidator
from ici.adapters.prompt_builders.basic_prompt_builder import BasicPromptBuilder
from ici.adapters.vector_stores.chroma import ChromaDBStore
from ici.adapters.embedders.sentence_transformer import SentenceTransformerEmbedder
from ici.adapters.generators import create_generator


class QueryOrchestrator(Orchestrator):
    """
    Orchestrator implementation focused solely on query processing operations.
    
    This orchestrator is specialized for managing query workflows, retrieving
    relevant context, and generating responses, with a clean separation from
    ingestion operations.
    """
    
    def __init__(self, logger_name: str = "query_orchestrator"):
        """
        Initialize the QueryOrchestrator.
        
        Args:
            logger_name: Name to use for the logger
        """
        self.logger = StructuredLogger(name=logger_name)
        self._is_initialized = False
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        
        # Component references
        self._validator: Optional[Validator] = None
        self._vector_store: Optional[VectorStore] = None
        self._prompt_builder: Optional[PromptBuilder] = None
        self._generator: Optional[Generator] = None
        self._embedder: Optional[Embedder] = None
        
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
        
        Loads query orchestrator configuration and initializes all query-related components.
        
        Returns:
            None
            
        Raises:
            OrchestratorError: If initialization fails
        """
        try:
            self.logger.info({
                "action": "QUERY_ORCHESTRATOR_INIT_START",
                "message": "Initializing QueryOrchestrator"
            })
            
            # Load orchestrator configuration
            try:
                self._config = get_component_config("orchestrator", self._config_path)
            except Exception as e:
                self.logger.warning({
                    "action": "QUERY_ORCHESTRATOR_CONFIG_WARNING",
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
            
            self._is_initialized = True
            
            self.logger.info({
                "action": "QUERY_ORCHESTRATOR_INIT_SUCCESS",
                "message": "QueryOrchestrator initialized successfully",
                "data": {
                    "num_results": self._num_results,
                    "similarity_threshold": self._similarity_threshold
                }
            })
            
        except Exception as e:
            self.logger.error({
                "action": "QUERY_ORCHESTRATOR_INIT_ERROR",
                "message": f"Failed to initialize orchestrator: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"QueryOrchestrator initialization failed: {str(e)}") from e
    
    async def _initialize_components(self) -> None:
        """
        Initialize all required components for query processing.
        
        Creates and initializes validator, vector store, prompt builder, and generator.
        
        Raises:
            OrchestratorError: If component initialization fails
        """
        try:
            # Initialize validator
            self._validator = RuleBasedValidator(logger_name="query_orchestrator.validator")
            await self._validator.initialize()

            # Initialize embedder
            self._embedder = SentenceTransformerEmbedder(logger_name="query_orchestrator.embedder")
            await self._embedder.initialize()
            
            # Initialize vector store
            self._vector_store = ChromaDBStore(logger_name="query_orchestrator.vector_store")
            await self._vector_store.initialize()
            
            self.logger.info({
                "action": "QUERY_ORCHESTRATOR_VECTOR_STORE_INIT",
                "message": "Vector store initialized successfully"
            })
            
            # Initialize prompt builder
            self._prompt_builder = BasicPromptBuilder(logger_name="query_orchestrator.prompt_builder")
            await self._prompt_builder.initialize()
            
            # Initialize the generator
            try:
                self.logger.info({
                    "action": "QUERY_ORCHESTRATOR_INIT_GENERATOR",
                    "message": "Initializing generator"
                })
                self._generator = create_generator(logger_name="query_orchestrator.generator")
                await self._generator.initialize()
                
                self.logger.info({
                    "action": "QUERY_ORCHESTRATOR_INIT_GENERATOR_SUCCESS",
                    "message": "Generator initialized successfully"
                })
            except Exception as e:
                self.logger.error({
                    "action": "QUERY_ORCHESTRATOR_GENERATOR_ERROR",
                    "message": f"Failed to initialize generator: {str(e)}",
                    "data": {"error": str(e), "error_type": type(e).__name__}
                })
                raise OrchestratorError(f"Failed to initialize generator: {str(e)}") from e
        except Exception as e:
            self.logger.error({
                "action": "QUERY_ORCHESTRATOR_COMPONENTS_ERROR",
                "message": f"Failed to initialize components: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Failed to initialize components: {str(e)}") from e
    
    async def process_query(self, source: str, user_id: str, query: str, additional_info: Dict[str, Any]) -> str:
        """
        Process a user query and generate a response.
        
        This is the main method for handling user queries, which validates input,
        retrieves relevant context, and generates a response.
        
        Args:
            source: Source of the query (e.g., "api", "cli")
            user_id: ID of the user making the query
            query: The actual query text
            additional_info: Additional context or metadata
            
        Returns:
            str: Response to the query
            
        Raises:
            OrchestratorError: If query processing fails
        """
        if not self._is_initialized:
            raise OrchestratorError("QueryOrchestrator must be initialized before processing queries")
        
        start_time = time.time()
        self.logger.info({
            "action": "QUERY_ORCHESTRATOR_PROCESS_START",
            "message": f"Processing query: {query}",
            "data": {
                "source": source,
                "user_id": user_id,
                "query_length": len(query)
            }
        })
        
        try:
            # Validate the query
            context = await self.build_context(user_id)
            rules = self.get_rules(user_id)
            is_valid, validation_errors = await self._validate_query(query, context, rules)
            
            if not is_valid:
                self.logger.warning({
                    "action": "QUERY_ORCHESTRATOR_VALIDATION_FAILED",
                    "message": "Query validation failed",
                    "data": {
                        "errors": validation_errors,
                        "query": query
                    }
                })
                return self._error_messages["validation_failed"]
            
            # Retrieve relevant documents
            documents = await self._search_documents(query, self._num_results)
            
            if not documents:
                self.logger.info({
                    "action": "QUERY_ORCHESTRATOR_NO_DOCUMENTS",
                    "message": "No relevant documents found for query",
                    "data": {"query": query}
                })
                return self._error_messages["no_documents"]
            
            # Build the prompt
            prompt = await self._prompt_builder.build_prompt(
                query=query,
                documents=documents,
                additional_info=additional_info
            )
            
            # Generate the response
            response = await self._generate_response(prompt)
            
            # Log completion
            elapsed_time = time.time() - start_time
            self.logger.info({
                "action": "QUERY_ORCHESTRATOR_PROCESS_COMPLETE",
                "message": "Query processing complete",
                "data": {
                    "query": query,
                    "elapsed_seconds": elapsed_time,
                    "response_length": len(response)
                }
            })
            
            return response
            
        except ValidationError as e:
            self.logger.error({
                "action": "QUERY_ORCHESTRATOR_VALIDATION_ERROR",
                "message": f"Validation error: {str(e)}",
                "data": {"error": str(e), "query": query}
            })
            return self._error_messages["validation_failed"]
        except VectorStoreError as e:
            self.logger.error({
                "action": "QUERY_ORCHESTRATOR_VECTOR_STORE_ERROR",
                "message": f"Vector store error: {str(e)}",
                "data": {"error": str(e), "query": query}
            })
            return self._error_messages["no_documents"]
        except (PromptBuilderError, GenerationError) as e:
            self.logger.error({
                "action": "QUERY_ORCHESTRATOR_GENERATION_ERROR",
                "message": f"Generation error: {str(e)}",
                "data": {"error": str(e), "query": query}
            })
            return self._error_messages["generation_failed"]
        except Exception as e:
            self.logger.error({
                "action": "QUERY_ORCHESTRATOR_PROCESS_ERROR",
                "message": f"Query processing error: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__, "query": query}
            })
            return f"An unexpected error occurred: {str(e)}"
    
    async def _validate_query(self, query: str, context: Dict[str, Any], rules: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """
        Validate a query against security rules.
        
        Args:
            query: The query text to validate
            context: Context information for validation
            rules: Validation rules to apply
            
        Returns:
            Tuple[bool, List[str]]: Validation result and any error messages
            
        Raises:
            ValidationError: If validation process fails
        """
        try:
            # If no rules are defined, consider the query valid
            if not rules:
                return True, []
            
            result = await self._validator.validate(
                input_text=query,
                context=context,
                rules=rules
            )
            
            return result.is_valid, result.errors
            
        except Exception as e:
            self.logger.error({
                "action": "QUERY_ORCHESTRATOR_VALIDATE_ERROR",
                "message": f"Validation process error: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise ValidationError(f"Validation process failed: {str(e)}") from e
    
    async def _search_documents(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Search for documents relevant to the query.
        
        Args:
            query: The query text
            top_k: Number of documents to retrieve
            
        Returns:
            List[Dict[str, Any]]: List of relevant documents
            
        Raises:
            VectorStoreError: If document search fails
        """
        try:
            # Generate embedding for the query
            query_embedding = await self._embedder.embed_query(query)
            
            # Search for relevant documents
            search_results = await self._vector_store.search(
                query_embedding=query_embedding,
                filter={},  # No filter by default
                top_k=top_k,
                alpha=1.0  # Default hybrid search parameter
            )
            
            self.logger.info({
                "action": "QUERY_ORCHESTRATOR_SEARCH_RESULTS",
                "message": f"Found {len(search_results)} relevant documents",
                "data": {"query": query, "top_k": top_k}
            })
            
            return search_results
            
        except EmbeddingError as e:
            self.logger.error({
                "action": "QUERY_ORCHESTRATOR_EMBEDDING_ERROR",
                "message": f"Failed to generate query embedding: {str(e)}",
                "data": {"error": str(e), "query": query}
            })
            raise VectorStoreError(f"Failed to generate query embedding: {str(e)}") from e
        except Exception as e:
            self.logger.error({
                "action": "QUERY_ORCHESTRATOR_SEARCH_ERROR",
                "message": f"Document search failed: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__, "query": query}
            })
            raise VectorStoreError(f"Document search failed: {str(e)}") from e
    
    async def _generate_response(self, prompt: str) -> str:
        """
        Generate a response using the LLM.
        
        Args:
            prompt: The prepared prompt
            
        Returns:
            str: Generated response
            
        Raises:
            GenerationError: If response generation fails
        """
        try:
            # Generate the response
            response = await self._generator.generate(prompt)
            
            return response
            
        except Exception as e:
            self.logger.error({
                "action": "QUERY_ORCHESTRATOR_GENERATION_ERROR",
                "message": f"Failed to generate response: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise GenerationError(f"Failed to generate response: {str(e)}") from e
    
    async def get_context(self, source: str, user_id: str, query: str, additional_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve context for a query without generating a response.
        
        This method is useful for debugging or examining what context would be
        used for a given query.
        
        Args:
            source: Source of the query
            user_id: ID of the user
            query: The query text
            additional_info: Additional context or metadata
            
        Returns:
            Dict[str, Any]: Context information including retrieved documents
            
        Raises:
            OrchestratorError: If context retrieval fails
        """
        if not self._is_initialized:
            raise OrchestratorError("QueryOrchestrator must be initialized before getting context")
        
        try:
            # Retrieve relevant documents
            documents = await self._search_documents(query, self._num_results)
            
            # Format the context
            context = {
                "query": query,
                "user_id": user_id,
                "source": source,
                "timestamp": time.time(),
                "documents": documents,
                "additional_info": additional_info
            }
            
            return context
            
        except Exception as e:
            self.logger.error({
                "action": "QUERY_ORCHESTRATOR_CONTEXT_ERROR",
                "message": f"Failed to get context: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__, "query": query}
            })
            raise OrchestratorError(f"Failed to get context: {str(e)}") from e
    
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
                "action": "QUERY_ORCHESTRATOR_CLOSE",
                "message": "Closing QueryOrchestrator resources"
            })
            
            # Close components
            
            self.logger.info({
                "action": "QUERY_ORCHESTRATOR_CLOSED",
                "message": "QueryOrchestrator resources closed successfully"
            })
        except Exception as e:
            self.logger.error({
                "action": "QUERY_ORCHESTRATOR_CLOSE_ERROR",
                "message": f"Failed to close resources: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Failed to close QueryOrchestrator resources: {str(e)}") from e
    
    async def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure the orchestrator.
        
        Args:
            config: Configuration settings
            
        Returns:
            None
            
        Raises:
            OrchestratorError: If configuration fails
        """
        try:
            if "num_results" in config:
                self._num_results = config["num_results"]
            
            if "similarity_threshold" in config:
                self._similarity_threshold = config["similarity_threshold"]
            
            if "rules_source" in config:
                self._rules_source = config["rules_source"]
            
            if "error_messages" in config:
                self._error_messages.update(config["error_messages"])
            
            self.logger.info({
                "action": "QUERY_ORCHESTRATOR_CONFIGURED",
                "message": "Orchestrator configured",
                "data": {
                    "num_results": self._num_results,
                    "similarity_threshold": self._similarity_threshold
                }
            })
        except Exception as e:
            self.logger.error({
                "action": "QUERY_ORCHESTRATOR_CONFIGURE_ERROR",
                "message": f"Failed to configure orchestrator: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Failed to configure QueryOrchestrator: {str(e)}") from e
    
    def get_rules(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get validation rules for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List[Dict[str, Any]]: List of validation rules
        """
        if self._rules_source == "config":
            # Get rules from configuration
            validation_rules = self._config.get("validation_rules", {})
            
            # Try to get user-specific rules, fall back to default
            rules = validation_rules.get(user_id, validation_rules.get("default", []))
            
            return rules
        else:
            # For other rule sources, implement here
            self.logger.warning({
                "action": "QUERY_ORCHESTRATOR_RULES_SOURCE_UNKNOWN",
                "message": f"Unknown rules source: {self._rules_source}",
                "data": {"user_id": user_id}
            })
            return []
    
    async def build_context(self, user_id: str) -> Dict[str, Any]:
        """
        Build validation context for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dict[str, Any]: Context for validation
        """
        # Get user context from configuration
        user_context = self._config.get("user_context", {})
        
        # Try to get user-specific context, fall back to default
        context = user_context.get(user_id, user_context.get("default", {}))
        
        # Add current timestamp
        context["timestamp"] = datetime.now().isoformat()
        
        return context
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Check the health of the query orchestrator and its components.
        
        Returns:
            Dict[str, Any]: Health status information
            
        Raises:
            OrchestratorError: If health check fails
        """
        if not self._is_initialized:
            return {
                "healthy": False,
                "message": "QueryOrchestrator not initialized",
                "components": {}
            }
        
        try:
            components = {}
            overall_healthy = True
            
            # Check validator health
            try:
                validator_health = await self._validator.healthcheck()
                components["validator"] = validator_health
                if not validator_health.get("healthy", False):
                    overall_healthy = False
            except Exception as e:
                components["validator"] = {
                    "healthy": False,
                    "message": f"Healthcheck failed: {str(e)}"
                }
                overall_healthy = False
            
            # Check embedder health
            try:
                embedder_health = await self._embedder.healthcheck()
                components["embedder"] = embedder_health
                if not embedder_health.get("healthy", False):
                    overall_healthy = False
            except Exception as e:
                components["embedder"] = {
                    "healthy": False,
                    "message": f"Healthcheck failed: {str(e)}"
                }
                overall_healthy = False
            
            # Check vector store health
            try:
                vector_store_health = await self._vector_store.healthcheck()
                components["vector_store"] = vector_store_health
                if not vector_store_health.get("healthy", False):
                    overall_healthy = False
            except Exception as e:
                components["vector_store"] = {
                    "healthy": False,
                    "message": f"Healthcheck failed: {str(e)}"
                }
                overall_healthy = False
            
            # Check prompt builder health
            try:
                prompt_builder_health = await self._prompt_builder.healthcheck()
                components["prompt_builder"] = prompt_builder_health
                if not prompt_builder_health.get("healthy", False):
                    overall_healthy = False
            except Exception as e:
                components["prompt_builder"] = {
                    "healthy": False,
                    "message": f"Healthcheck failed: {str(e)}"
                }
                overall_healthy = False
            
            # Check generator health
            try:
                generator_health = await self._generator.healthcheck()
                components["generator"] = generator_health
                if not generator_health.get("healthy", False):
                    overall_healthy = False
            except Exception as e:
                components["generator"] = {
                    "healthy": False,
                    "message": f"Healthcheck failed: {str(e)}"
                }
                overall_healthy = False
            
            return {
                "healthy": overall_healthy,
                "message": "OK" if overall_healthy else "One or more components are unhealthy",
                "components": components
            }
        except Exception as e:
            self.logger.error({
                "action": "QUERY_ORCHESTRATOR_HEALTHCHECK_ERROR",
                "message": f"Healthcheck failed: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            return {
                "healthy": False,
                "message": f"Healthcheck failed: {str(e)}",
                "components": {}
            } 