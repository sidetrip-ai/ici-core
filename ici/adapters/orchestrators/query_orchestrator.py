"""
QueryOrchestrator implementation that focuses solely on query processing.

This orchestrator is a specialized version that only handles query workflows,
allowing for cleaner separation of concerns between querying and ingestion.
"""

import os
import time
from typing import Dict, Any, List, Optional, Tuple
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
        
        start_time = time.time()
        
        try:
            # Generate standard user ID
            standard_user_id = await self._ensure_valid_user_id(source, user_id)
            
            self.logger.info({
                "action": "ORCHESTRATOR_PROCESS_QUERY",
                "message": "Processing query",
                "data": {
                    "source": source,
                    "user_id": standard_user_id,
                    "query_length": len(query) if query else 0
                }
            })
            
            # Step 1: Build context for validation
            context = await self.build_context(standard_user_id)
            
            # Add source to context
            context["source"] = source
            
            # Add any additional info to context
            if additional_info:
                context.update(additional_info)
            
            # Step 2: Get rules for validation
            rules = self.get_rules(standard_user_id)
            
            # Step 3: Validate the query
            is_valid, failure_reasons = await self._validate_query(query, context, rules)
            
            if not is_valid:
                self.logger.info({
                    "action": "ORCHESTRATOR_VALIDATION_FAILED",
                    "message": "Query validation failed",
                    "data": {
                        "user_id": standard_user_id,
                        "failure_reasons": failure_reasons
                    }
                })
                
                return self._error_messages.get("validation_failed")
            
            self.logger.info({
                "action": "ORCHESTRATOR_VALIDATION_SUCCESS",
                "message": "Query validation successful",
                "data": {"user_id": standard_user_id, "query": query}
            })
            
            # Step 4: Search for relevant documents
            documents = await self._search_documents(query, self._num_results)

            self.logger.info({
                "action": "ORCHESTRATOR_DOCUMENTS_FOUND",
                "message": "Documents found",
                "data": {"documents": documents, "query": query, "num_results": self._num_results}
            })
            
            # Step 5: Build prompt with documents and query
            prompt = await self._prompt_builder.build_prompt(query, documents)
            

            print("--------------------------------")
            print("Prompt: ", prompt)
            print("--------------------------------")
            
            # Step 6: Generate response
            response = await self._generate_response(prompt)
            
            # Log completion time
            elapsed_time = time.time() - start_time
            self.logger.info({
                "action": "ORCHESTRATOR_QUERY_COMPLETE",
                "message": "Query processed successfully",
                "data": {
                    "user_id": standard_user_id,
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
    
    async def get_context(self, source: str, user_id: str, query: str, additional_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieves the context for a given user ID.
        
        Args:
            user_id: The user ID to retrieve context for
        
        Returns:
            Dict[str, Any]: The context for the user ID
        """
        if not self._is_initialized:
            raise OrchestratorError("Orchestrator not initialized. Call initialize() first.")
        
        start_time = time.time()
        
        try:
            # Generate standard user ID
            standard_user_id = await self._ensure_valid_user_id(source, user_id)
            
            self.logger.info({
                "action": "ORCHESTRATOR_PROCESS_QUERY",
                "message": "Processing query",
                "data": {
                    "source": source,
                    "user_id": standard_user_id,
                    "query_length": len(query) if query else 0
                }
            })
            
            # Step 1: Build context for validation
            context = await self.build_context(standard_user_id)
            
            # Add source to context
            context["source"] = source
            
            # Add any additional info to context
            if additional_info:
                context.update(additional_info)
            
            # Step 2: Get rules for validation
            rules = self.get_rules(standard_user_id)
            
            # Step 3: Validate the query
            is_valid, failure_reasons = await self._validate_query(query, context, rules)
            
            if not is_valid:
                self.logger.info({
                    "action": "ORCHESTRATOR_VALIDATION_FAILED",
                    "message": "Query validation failed",
                    "data": {
                        "user_id": standard_user_id,
                        "failure_reasons": failure_reasons
                    }
                })
                
                return self._error_messages.get("validation_failed")
            
            self.logger.info({
                "action": "ORCHESTRATOR_VALIDATION_SUCCESS",
                "message": "Query validation successful",
                "data": {"user_id": standard_user_id, "query": query}
            })

            # to do, implement a recursive search for relevant documents with LLM
            # Step 4: Search for relevant documents
            documents = await self._search_documents(query, self._num_results)

            self.logger.info({
                "action": "ORCHESTRATOR_DOCUMENTS_FOUND",
                "message": "Documents found",
                "data": {"documents": documents, "query": query, "num_results": self._num_results}
            })
            
            # Step 5: Build prompt with documents and query
            prompt = await self._prompt_builder.build_prompt(query, documents)

            print("--------------------------------")
            print("Prompt: ", prompt)
            print("--------------------------------")
            
            # Log completion time
            return {
                "status": "success",
                "query": query,
                "prompt": prompt,
                "documents": documents
            }
            
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
            return {
                "status": "error",
                "query": query,
                "error": str(e)
            }
    
    async def _ensure_valid_user_id(self, source: str, provided_user_id: str) -> str:
        """
        Ensures a valid standardized user ID.
        
        Args:
            source: The source of the query (e.g., 'cli', 'web', 'api')
            provided_user_id: The user ID provided with the request
            
        Returns:
            str: A valid standardized user ID
            
        Raises:
            OrchestratorError: If user ID validation/generation fails
        """
        try:
            # For now, simply concatenate source and user ID
            standard_user_id = f"{source}:{provided_user_id}"
            
            self.logger.info({
                "action": "ORCHESTRATOR_USER_ID",
                "message": "Generated standard user ID",
                "data": {
                    "source": source,
                    "provided_user_id": provided_user_id,
                    "standard_user_id": standard_user_id
                }
            })
            
            return standard_user_id
            
        except Exception as e:
            self.logger.error({
                "action": "ORCHESTRATOR_USER_ID_ERROR",
                "message": f"Failed to ensure valid user ID: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            
            # Fallback to a simple user ID
            return f"{source}:{provided_user_id}"
    
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
        Searches for documents relevant to the query using hybrid retrieval with query expansion.
        
        Args:
            query: The search query
            top_k: Maximum number of documents to retrieve
            
        Returns:
            List[Dict[str, Any]]: List of relevant documents
            
        Raises:
            OrchestratorError: If search fails
        """
        try:
            # Check for source specification in the query (e.g. "from:telegram" or "source:whatsapp")
            source_match = re.search(r'(?:from|source):(\w+)', query, re.IGNORECASE)
            source = None
            
            if source_match:
                # Extract the source name
                source = source_match.group(1).lower()
                # Remove the source specification from the query
                query = re.sub(r'(?:from|source):\w+\s*', '', query).strip()
                
                self.logger.info({
                    "action": "ORCHESTRATOR_SOURCE_SPECIFIED",
                    "message": f"Source specified in query: {source}",
                    "data": {"source": source, "cleaned_query": query}
                })
            
            # Generate expanded queries for better retrieval
            expanded_queries = await self._expand_query(query)
            
            self.logger.info({
                "action": "ORCHESTRATOR_EXPANDED_QUERIES",
                "message": f"Using {len(expanded_queries)} expanded queries for search",
                "data": {"expanded_queries": expanded_queries}
            })
            
            # Results from all expanded queries
            all_semantic_results = []
            all_keyword_results = []
            
            # Process each expanded query
            for expanded_query in expanded_queries:
                # Convert text query to embedding vector using the embedder
                query_vector, _ = await self._embedder.embed(expanded_query)
                
                # Get collection name if source is specified
                collection_name = None
                if source:
                    collection_name = self._vector_store.find_collection_name(source)
                    self.logger.info({
                        "action": "ORCHESTRATOR_COLLECTION_FOR_SOURCE",
                        "message": f"Using collection '{collection_name}' for source '{source}'",
                        "data": {"source": source, "collection_name": collection_name}
                    })

                print("--------------------------------")
                print("expanded query: ", expanded_query)
                print("--------------------------------")
                print("collection name: ", collection_name)
                print("--------------------------------")
                
                # Perform semantic search for this expanded query
                semantic_results = await self._vector_store.search(
                    query_vector=query_vector,
                    num_results=max(5, top_k),  # Get at least 5 results per query
                    filters=None,
                    collection_name=collection_name
                )

                print("--------------------------------")
                print("semantic results: ", semantic_results)
                print("--------------------------------")
                
                # Add to combined results
                all_semantic_results.append(semantic_results)
                
                # Optional: Perform keyword search if available
                try:
                    if hasattr(self._vector_store, "keyword_search_async"):
                        print("--------------------------------")
                        print("keyword search async")
                        print("--------------------------------")
                        # Use the async version that waits for indexing to complete
                        keyword_results = await self._vector_store.keyword_search_async(
                            query=expanded_query,
                            num_results=max(5, top_k)
                        )
                        print("--------------------------------")
                        print("keyword results: ", keyword_results)
                        print("--------------------------------")
                        all_keyword_results.append(keyword_results)
                    elif hasattr(self._vector_store, "keyword_search"):
                        # Fallback to synchronous version
                        keyword_results = self._vector_store.keyword_search(
                            query=expanded_query,
                            num_results=max(5, top_k)
                        )
                        all_keyword_results.append(keyword_results)
                except Exception as e:
                    self.logger.warning({
                        "action": "ORCHESTRATOR_KEYWORD_SEARCH_ERROR",
                        "message": f"Keyword search failed: {str(e)}",
                        "data": {"error": str(e)}
                    })
            
            # Flatten all results while retaining origin
            flattened_semantic = []
            for results in all_semantic_results:
                flattened_semantic.extend(results)
                
            flattened_keyword = []
            for results in all_keyword_results:
                flattened_keyword.extend(results)
            
            # Combine results using reciprocal rank fusion
            combined_results = self._reciprocal_rank_fusion(
                [flattened_semantic, flattened_keyword], 
                k=60  # RRF constant
            )

            print("--------------------------------")
            print("combined results: ", combined_results)
            print("--------------------------------")
            
            # Apply similarity threshold filtering
            filtered_results = []
            print("--------------------------------")
            print("Starting similarity threshold filtering")
            print("--------------------------------")
            for doc in combined_results:
                print("--------------------------------")
                print("doc: ", doc)
                print("--------------------------------")
                # Skip documents with no score or below threshold
                if "score" not in doc or doc["score"] is None:
                    continue
                    
                if doc["score"] >= self._similarity_threshold:
                    filtered_results.append(doc)
                    
                # Break if we have enough results
                if len(filtered_results) >= top_k:
                    break
            
            self.logger.warning({
                "action": "ORCHESTRATOR_SEARCH_RESULTS",
                "message": "Search results",
                "data": {
                    "semantic_results": len(flattened_semantic),
                    "keyword_results": len(flattened_keyword),
                    "combined_results": len(combined_results),
                    "filtered_results": len(filtered_results),
                    "source_specified": source is not None,
                    "source": source
                }
            })
            
            return filtered_results[:top_k]
            
        except Exception as e:
            self.logger.error({
                "action": "ORCHESTRATOR_SEARCH_ERROR",
                "message": f"Failed to search documents: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Failed to search documents: {str(e)}") from e
    
    def _reciprocal_rank_fusion(self, result_lists: List[List[Dict[str, Any]]], k: int = 60) -> List[Dict[str, Any]]:
        """
        Combines multiple result lists using Reciprocal Rank Fusion.
        
        Args:
            result_lists: List of result lists to combine
            k: Constant for RRF calculation (prevents division by zero and controls impact)
            
        Returns:
            List[Dict[str, Any]]: Combined and reranked results
        """
        # Track document scores by ID
        doc_scores = {}
        doc_objects = {}
        
        # Process each result list
        for results in result_lists:
            if not results:
                continue
                
            for rank, doc in enumerate(results):
                # Get document ID or create one
                doc_id = doc.get("id", None)
                if doc_id is None:
                    # Create stable ID from content if none exists
                    text = doc.get("text", "")
                    metadata = doc.get("metadata", {})
                    doc_id = f"{hash(text)}_{hash(str(metadata))}"
                
                # Store document object for later
                doc_objects[doc_id] = doc
                
                # Calculate RRF score: 1/(k + rank)
                rrf_score = 1.0 / (k + rank)
                
                # Add to existing score or initialize
                if doc_id in doc_scores:
                    doc_scores[doc_id] += rrf_score
                else:
                    doc_scores[doc_id] = rrf_score
        
        # Sort documents by RRF score
        sorted_doc_ids = sorted(doc_scores.keys(), key=lambda x: doc_scores[x], reverse=True)
        
        # Create final result list with original documents
        combined_results = []
        for doc_id in sorted_doc_ids:
            doc = doc_objects[doc_id]
            # Add RRF score to document
            doc["rrf_score"] = doc_scores[doc_id]
            combined_results.append(doc)
            
        return combined_results
    
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
        
    async def _expand_query(self, query: str) -> List[str]:
        """
        Generate multiple versions of the query to improve retrieval.
        
        Args:
            query: The original query string
            
        Returns:
            List[str]: A list of expanded queries
        """
        expanded_queries = [query]  # Always include the original query
        
#         try:
#             # If LLM generator exists, use it for sophisticated expansions
#             if hasattr(self, '_generator') and self._generator:
#                 expansion_prompt = f"""Generate three alternative versions of the following query to improve document retrieval.
                
# Original Query: {query}

# Instructions:
# 1. Rephrase the query in different ways while preserving the core intent
# 2. Use synonyms for key terms
# 3. Make one version more specific and one more general
# 4. Format as a numbered list with no additional text

# Example:
# 1. [rephrased query 1]
# 2. [rephrased query 2]
# 3. [rephrased query 3]
# """
                
#                 try:
#                     result = await self._generator.generate(expansion_prompt)
                    
#                     # Extract expanded queries from the result
#                     lines = [line.strip() for line in result.split('\n') if line.strip()]
#                     for line in lines:
#                         # Extract the query part after any numbering (e.g., "1. query" -> "query")
#                         if re.match(r'^\d+\.', line):
#                             expanded_query = re.sub(r'^\d+\.\s*', '', line)
#                             if expanded_query and expanded_query not in expanded_queries:
#                                 expanded_queries.append(expanded_query)
                    
#                     self.logger.info({
#                         "action": "ORCHESTRATOR_QUERY_EXPANSION",
#                         "message": "Generated expanded queries using LLM",
#                         "data": {"original": query, "expanded": expanded_queries}
#                     })
                    
#                 except Exception as e:
#                     self.logger.warning({
#                         "action": "ORCHESTRATOR_QUERY_EXPANSION_ERROR",
#                         "message": f"Failed to expand query with LLM: {str(e)}",
#                         "data": {"error": str(e)}
#                     })
            
#             # Basic query expansion methods (if LLM expansion failed or wasn't available)
#             if len(expanded_queries) <= 1:
#                 # Remove question words
#                 question_words = ["what", "who", "where", "when", "why", "how", "is", "are", "can", "could", "would", "should"]
                
#                 # Simple rephrasing by removing question words
#                 for word in question_words:
#                     pattern = rf'\b{word}\b\s+'
#                     simplified = re.sub(pattern, '', query, flags=re.IGNORECASE)
#                     if simplified != query and simplified not in expanded_queries:
#                         expanded_queries.append(simplified)
                
#                 # Add some context-related terms
#                 expanded_queries.append(f"information about {query}")
                
#                 self.logger.info({
#                     "action": "ORCHESTRATOR_QUERY_EXPANSION",
#                     "message": "Generated expanded queries using rules",
#                     "data": {"original": query, "expanded": expanded_queries}
#                 })
        
#         except Exception as e:
#             self.logger.warning({
#                 "action": "ORCHESTRATOR_QUERY_EXPANSION_ERROR",
#                 "message": f"Error in query expansion: {str(e)}",
#                 "data": {"error": str(e)}
#             })
#             # Ensure we at least return the original query
#             if not expanded_queries:
#                 expanded_queries = [query]
        
        return expanded_queries 
    
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