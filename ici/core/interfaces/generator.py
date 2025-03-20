from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class Generator(ABC):
    """
    Interface for components that produce responses using language models.

    The Generator abstracts the language model implementation, supporting multiple
    providers including OpenAI, xAI, Anthropic, and local models, with configurable parameters.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the generator with configuration parameters.
        
        This method should be called after the generator instance is created,
        before any other methods are used. Configuration should be loaded from
        a central configuration source (e.g., config.yaml).
        
        Returns:
            None
        
        Raises:
            Exception: If initialization fails for any reason.
        """
        pass

    @abstractmethod
    def generate(
        self, prompt: str, generation_options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generates an output based on the provided prompt.

        Generation options can include parameters like:
        - temperature: Controls randomness (0.0-2.0)
        - max_tokens: Limits response length
        - top_p: Controls diversity via nucleus sampling
        - frequency_penalty: Reduces word repetition
        - presence_penalty: Reduces topic repetition

        Args:
            prompt: The input prompt for the language model
            generation_options: Optional parameters to override defaults

        Returns:
            str: The generated text response

        Raises:
            GenerationError: If text generation fails for any reason
        """
        pass

    @abstractmethod
    def set_model(self, model: str) -> None:
        """
        Sets the specific model to use for generation.

        Args:
            model: The model identifier (e.g., 'gpt-4', 'claude-2', 'mistral-7b')

        Raises:
            GenerationError: If the model is invalid or unavailable
        """
        pass

    @abstractmethod
    def set_default_options(self, options: Dict[str, Any]) -> None:
        """
        Sets default options for all generation requests.

        Args:
            options: Dictionary of default generation parameters

        Raises:
            GenerationError: If any option is invalid
        """
        pass

    @abstractmethod
    def healthcheck(self) -> Dict[str, Any]:
        """
        Checks if the generator is properly configured and can connect to the language model.

        Returns:
            Dict[str, Any]: A dictionary containing health status information:
                {
                    'healthy': bool,  # Whether the generator is functioning properly
                    'message': str,   # Optional message providing more details
                    'details': dict   # Optional additional details about the health check
                }

        Raises:
            GenerationError: If the health check itself encounters an error
        """
        pass
