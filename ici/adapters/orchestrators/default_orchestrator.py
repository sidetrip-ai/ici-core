"""
DefaultOrchestrator implementation for the Orchestrator interface.

This module provides an implementation of the Orchestrator interface
that coordinates the processing of queries through validation,
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
    Default Orchestrator implementation for processing queries.
    
    Coordinates the flow from validation to generation for messages.
    Supports multi-turn conversations with chat history functionality.
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
                    print("Fetching recent initial data (can take a while)...")
                    await self._pipeline.start()
                    print("Pipeline stored data successfully")
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
    
    async def _initialize_chat_components(self) -> None:
        """
        Initialize chat-specific components.
        
        Creates and initializes chat history manager and user ID generator.
        
        Raises:
            OrchestratorError: If component initialization fails
        """
        try:
            self.logger.info({
                "action": "ORCHESTRATOR_CHAT_INIT_START",
                "message": "Initializing chat components"
            })
            
            # Initialize chat history manager
            self._chat_history_manager = JSONChatHistoryManager()
            await self._chat_history_manager.initialize()
            
            # Initialize user ID generator
            self._user_id_generator = DefaultUserIDGenerator()
            await self._user_id_generator.initialize()
            
            self.logger.info({
                "action": "ORCHESTRATOR_CHAT_INIT_SUCCESS",
                "message": "Chat components initialized successfully"
            })
            
        except Exception as e:
            self.logger.error({
                "action": "ORCHESTRATOR_CHAT_INIT_ERROR",
                "message": f"Failed to initialize chat components: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Chat component initialization failed: {str(e)}") from e
    
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
            print("Initializing ingestion pipeline...")
            self._pipeline = DefaultIngestionPipeline(logger_name="orchestrator.pipeline")
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
        
        start_time = time.time()
        
        try:
            # Generate standard user ID
            standard_user_id = await self._ensure_valid_user_id(source, user_id)
            
            # Check if query is a special command
            if query.strip().startswith("/"):
                command = query.strip().split()[0].lower()
                if command in self._commands:
                    self.logger.info({
                        "action": "ORCHESTRATOR_COMMAND",
                        "message": f"Processing command: {command}",
                        "data": {"user_id": standard_user_id, "command": command}
                    })
                    return await self._commands[command](standard_user_id, query)
            
            # Ensure user has an active chat
            chat_id = await self._ensure_active_chat(standard_user_id)
            
            self.logger.info({
                "action": "ORCHESTRATOR_PROCESS_QUERY",
                "message": "Processing query with chat context",
                "data": {
                    "source": source,
                    "user_id": standard_user_id,
                    "chat_id": chat_id,
                    "query_length": len(query) if query else 0
                }
            })
            
            # Store user message in chat history
            await self._chat_history_manager.add_message(
                chat_id=chat_id,
                content=query,
                role="user"
            )
            
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
                
                # Store system message about validation failure
                error_message = self._error_messages.get("validation_failed")
                await self._chat_history_manager.add_message(
                    chat_id=chat_id,
                    content=error_message,
                    role="assistant"
                )
                return error_message
            
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
            
            # Get chat history for context
            chat_messages = await self._chat_history_manager.get_messages(chat_id)
            
            # Step 5: Build prompt with documents, query, and chat history
            prompt = await self._build_chat_prompt(query, documents, chat_messages)
            
            # Step 6: Generate response
            response = await self._generate_response(prompt)
            
            # Store assistant response in chat history
            await self._chat_history_manager.add_message(
                chat_id=chat_id,
                content=response,
                role="assistant"
            )
            
            # Try to generate a title for new chats
            if len(chat_messages) <= 2:  # Only user's first message + system greeting
                await self._chat_history_manager.generate_title(chat_id)
            
            # Log completion time
            elapsed_time = time.time() - start_time
            self.logger.info({
                "action": "ORCHESTRATOR_QUERY_COMPLETE",
                "message": "Query processed successfully",
                "data": {
                    "user_id": standard_user_id,
                    "chat_id": chat_id,
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
    
    async def _ensure_valid_user_id(self, source: str, provided_user_id: str) -> str:
        """
        Ensures a valid standardized user ID.
        
        If the provided user ID is already valid, it's returned as is.
        Otherwise, a new standardized user ID is generated.
        
        Args:
            source: The source of the query (e.g., 'cli', 'web', 'api')
            provided_user_id: The user ID provided with the request
            
        Returns:
            str: A valid standardized user ID
            
        Raises:
            OrchestratorError: If user ID validation/generation fails
        """
        try:
            # Check if the provided user ID is already valid
            if await self._user_id_generator.validate_id(provided_user_id):
                return provided_user_id
            
            # Generate a new standard user ID
            standard_user_id = await self._user_id_generator.generate_id(source, provided_user_id)
            
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
    
    async def _ensure_active_chat(self, user_id: str) -> str:
        """
        Ensures the user has an active chat session.
        
        If the user already has an active chat, returns its ID.
        Otherwise, creates a new chat and returns the new ID.
        
        Args:
            user_id: The standardized user ID
            
        Returns:
            str: The active chat ID for the user
            
        Raises:
            OrchestratorError: If chat creation/retrieval fails
        """
        try:
            # Check if user already has an active chat
            if user_id in self._active_chats:
                return self._active_chats[user_id]
            
            # Create a new chat for the user
            chat_id = await self._chat_history_manager.create_chat(user_id)
            
            # Add a system greeting message
            await self._chat_history_manager.add_message(
                chat_id=chat_id,
                content="Hello! I'm your AI assistant. How can I help you today?",
                role="system"
            )
            
            # Store the active chat ID
            self._active_chats[user_id] = chat_id
            
            self.logger.info({
                "action": "ORCHESTRATOR_NEW_CHAT",
                "message": "Created new chat for user",
                "data": {"user_id": user_id, "chat_id": chat_id}
            })
            
            return chat_id
            
        except Exception as e:
            self.logger.error({
                "action": "ORCHESTRATOR_CHAT_ERROR",
                "message": f"Failed to ensure active chat: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            
            # Fallback to a temporary chat ID
            temp_chat_id = f"temp_{int(time.time())}"
            self._active_chats[user_id] = temp_chat_id
            return temp_chat_id
    
    async def _build_chat_prompt(
        self, 
        query: str, 
        documents: List[Dict[str, Any]],
        chat_messages: List[Dict[str, Any]]
    ) -> str:
        """
        Builds a prompt that includes chat history context.
        
        Args:
            query: The user query
            documents: Retrieved documents
            chat_messages: Chat history messages
            
        Returns:
            str: The constructed prompt
            
        Raises:
            PromptBuilderError: If prompt building fails
        """
        try:
            # Format chat history as context
            chat_context = self._format_chat_history(chat_messages)
            
            # Add document context
            doc_context = self._format_documents(documents)
            
            # Combine contexts
            combined_context = ""
            if chat_context and doc_context:
                combined_context = f"Chat history:\n{chat_context}\n\nRelevant information:\n{doc_context}"
            elif chat_context:
                combined_context = f"Chat history:\n{chat_context}"
            elif doc_context:
                combined_context = f"Relevant information:\n{doc_context}"
            
            # Build the prompt using the prompt builder
            # For backward compatibility, we'll use the existing prompt builder's template
            # but replace the context with our combined context
            prompt = await self._prompt_builder.build_prompt(query, [{"text": combined_context}])
            
            self.logger.debug({
                "action": "ORCHESTRATOR_PROMPT_BUILT",
                "message": "Chat prompt built successfully",
                "data": {
                    "documents_count": len(documents),
                    "messages_count": len(chat_messages),
                    "prompt_length": len(prompt)
                }
            })
            
            return prompt
            
        except Exception as e:
            self.logger.error({
                "action": "ORCHESTRATOR_PROMPT_ERROR",
                "message": f"Failed to build chat prompt: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            
            # Return a simple prompt without context if prompt building fails
            return f"Answer the following question based on your general knowledge: {query}"
    
    def _format_chat_history(self, messages: List[Dict[str, Any]]) -> str:
        """
        Formats chat history messages into a string for the prompt.
        
        Args:
            messages: List of chat messages
            
        Returns:
            str: Formatted chat history
        """
        if not messages:
            return ""
        
        formatted_messages = []
        
        for msg in messages:
            role = msg.get("role", "").upper()
            content = msg.get("content", "")
            
            if role == "SYSTEM":
                # Skip system messages in the context
                continue
                
            formatted_messages.append(f"{role}: {content}")
        
        return "\n\n".join(formatted_messages)
    
    def _format_documents(self, documents: List[Dict[str, Any]]) -> str:
        """
        Formats retrieved documents into a string for the prompt.
        
        Args:
            documents: List of documents
            
        Returns:
            str: Formatted documents
        """
        if not documents:
            return ""
        
        doc_texts = []
        
        for doc in documents:
            if "text" in doc:
                doc_texts.append(doc["text"])
            elif "content" in doc:
                doc_texts.append(doc["content"])
        
        return "\n\n".join(doc_texts)
    
    async def _handle_new_chat_command(self, user_id: str, query: str) -> str:
        """
        Handles the /new command to create a new chat.
        
        Args:
            user_id: The user ID
            query: The full command text
            
        Returns:
            str: Response message
        """
        try:
            # Create a new chat
            chat_id = await self._chat_history_manager.create_chat(user_id)
            
            # Update active chat
            self._active_chats[user_id] = chat_id
            
            # Add system greeting
            await self._chat_history_manager.add_message(
                chat_id=chat_id,
                content="New conversation started. How can I help you today?",
                role="system"
            )
            
            self.logger.info({
                "action": "ORCHESTRATOR_NEW_CHAT_COMMAND",
                "message": "Created new chat via command",
                "data": {"user_id": user_id, "chat_id": chat_id}
            })
            
            return "I've started a new conversation for you. How can I help you today?"
            
        except Exception as e:
            self.logger.error({
                "action": "ORCHESTRATOR_NEW_CHAT_ERROR",
                "message": f"Failed to create new chat: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            
            return "I couldn't create a new conversation. Please try again later."
    
    async def _handle_help_command(self, user_id: str, query: str) -> str:
        """
        Handles the /help command.
        
        Args:
            user_id: The user ID
            query: The full command text
            
        Returns:
            str: Response message
        """
        help_text = (
            "Available commands:\n"
            "/new - Start a new conversation\n"
            "/help - Show this help message\n\n"
            "You can ask me questions, and I'll search for relevant information to assist you."
        )
        
        # Store the help message in the active chat
        chat_id = await self._ensure_active_chat(user_id)
        await self._chat_history_manager.add_message(
            chat_id=chat_id,
            content=help_text,
            role="assistant"
        )
        
        return help_text
    
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
                
            # Check chat history manager health
            if self._chat_history_manager:
                chat_manager_health = await self._chat_history_manager.healthcheck()
                health_result["components"]["chat_history_manager"] = chat_manager_health
            
            # Check user ID generator health
            if self._user_id_generator:
                user_id_generator_health = await self._user_id_generator.healthcheck()
                health_result["components"]["user_id_generator"] = user_id_generator_health
            
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
                "component_count": len(health_result["components"]),
                "active_chats_count": len(self._active_chats),
                "supported_commands": list(self._commands.keys())
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