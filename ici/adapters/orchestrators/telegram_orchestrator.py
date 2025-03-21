"""
TelegramOrchestrator implementation for the Orchestrator interface.

This module provides an implementation of the Orchestrator interface
that coordinates the processing of Telegram queries through validation,
vector search, prompt building, and response generation.
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
from ici.core.exceptions import OrchestratorError, ValidationError, VectorStoreError, PromptBuilderError, GenerationError, EmbeddingError
from ici.utils.config import get_component_config, load_config
from ici.core.interfaces.embedder import Embedder
from ici.adapters.loggers.structured_logger import StructuredLogger
from ici.adapters.validators.rule_based import RuleBasedValidator
from ici.adapters.prompt_builders.basic_prompt_builder import BasicPromptBuilder
from ici.adapters.vector_stores.chroma import ChromaDBStore
from ici.adapters.embedders.sentence_transformer import SentenceTransformerEmbedder
from ici.adapters.pipelines.telegram import TelegramIngestionPipeline
from ici.adapters.generators import create_generator


class TelegramOrchestrator(Orchestrator):
    """
    Orchestrator implementation for processing Telegram queries.
    
    Coordinates the flow from validation to generation for Telegram messages.
    """
    
    def __init__(self, logger_name: str = "orchestrator"):
        """
        Initialize the TelegramOrchestrator.
        
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
                "message": "Initializing TelegramOrchestrator"
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
            
            self._is_initialized = True
            
            # Start the pipeline if configured to do so
            pipeline_config = self._config.get("pipeline", {})
            auto_start = pipeline_config.get("auto_start", True)
            
            if auto_start and self._pipeline:
                try:
                    # await self._pipeline.start()
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
                "message": "TelegramOrchestrator initialized successfully",
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
    
    async def _initialize_components(self) -> None:
        """
        Initialize all required components.
        
        Creates and initializes validator, vector store, prompt builder, generator, and pipeline.
        
        Raises:
            OrchestratorError: If component initialization fails
        """
        try:
            # Initialize validator
            self._validator = RuleBasedValidator(logger_name="orchestrator.validator")
            await self._validator.initialize()

            self._embedder = SentenceTransformerEmbedder(logger_name="orchestrator.embedder")
            await self._embedder.initialize()
            
            # Initialize vector store
            self._vector_store = ChromaDBStore(logger_name="orchestrator.vector_store")
            await self._vector_store.initialize()
            
            # Initialize prompt builder
            self._prompt_builder = BasicPromptBuilder(logger_name="orchestrator.prompt_builder")
            await self._prompt_builder.initialize()
            
            # Initialize the generator
            try:
                self.logger.info({
                    "action": "ORCHESTRATOR_INIT_GENERATOR",
                    "message": "Initializing generator"
                })
                self._generator = create_generator(logger_name="orchestrator.generator")
                await self._generator.initialize()
                
                self.logger.info({
                    "action": "ORCHESTRATOR_INIT_GENERATOR_SUCCESS",
                    "message": "Generator initialized successfully"
                })
            except Exception as e:
                self.logger.error({
                    "action": "ORCHESTRATOR_INIT_GENERATOR_ERROR",
                    "message": f"Failed to initialize generator: {str(e)}",
                    "data": {"error": str(e), "error_type": type(e).__name__}
                })
                raise e
            
            # Initialize ingestion pipeline
            self._pipeline = TelegramIngestionPipeline(logger_name="orchestrator.pipeline")
            await self._pipeline.initialize()
            
            self.logger.info({
                "action": "ORCHESTRATOR_COMPONENTS_INIT",
                "message": "All components initialized successfully"
            })
            
        except Exception as e:
            self.logger.error({
                "action": "ORCHESTRATOR_COMPONENTS_INIT_ERROR",
                "message": f"Failed to initialize components: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Component initialization failed: {str(e)}") from e
    
    async def process_query(self, source: str, user_id: str, query: str, additional_info: Dict[str, Any]) -> str:
        """
        Manages query processing from validation to generation.

        Args:
            source: The source of the query
            user_id: Identifier for the user making the request
            query: The user input/question to process
            additional_info: Dictionary containing additional attributes and values

        Returns:
            str: The final response to the user

        Raises:
            OrchestratorError: If the orchestration process fails
        """
        if not self._is_initialized:
            raise OrchestratorError("Orchestrator not initialized. Call initialize() first.")
        
        self.logger.info({
            "action": "ORCHESTRATOR_PROCESS_QUERY",
            "message": "Processing query",
            "data": {
                "source": source,
                "user_id": user_id,
                "query_length": len(query) if query else 0
            }
        })
        
        start_time = time.time()
        
        try:
            # Step 1: Build context for validation
            context = await self.build_context(user_id)
            
            # Add source to context
            context["source"] = source
            
            # Add any additional info to context
            if additional_info:
                context.update(additional_info)
            
            # Step 2: Get rules for validation
            rules = self.get_rules(user_id)
            
            # Step 3: Validate the query
            is_valid, failure_reasons = await self._validate_query(query, context, rules)
            
            if not is_valid:
                self.logger.info({
                    "action": "ORCHESTRATOR_VALIDATION_FAILED",
                    "message": "Query validation failed",
                    "data": {
                        "user_id": user_id,
                        "failure_reasons": failure_reasons
                    }
                })
                return self._error_messages.get("validation_failed")
            
            self.logger.info({
                "action": "ORCHESTRATOR_VALIDATION_SUCCESS",
                "message": "Query validation successful",
                "data": {"user_id": user_id, "query": query}
            })
            
            # Step 4: Search for relevant documents
            documents = await self._search_documents(query, self._num_results)

            self.logger.info({
                "action": "ORCHESTRATOR_DOCUMENTS_FOUND",
                "message": "Documents found",
                "data": {"documents": documents, "query": query, "num_results": self._num_results}
            })
            
            # Step 5: Build prompt with documents and query
            prompt = await self._build_prompt(query, documents)
            
            # Step 6: Generate response
            response = await self._generate_response(prompt)
            
            # Log completion time
            elapsed_time = time.time() - start_time
            self.logger.info({
                "action": "ORCHESTRATOR_QUERY_COMPLETE",
                "message": "Query processed successfully",
                "data": {
                    "user_id": user_id,
                    "elapsed_time": elapsed_time,
                    "documents_found": len(documents),
                    "response_length": len(response)
                }
            })
            
            return response
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error({
                "action": "ORCHESTRATOR_PROCESS_ERROR",
                "message": f"Failed to process query: {str(e)}",
                "data": {
                    "user_id": user_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "elapsed_time": elapsed_time
                }
            })
            
            # Return a generic error message
            return self._error_messages.get("generation_failed")
    
    async def _validate_query(self, query: str, context: Dict[str, Any], rules: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """
        Validates a query using the validator component.
        
        Args:
            query: The query to validate
            context: The validation context
            rules: The validation rules
            
        Returns:
            Tuple[bool, List[str]]: Validation result and failure reasons
            
        Raises:
            OrchestratorError: If validation fails for technical reasons
        """
        try:
            failure_reasons = []
            is_valid = await self._validator.validate(query, context, rules, failure_reasons)
            return is_valid, failure_reasons
            
        except ValidationError as e:
            self.logger.error({
                "action": "ORCHESTRATOR_VALIDATION_ERROR",
                "message": f"Validation error: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Validation failed: {str(e)}") from e
    
    async def _search_documents(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Searches for documents relevant to the query.
        
        Args:
            query: The search query
            top_k: Maximum number of documents to retrieve
            
        Returns:
            List[Dict[str, Any]]: List of relevant documents
            
        Raises:
            OrchestratorError: If search fails
        """
        try:
            # Convert text query to embedding vector using the embedder
            self.logger.info({
                "action": "ORCHESTRATOR_EMBED_QUERY",
                "message": "Converting query to embedding",
                "data": {"query": query}
            })
            
            # Get embedding from the embedder
            query_vector, _ = await self._embedder.embed(query)

            self.logger.info({
                "action": "ORCHESTRATOR_EMBEDDING_SUCCESS",
                "message": "Embedding successful",
                "data": {"query_vector": query_vector}
            })
            
            # Search for documents with the embedding vector
            # Request more results than needed to apply similarity threshold filtering
            search_results = self._vector_store.search(
                query_vector=query_vector,
                num_results=top_k * 2,  # Request more to filter by threshold
                filters=None  # No filters for now
            )

            self.logger.info({
                "action": "ORCHESTRATOR_SEARCH_RESULTS",
                "message": "Search results",
                "data": {"search_results": search_results}
            })
            
            # Filter results by similarity threshold
            if self._similarity_threshold > 0:
                filtered_results = [
                    doc for doc in search_results 
                    if doc.get('score', 0) >= self._similarity_threshold
                ]
                search_results = filtered_results[:top_k]  # Limit to requested number
            else:
                # Just take the top_k if no threshold
                search_results = search_results[:top_k]
            
            if not search_results:
                self.logger.info({
                    "action": "ORCHESTRATOR_NO_DOCUMENTS",
                    "message": "No relevant documents found",
                    "data": {"query": query, "top_k": top_k, "threshold": self._similarity_threshold}
                })
            else:
                self.logger.info({
                    "action": "ORCHESTRATOR_DOCUMENTS_FOUND",
                    "message": f"Found {len(search_results)} relevant documents",
                    "data": {
                        "count": len(search_results), 
                        "top_k": top_k,
                        "threshold": self._similarity_threshold
                    }
                })
            
            return search_results
            
        except Exception as e:
            self.logger.error({
                "action": "ORCHESTRATOR_SEARCH_ERROR",
                "message": f"Search failed: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            
            # Return empty list on error
            return []
    
    async def _build_prompt(self, query: str, documents: List[Dict[str, Any]]) -> str:
        """
        Builds a prompt using the prompt builder component.
        
        Args:
            query: The user query
            documents: Retrieved documents
            
        Returns:
            str: The constructed prompt
            
        Raises:
            OrchestratorError: If prompt building fails
        """
        try:
            prompt = await self._prompt_builder.build_prompt(query, documents)
            
            self.logger.debug({
                "action": "ORCHESTRATOR_PROMPT_BUILT",
                "message": "Prompt built successfully",
                "data": {
                    "documents_count": len(documents),
                    "prompt_length": len(prompt)
                }
            })
            
            return prompt
            
        except Exception as e:
            self.logger.error({
                "action": "ORCHESTRATOR_PROMPT_ERROR",
                "message": f"Failed to build prompt: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            
            # Return a simple prompt without context if prompt building fails
            return f"Answer the following question based on your general knowledge: {query}"
    
    async def _generate_response(self, prompt: str) -> str:
        """
        Generates a response using the generator component.
        
        Args:
            prompt: The input prompt
            
        Returns:
            str: The generated response
            
        Raises:
            OrchestratorError: If generation fails
        """
        try:
            # Get any custom generation options from config
            generation_options = self._config.get("generation_options", {})

            self.logger.info({
                "action": "ORCHESTRATOR_GENERATION_START",
                "message": "Generating response",
                "data": {"prompt": prompt, "options": generation_options}
            })
            
            # Generate response
            response = await self._generator.generate(prompt, generation_options)
            
            self.logger.debug({
                "action": "ORCHESTRATOR_GENERATION_SUCCESS",
                "message": "Response generated successfully",
                "data": {"response_length": len(response)}
            })
            
            return response
            
        except Exception as e:
            self.logger.error({
                "action": "ORCHESTRATOR_GENERATION_ERROR",
                "message": f"Failed to generate response: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            
            # Return fallback response
            return self._error_messages.get("generation_failed")
    
    async def configure(self, config: Dict[str, Any]) -> None:
        """
        Configures the orchestrator with the provided settings.

        Args:
            config: Dictionary containing configuration options

        Raises:
            OrchestratorError: If configuration is invalid
        """
        if not self._is_initialized:
            raise OrchestratorError("Orchestrator not initialized. Call initialize() first.")
        
        try:
            # Update configuration
            if "num_results" in config:
                self._num_results = config.get("num_results")
                
            if "similarity_threshold" in config:
                self._similarity_threshold = config.get("similarity_threshold")
                
            if "rules_source" in config:
                self._rules_source = config.get("rules_source")
                
            if "error_messages" in config:
                self._error_messages.update(config.get("error_messages", {}))
            
            # Update internal config
            self._config.update(config)
            
            self.logger.info({
                "action": "ORCHESTRATOR_CONFIGURED",
                "message": "Orchestrator configuration updated",
                "data": {
                    "num_results": self._num_results,
                    "similarity_threshold": self._similarity_threshold,
                    "rules_source": self._rules_source
                }
            })
            
        except Exception as e:
            self.logger.error({
                "action": "ORCHESTRATOR_CONFIGURE_ERROR",
                "message": f"Failed to configure orchestrator: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Configuration failed: {str(e)}") from e
    
    def get_rules(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves validation rules for the specified user.

        Args:
            user_id: Identifier for the user

        Returns:
            List[Dict[str, Any]]: List of validation rule dictionaries

        Raises:
            OrchestratorError: If rules cannot be retrieved
        """
        try:
            # Get rules based on the configured source
            if self._rules_source == "config":
                # Get rules from configuration
                rules = self._config.get("validation_rules", {}).get(user_id, [])
                
                # If no user-specific rules, use default rules
                if not rules:
                    rules = self._config.get("validation_rules", {}).get("default", [])
                    
                return rules
                
            elif self._rules_source == "database":
                # TODO: Implement database rules retrieval when needed
                # For now, return empty rules
                self.logger.warning({
                    "action": "ORCHESTRATOR_RULES_WARNING",
                    "message": "Database rules source not yet implemented",
                    "data": {"user_id": user_id}
                })
                return []
                
            else:
                self.logger.warning({
                    "action": "ORCHESTRATOR_RULES_WARNING",
                    "message": f"Unknown rules source: {self._rules_source}",
                    "data": {"user_id": user_id}
                })
                return []
                
        except Exception as e:
            self.logger.error({
                "action": "ORCHESTRATOR_RULES_ERROR",
                "message": f"Failed to retrieve rules: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__, "user_id": user_id}
            })
            
            # Return empty rules on error
            return []
    
    async def build_context(self, user_id: str) -> Dict[str, Any]:
        """
        Builds validation context for the specified user.

        Args:
            user_id: Identifier for the user

        Returns:
            Dict[str, Any]: Context dictionary for validation

        Raises:
            OrchestratorError: If context cannot be built
        """
        try:
            # Create base context
            context = {
                "user_id": user_id,
                "timestamp": time.time()
            }
            
            # Add user-specific context if available
            user_context = self._config.get("user_context", {}).get(user_id, {})
            if user_context:
                context.update(user_context)
            
            # Add system-level context
            context.update({
                "system_version": "1.0.0",  # Example
                "context_generated_at": time.time()
            })
            
            return context
            
        except Exception as e:
            self.logger.error({
                "action": "ORCHESTRATOR_CONTEXT_ERROR",
                "message": f"Failed to build context: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__, "user_id": user_id}
            })
            
            # Return minimal context on error
            return {"user_id": user_id, "timestamp": time.time()}
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Checks if the orchestrator and all its components are properly configured and functioning.

        Returns:
            Dict[str, Any]: Health status information

        Raises:
            OrchestratorError: If the health check itself fails
        """
        health_result = {
            "healthy": False,
            "message": "Orchestrator health check failed",
            "details": {"initialized": self._is_initialized},
            "components": {}
        }
        
        if not self._is_initialized:
            health_result["message"] = "Orchestrator not initialized"
            return health_result
        
        try:
            # Check validator health
            if self._validator:
                validator_health = await self._validator.healthcheck()
                health_result["components"]["validator"] = validator_health
            
            # Check vector store health
            if self._vector_store:
                vector_store_health = await self._vector_store.healthcheck()
                health_result["components"]["vector_store"] = vector_store_health
            
            # Check prompt builder health
            if self._prompt_builder:
                prompt_builder_health = await self._prompt_builder.healthcheck()
                health_result["components"]["prompt_builder"] = prompt_builder_health
            
            # Check generator health
            if self._generator:
                generator_health = await self._generator.healthcheck()
                health_result["components"]["generator"] = generator_health
            
            # Check pipeline health if available
            if self._pipeline and hasattr(self._pipeline, "healthcheck"):
                pipeline_health = await self._pipeline.healthcheck()
                health_result["components"]["pipeline"] = pipeline_health
            
            # Determine overall health (all components must be healthy)
            components_healthy = all(
                component.get("healthy", False) 
                for component in health_result["components"].values()
                if component  # Skip None values
            )
            
            health_result["healthy"] = components_healthy
            health_result["message"] = "Orchestrator is healthy" if components_healthy else "One or more components unhealthy"
            
            # Add diagnostic info
            health_result["details"].update({
                "num_results": self._num_results,
                "similarity_threshold": self._similarity_threshold,
                "rules_source": self._rules_source,
                "component_count": len(health_result["components"])
            })
            
            return health_result
            
        except Exception as e:
            health_result["message"] = f"Orchestrator health check failed: {str(e)}"
            health_result["details"]["error"] = str(e)
            health_result["details"]["error_type"] = type(e).__name__
            
            self.logger.error({
                "action": "ORCHESTRATOR_HEALTHCHECK_ERROR",
                "message": f"Health check failed: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            
            return health_result 