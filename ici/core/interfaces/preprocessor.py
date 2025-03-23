from abc import ABC, abstractmethod
from typing import Any, List, Dict


class Preprocessor(ABC):
    """
    Interface for components that transform raw, source-specific data into a standardized format.

    Each Preprocessor is typically paired with a specific Ingestor to handle its unique data
    structure. It transforms raw data into a consistent document format for downstream processing.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the preprocessor with configuration parameters.
        
        This method should be called after the preprocessor instance is created,
        before any other methods are used. Configuration should be loaded from
        a central configuration source (e.g., config.yaml).
        
        Returns:
            None
        
        Raises:
            Exception: If initialization fails for any reason.
        """
        pass

    @abstractmethod
    def preprocess(self, raw_data: Any) -> List[Dict[str, Any]]:
        """
        Transforms raw data into a list of standardized documents.

        The standardized document format should include at minimum:
        - 'text': str - The primary content to be embedded
        - 'metadata': Dict[str, Any] - Contextual data about the document

        Args:
            raw_data: Source-specific data from an Ingestor

        Returns:
            List[Dict[str, Any]]: A list of standardized documents, each with 'text' and 'metadata' fields.

        Raises:
            PreprocessorError: If preprocessing fails for any reason.
        """
        pass

    @abstractmethod
    def healthcheck(self) -> Dict[str, Any]:
        """
        Checks if the preprocessor is properly configured and functioning.

        Returns:
            Dict[str, Any]: A dictionary containing health status information:
                {
                    'healthy': bool,  # Whether the preprocessor is functioning properly
                    'message': str,   # Optional message providing more details
                    'details': dict   # Optional additional details about the health check
                }

        Raises:
            PreprocessorError: If the health check itself encounters an error.
        """
        pass
