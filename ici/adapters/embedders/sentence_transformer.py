"""
SentenceTransformer-based implementation of the Embedder interface.

This module provides an implementation of the Embedder interface using
the sentence-transformers library for high-quality text embeddings.
"""

import os
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import torch
from sentence_transformers import SentenceTransformer

from ici.core.interfaces.embedder import Embedder
from ici.core.exceptions import EmbeddingError
from ici.utils.config import get_component_config
from ici.adapters.loggers.structured_logger import StructuredLogger


class SentenceTransformerEmbedder(Embedder):
    """
    Embedder implementation using SentenceTransformers library.
    
    This class provides methods to generate vector embeddings from text
    using pre-trained sentence transformer models.
    """
    
    def __init__(self, logger_name: str = "embedder"):
        """
        Initialize the SentenceTransformerEmbedder.
        
        Args:
            logger_name: Name to use for the logger
        """
        self.logger = StructuredLogger(name=logger_name)
        self._model = None
        self._model_name = None
        self._is_initialized = False
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
    
    async def initialize(self) -> None:
        """
        Initialize the embedder with configuration parameters.
        
        Loads the specified SentenceTransformer model based on configuration.
        
        Returns:
            None
            
        Raises:
            EmbeddingError: If initialization fails
        """
        try:
            self.logger.info({
                "action": "EMBEDDER_INIT_START",
                "message": "Initializing SentenceTransformer embedder"
            })
            
            # Load embedder configuration
            embedder_config = get_component_config("embedder", self._config_path)
            
            # Extract model name with default
            self._model_name = embedder_config.get(
                "model_name", 
                "all-MiniLM-L6-v2"  # Default model: good balance of speed and quality
            )
            
            # Load the model
            self._model = SentenceTransformer(self._model_name, device=self._device)
            
            # Set initialization flag
            self._is_initialized = True
            
            self.logger.info({
                "action": "EMBEDDER_INIT_SUCCESS",
                "message": f"Successfully initialized SentenceTransformer embedder with model '{self._model_name}'",
                "data": {
                    "model_name": self._model_name,
                    "device": self._device,
                    "embedding_dimensions": self.dimensions
                }
            })
            
        except Exception as e:
            self.logger.error({
                "action": "EMBEDDER_INIT_ERROR",
                "message": f"Failed to initialize SentenceTransformer embedder: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise EmbeddingError(f"Embedder initialization failed: {str(e)}") from e
    
    async def embed(self, text: str) -> Tuple[List[float], Optional[Dict[str, Any]]]:
        """
        Generates a vector embedding from the input text.
        
        Args:
            text: The text to embed
            
        Returns:
            Tuple[List[float], Optional[Dict[str, Any]]]: 
                - A fixed-length vector of floats representing the text embedding
                - Optional metadata about the embedding
            
        Raises:
            EmbeddingError: If embedding generation fails or embedder not initialized
        """
        if not self._is_initialized:
            raise EmbeddingError("Embedder not initialized. Call initialize() first.")
        
        try:
            if not text or not isinstance(text, str):
                self.logger.warning({
                    "action": "EMBEDDER_INVALID_INPUT",
                    "message": "Invalid input for embedding",
                    "data": {"input_type": type(text).__name__}
                })
                # Return zero vector for empty/invalid inputs with warning metadata
                return [0.0] * self.dimensions, {"warning": "Invalid or empty input"}
            
            # Generate embedding
            embedding = self._model.encode(text, convert_to_numpy=True).tolist()
            
            self.logger.debug({
                "action": "EMBEDDER_GENERATE",
                "message": "Generated embedding",
                "data": {
                    "text_length": len(text),
                    "embedding_size": len(embedding)
                }
            })
            
            # Return embedding vector and metadata
            metadata = {
                "model": self._model_name,
                "text_length": len(text)
            }
            
            return embedding, metadata
            
        except Exception as e:
            self.logger.error({
                "action": "EMBEDDER_ERROR",
                "message": f"Failed to generate embedding: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise EmbeddingError(f"Embedding generation failed: {str(e)}") from e
    
    async def embed_batch(self, texts: List[str]) -> List[Tuple[List[float], Optional[Dict[str, Any]]]]:
        """
        Generates vector embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List[Tuple[List[float], Optional[Dict[str, Any]]]]: 
                A list of tuples, each containing:
                - A fixed-length vector of floats
                - Optional metadata about the embedding
            
        Raises:
            EmbeddingError: If batch embedding generation fails
        """
        if not self._is_initialized:
            raise EmbeddingError("Embedder not initialized. Call initialize() first.")
        
        try:
            if not texts:
                self.logger.warning({
                    "action": "EMBEDDER_BATCH_EMPTY",
                    "message": "Empty batch for embedding"
                })
                return []
            
            # Process texts for embedding
            valid_texts = []
            invalid_indices = []
            
            for i, text in enumerate(texts):
                if not isinstance(text, str) or not text:
                    self.logger.warning({
                        "action": "EMBEDDER_INVALID_BATCH_ITEM",
                        "message": f"Invalid item at index {i} in batch",
                        "data": {"item_type": type(text).__name__}
                    })
                    valid_texts.append("")  # Add empty string as placeholder
                    invalid_indices.append(i)
                else:
                    valid_texts.append(text)
            
            # Generate embeddings in batch
            embeddings = self._model.encode(valid_texts, convert_to_numpy=True).tolist()
            
            # Create result with metadata
            results = []
            for i, embedding in enumerate(embeddings):
                if i in invalid_indices:
                    metadata = {"warning": "Invalid or empty input", "model": self._model_name}
                else:
                    metadata = {
                        "model": self._model_name,
                        "text_length": len(valid_texts[i])
                    }
                results.append((embedding, metadata))
            
            self.logger.debug({
                "action": "EMBEDDER_BATCH_GENERATE",
                "message": "Generated batch embeddings",
                "data": {
                    "batch_size": len(texts),
                    "embedding_size": self.dimensions
                }
            })
            
            return results
            
        except Exception as e:
            self.logger.error({
                "action": "EMBEDDER_BATCH_ERROR",
                "message": f"Failed to generate batch embeddings: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise EmbeddingError(f"Batch embedding generation failed: {str(e)}") from e
    
    @property
    def dimensions(self) -> int:
        """
        Returns the dimensionality of the embeddings produced by this embedder.
        
        Returns:
            int: The number of dimensions in the embedding vectors
            
        Raises:
            EmbeddingError: If the embedder is not initialized
        """
        if not self._is_initialized:
            raise EmbeddingError("Embedder not initialized. Call initialize() first.")
        
        return self._model.get_sentence_embedding_dimension()
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Check if the embedder is properly configured and can generate embeddings.
        
        Returns:
            Dict[str, Any]: Health status information
            
        Raises:
            Exception: If the health check itself fails
        """
        health_result = {
            "healthy": False,
            "message": "SentenceTransformer embedder health check failed",
            "details": {
                "model_name": self._model_name,
                "device": self._device,
                "initialized": self._model is not None
            }
        }
        
        if not self._model:
            health_result["message"] = "Model not initialized"
            return health_result
            
        try:
            # Test embedding generation with a simple text
            test_text = "This is a test sentence for embedding."
            
            # Generate a test embedding
            embedding, _ = await self.embed(test_text)
            
            # Check dimensions
            test_embedding = embedding
            
            if test_embedding and len(test_embedding) == self.dimensions:
                health_result["healthy"] = True
                health_result["message"] = f"SentenceTransformer embedder healthy using model '{self._model_name}'"
                health_result["details"]["embedding_dimensions"] = self.dimensions
                health_result["details"]["test_successful"] = True
            
            return health_result
            
        except Exception as e:
            self.logger.error({
                "action": "EMBEDDER_HEALTHCHECK_ERROR",
                "message": f"Health check failed: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            health_result["details"]["error"] = str(e)
            health_result["details"]["error_type"] = type(e).__name__
            
            return health_result 