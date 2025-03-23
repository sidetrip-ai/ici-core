from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class Orchestrator(ABC):
    """
    Interface for components that manage the query pipeline, coordinating components
    from validation to response generation.

    The Orchestrator centralizes query handling and rule/context management, ensuring a
    consistent workflow while delegating tasks to specialized components.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the orchestrator with configuration parameters.
        
        This method should be called after the orchestrator instance is created,
        before any other methods are used. Configuration should be loaded from
        a central configuration source (e.g., config.yaml).
        
        Returns:
            None
        
        Raises:
            Exception: If initialization fails for any reason.
        """
        pass

    @abstractmethod
    async def process_query(self, source: str, user_id: str, query: str, additional_info: Dict[str, Any]) -> str:
        """
        Manages query processing from validation to generation.

        Workflow:
        1. Retrieves validation rules dynamically based on user_id
        2. Builds context for validation based on user_id and runtime data
        3. Validates input with validator
        4. If validation fails, returns appropriate error message
        5. Generates query embedding
        6. Retrieves relevant documents with user-specific filters
        7. Constructs prompt with prompt_builder
        8. Generates response with generator
        9. Returns final output or error message

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
        pass

    @abstractmethod
    async def configure(self, config: Dict[str, Any]) -> None:
        """
        Configures the orchestrator with the provided settings.

        Configuration can include:
        - num_results: Number of documents to retrieve
        - rules_source: Where to fetch validation rules from
        - context_filters: Metadata filters to apply
        - error_messages: Custom error messages
        - retry: Retry configuration

        Args:
            config: Dictionary containing configuration options

        Raises:
            OrchestratorError: If configuration is invalid
        """
        pass

    @abstractmethod
    def get_rules(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves validation rules for the specified user.

        Retrieves rules from the configured rules source (database, config files).

        Args:
            user_id: Identifier for the user

        Returns:
            List[Dict[str, Any]]: List of validation rule dictionaries

        Raises:
            OrchestratorError: If rules cannot be retrieved
        """
        pass

    @abstractmethod
    async def build_context(self, user_id: str) -> Dict[str, Any]:
        """
        Builds validation context for the specified user.

        Assembles context data including user information, current time,
        and other relevant runtime data needed for validation.

        Args:
            user_id: Identifier for the user

        Returns:
            Dict[str, Any]: Context dictionary for validation

        Raises:
            OrchestratorError: If context cannot be built
        """
        pass

    @abstractmethod
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Checks if the orchestrator and all its components are properly configured and functioning.

        Returns:
            Dict[str, Any]: A dictionary containing health status information:
                {
                    'healthy': bool,  # Whether the orchestrator is functioning properly
                    'message': str,   # Optional message providing more details
                    'details': dict,  # Optional additional details about the health check
                    'components': {   # Health status of individual components
                        'validator': {...},
                        'embedder': {...},
                        'vector_store': {...},
                        'prompt_builder': {...},
                        'generator': {...}
                    }
                }

        Raises:
            OrchestratorError: If the health check itself encounters an error
        """
        pass
