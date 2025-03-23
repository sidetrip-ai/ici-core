from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple


class Embedder(ABC):
    """
    Interface for components that generate vector embeddings from text data.

    The Embedder is shared between Ingestion and Query Pipelines to ensure
    identical embedding logic, crucial for accurate similarity matching.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the embedder with configuration parameters.
        
        This method should be called after the embedder instance is created,
        before any other methods are used. Configuration should be loaded from
        a central configuration source (e.g., config.yaml).
        
        Returns:
            None
        
        Raises:
            Exception: If initialization fails for any reason.
        """
        pass

    @abstractmethod
    async def embed(self, text: str) -> Tuple[List[float], Optional[Dict[str, Any]]]:
        """
        Generates a vector embedding from the input text.

        Args:
            text: The text to embed

        Returns:
            List[float]: A fixed-length vector of floats representing the text embedding

        Raises:
            EmbeddingError: If embedding generation fails for any reason
        """
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[Tuple[List[float], Optional[Dict[str, Any]]]]:
        """
        Generates vector embeddings for multiple texts.

        This method should optimize batch processing for efficiency when embedding
        multiple texts at once.

        Args:
            texts: List of texts to embed

        Returns:
            List[List[float]]: A list of fixed-length vectors, one for each input text

        Raises:
            EmbeddingError: If batch embedding generation fails for any reason
        """
        pass

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """
        Returns the dimensionality of the embeddings produced by this embedder.

        Returns:
            int: The number of dimensions in the embedding vectors
        """
        pass

    @abstractmethod
    def healthcheck(self) -> Dict[str, Any]:
        """
        Checks if the embedder is properly configured and functioning.

        Returns:
            Dict[str, Any]: A dictionary containing health status information:
                {
                    'healthy': bool,  # Whether the embedder is functioning properly
                    'message': str,   # Optional message providing more details
                    'details': dict   # Optional additional details about the health check
                }

        Raises:
            EmbeddingError: If the health check itself encounters an error
        """
        pass

    def arguments(self) -> Dict[str, Any]:
        """
        Get the arguments used to initialize this embedder.
        
        Returns:
            Dict[str, Any]: Dictionary of initialization arguments
        """
        return {}

        
