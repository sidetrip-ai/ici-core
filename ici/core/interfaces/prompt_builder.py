from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class PromptBuilder(ABC):
    """
    Interface for components that construct prompts for language models by integrating
    user input with retrieved documents.

    The PromptBuilder combines user input with relevant context to create effective prompts,
    handling edge cases and providing fallback mechanisms.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the prompt builder with configuration parameters.
        
        This method should be called after the prompt builder instance is created,
        before any other methods are used. Configuration should be loaded from
        a central configuration source (e.g., config.yaml).
        
        Returns:
            None
        
        Raises:
            Exception: If initialization fails for any reason.
        """
        pass

    @abstractmethod
    async def build_prompt(
        self,
        input: str,
        documents: List[Dict[str, Any]],
        max_context_length: Optional[int] = None,
    ) -> str:
        """
        Constructs a prompt from the input and retrieved documents.

        Handles edge cases through specific fallback mechanisms:
        - No documents: Uses a fallback template
        - Empty or invalid input: Returns standardized error prompt
        - Excessive content: Implements truncation strategies to fit model context windows

        Args:
            input: The user input/question
            documents: List of relevant documents from the vector store
            max_context_length: Optional maximum length for context section

        Returns:
            str: Complete prompt for the language model

        Raises:
            PromptBuilderError: If prompt construction fails for any reason
        """
        pass

    @abstractmethod
    async def set_template(self, template: str) -> None:
        """
        Sets a custom template for the prompt builder.

        The template should include placeholders for context and question:
        "Context:\n{context}\n\nQuestion: {question}"

        Args:
            template: The template string with {context} and {question} placeholders

        Raises:
            PromptBuilderError: If the template is invalid
        """
        pass

    @abstractmethod
    def set_fallback_template(self, template: str) -> None:
        """
        Sets a custom fallback template for when no documents are available.

        The template should include a placeholder for the question:
        "Answer based on general knowledge: {question}"

        Args:
            template: The fallback template string with {question} placeholder

        Raises:
            PromptBuilderError: If the template is invalid
        """
        pass

    @abstractmethod
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Checks if the prompt builder is properly configured and functioning.

        Returns:
            Dict[str, Any]: A dictionary containing health status information:
                {
                    'healthy': bool,  # Whether the prompt builder is functioning properly
                    'message': str,   # Optional message providing more details
                    'details': dict   # Optional additional details about the health check
                }

        Raises:
            PromptBuilderError: If the health check itself encounters an error
        """
        pass
