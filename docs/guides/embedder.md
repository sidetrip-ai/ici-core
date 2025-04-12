# Embedder Component Guide

## Overview

An Embedder converts text into vector embeddings (numerical representations) that capture semantic meaning. These embeddings enable semantic search, allowing the system to find documents with similar meaning rather than just matching keywords. The embedder is a critical component that determines the quality of document retrieval.

Embedder is ideallty needed when you want to improve exsting system performance. If you want to work on connecting new data source, you don't need to think about embedder at all.

## Interface

All embedders must implement the `Embedder` interface defined in `ici/core/interfaces/embedder.py`:

```python
class Embedder(ABC):
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the embedder with configuration parameters."""
        pass
        
    @abstractmethod
    async def embed(self, text: str) -> Tuple[List[float], Dict[str, Any]]:
        """
        Generate an embedding vector for the given text.
        
        Args:
            text: The text to embed
            
        Returns:
            Tuple[List[float], Dict[str, Any]]: The embedding vector and metadata
        """
        pass
```

## Expected Input and Output

### Input Format

Embedders receive text strings that need to be converted to vector embeddings:

```python
text = "This is a sample text that needs to be embedded."
```

### Output Format

Embedders should return a tuple containing:
1. The embedding vector (a list of floating-point numbers)
2. Metadata about the embedding (optional)

```python
(
    [0.1, 0.2, 0.3, ..., 0.768],  # Vector with typically 768 or more dimensions
    {
        "model": "sentence-transformer-base",
        "dimensions": 768,
        "version": "1.0.0",
        "elapsed_time_ms": 15.2,
        # Other metadata
    }
)
```

## Implementing a Custom Embedder

Here's a step-by-step guide to implementing a custom embedder:

### 1. Create a new class

Create a new file in `ici/adapters/embedders/` for your custom embedder:

```python
"""
Custom embedder implementation using a specific model or API.
"""

import os
import time
from typing import Dict, Any, List, Tuple, Optional

from ici.core.interfaces.embedder import Embedder
from ici.core.exceptions import EmbeddingError
from ici.adapters.loggers import StructuredLogger
from ici.utils.config import get_component_config

class CustomEmbedder(Embedder):
    """
    Embedder implementation using a specific model or API.
    
    This embedder transforms text into vector representations suitable
    for semantic search and retrieval.
    
    Configuration options:
    - model_name: Name of the embedding model to use
    - dimensions: Vector dimensions
    - cache_dir: Local directory to cache models
    """
    
    def __init__(self, logger_name: str = "custom_embedder"):
        """
        Initialize the custom embedder.
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = StructuredLogger(name=logger_name)
        self._is_initialized = False
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        
        # Default configuration
        self._model_name = "default-model"
        self._dimensions = 768
        self._cache_dir = "./cache"
        self._model = None
```

### 2. Implement the initialize method

Load your configuration from config.yaml and initialize the embedding model:

```python
async def initialize(self) -> None:
    """
    Initialize the embedder with configuration parameters.
    
    Loads configuration from config.yaml and sets up the embedding model.
    
    Returns:
        None
        
    Raises:
        EmbeddingError: If initialization fails
    """
    try:
        self.logger.info({
            "action": "EMBEDDER_INIT_START",
            "message": "Initializing custom embedder"
        })
        
        # Load embedder configuration
        try:
            embedder_config = get_component_config("embedders.custom", self._config_path)
            
            # Extract configuration with defaults
            if embedder_config:
                self._model_name = embedder_config.get("model_name", self._model_name)
                self._dimensions = int(embedder_config.get("dimensions", self._dimensions))
                self._cache_dir = embedder_config.get("cache_dir", self._cache_dir)
                
                # Additional configuration options can be extracted here
                
                self.logger.info({
                    "action": "EMBEDDER_CONFIG_LOADED",
                    "message": "Loaded embedder configuration",
                    "data": {
                        "model_name": self._model_name,
                        "dimensions": self._dimensions,
                        "cache_dir": self._cache_dir
                    }
                })
            
        except Exception as e:
            # Use defaults if configuration loading fails
            self.logger.warning({
                "action": "EMBEDDER_CONFIG_WARNING",
                "message": f"Failed to load configuration: {str(e)}. Using defaults.",
                "data": {"error": str(e)}
            })
        
        # Initialize the embedding model
        try:
            # Import your model framework here
            # For example, if using sentence-transformers:
            # from sentence_transformers import SentenceTransformer
            # self._model = SentenceTransformer(self._model_name, cache_folder=self._cache_dir)
            
            # Or if using an API-based model:
            # self._api_key = embedder_config.get("api_key")
            # self._api_url = embedder_config.get("api_url")
            
            # Placeholder for model initialization
            self._model = self._initialize_model()
            
            self.logger.info({
                "action": "EMBEDDER_MODEL_LOADED",
                "message": f"Loaded embedding model: {self._model_name}",
                "data": {"model_name": self._model_name}
            })
            
        except Exception as e:
            self.logger.error({
                "action": "EMBEDDER_MODEL_ERROR",
                "message": f"Failed to load embedding model: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise EmbeddingError(f"Failed to load embedding model: {str(e)}") from e
        
        self._is_initialized = True
        
        self.logger.info({
            "action": "EMBEDDER_INIT_SUCCESS",
            "message": "Custom embedder initialized successfully"
        })
        
    except Exception as e:
        self.logger.error({
            "action": "EMBEDDER_INIT_ERROR",
            "message": f"Failed to initialize embedder: {str(e)}",
            "data": {"error": str(e), "error_type": type(e).__name__}
        })
        raise EmbeddingError(f"Embedder initialization failed: {str(e)}") from e

def _initialize_model(self):
    """
    Initialize the actual embedding model.
    
    This is a placeholder method - implement with your specific model.
    
    Returns:
        The initialized model
    """
    # Replace with actual model initialization
    # Example for sentence-transformers:
    # return SentenceTransformer(self._model_name, cache_folder=self._cache_dir)
    
    # Example for API-based models:
    # return APIClient(self._api_key, self._api_url)
    
    # Return a placeholder for now
    return "model_placeholder"
```

### 3. Implement the embed method

Implement the method to convert text to embeddings:

```python
async def embed(self, text: str) -> Tuple[List[float], Dict[str, Any]]:
    """
    Generate an embedding vector for the given text.
    
    Args:
        text: The text to embed
        
    Returns:
        Tuple[List[float], Dict[str, Any]]: The embedding vector and metadata
        
    Raises:
        EmbeddingError: If embedding generation fails
    """
    if not self._is_initialized:
        raise EmbeddingError("Embedder not initialized. Call initialize() first.")
    
    if not text or not isinstance(text, str):
        self.logger.warning({
            "action": "EMBEDDER_INVALID_INPUT",
            "message": "Invalid input text for embedding",
            "data": {"text_type": type(text).__name__}
        })
        # Return zero vector with appropriate dimensions
        return [0.0] * self._dimensions, {"error": "Invalid input text"}
    
    try:
        start_time = time.time()
        
        # Generate embedding
        # This is where you call your model to generate the embedding
        embedding = self._generate_embedding(text)
        
        elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Create metadata
        metadata = {
            "model": self._model_name,
            "dimensions": len(embedding),
            "elapsed_time_ms": elapsed_time,
            "text_length": len(text)
        }
        
        self.logger.debug({
            "action": "EMBEDDING_GENERATED",
            "message": "Generated embedding",
            "data": {
                "text_length": len(text),
                "elapsed_time_ms": elapsed_time
            }
        })
        
        return embedding, metadata
        
    except Exception as e:
        self.logger.error({
            "action": "EMBEDDING_ERROR",
            "message": f"Failed to generate embedding: {str(e)}",
            "data": {"error": str(e), "error_type": type(e).__name__}
        })
        raise EmbeddingError(f"Failed to generate embedding: {str(e)}") from e

def _generate_embedding(self, text: str) -> List[float]:
    """
    Generate the actual embedding using the model.
    
    This is a placeholder method - implement with your specific model.
    
    Args:
        text: The text to embed
        
    Returns:
        List[float]: The embedding vector
    """
    # Replace with actual embedding generation
    # Example for sentence-transformers:
    # return self._model.encode(text).tolist()
    
    # Example for API-based models:
    # response = self._model.embed(text)
    # return response["embedding"]
    
    # Return a placeholder random vector for demonstration
    import random
    return [random.random() for _ in range(self._dimensions)]
```

### 4. Implement batch embedding (optional)

For efficiency, you may want to implement a method for batch embedding:

```python
async def embed_batch(self, texts: List[str]) -> List[Tuple[List[float], Dict[str, Any]]]:
    """
    Generate embedding vectors for a batch of texts.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List[Tuple[List[float], Dict[str, Any]]]: List of embedding vectors and metadata
        
    Raises:
        EmbeddingError: If batch embedding generation fails
    """
    if not self._is_initialized:
        raise EmbeddingError("Embedder not initialized. Call initialize() first.")
    
    results = []
    
    try:
        start_time = time.time()
        
        # Generate embeddings in batch
        # This is where you call your model to generate the embeddings in batch
        batch_embeddings = self._generate_batch_embeddings(texts)
        
        elapsed_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        avg_time_per_item = elapsed_time / len(texts) if texts else 0
        
        # Create results with metadata
        for i, embedding in enumerate(batch_embeddings):
            text = texts[i]
            metadata = {
                "model": self._model_name,
                "dimensions": len(embedding),
                "batch_size": len(texts),
                "batch_index": i,
                "elapsed_time_ms": elapsed_time,
                "avg_time_per_item_ms": avg_time_per_item,
                "text_length": len(text)
            }
            results.append((embedding, metadata))
        
        self.logger.debug({
            "action": "BATCH_EMBEDDING_GENERATED",
            "message": f"Generated {len(texts)} embeddings in batch",
            "data": {
                "batch_size": len(texts),
                "elapsed_time_ms": elapsed_time,
                "avg_time_per_item_ms": avg_time_per_item
            }
        })
        
        return results
        
    except Exception as e:
        self.logger.error({
            "action": "BATCH_EMBEDDING_ERROR",
            "message": f"Failed to generate batch embeddings: {str(e)}",
            "data": {"error": str(e), "error_type": type(e).__name__}
        })
        raise EmbeddingError(f"Failed to generate batch embeddings: {str(e)}") from e

def _generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a batch of texts using the model.
    
    This is a placeholder method - implement with your specific model.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List[List[float]]: List of embedding vectors
    """
    # Replace with actual batch embedding generation
    # Example for sentence-transformers:
    # return self._model.encode(texts).tolist()
    
    # Example for API-based models:
    # response = self._model.embed_batch(texts)
    # return [item["embedding"] for item in response["embeddings"]]
    
    # Return placeholder random vectors for demonstration
    import random
    return [[random.random() for _ in range(self._dimensions)] for _ in texts]
```

## Configuration Setup

In your `config.yaml` file, add a section for your embedder:

```yaml
embedders:
  custom:
    model_name: "sentence-transformers/all-MiniLM-L6-v2"
    dimensions: 384
    cache_dir: "./cache/models"
    # Additional configuration options specific to your embedder
    batch_size: 32
    use_gpu: true
    normalize_embeddings: true
```

## Embedder Pipeline Integration

Your embedder will be used by the ingestion pipeline:

```python
# In DefaultIngestionPipeline._initialize_components:
custom_embedder = CustomEmbedder()
await custom_embedder.initialize()

# Set as pipeline embedder
self._embedder = custom_embedder
```

## Best Practices

1. **Model Selection**: Choose an appropriate embedding model for your domain. Different models have different strengths (e.g., multilingual support, domain-specific knowledge).

2. **Dimensionality**: Higher dimensions capture more information but take more space and computation time. Choose dimensions appropriate for your use case.

3. **Normalization**: Consider normalizing embeddings to unit length for consistent similarity calculations.

4. **Batching**: Implement efficient batch processing for better performance when embedding multiple texts.

5. **Caching**: Cache embeddings for frequently used texts to improve performance.

6. **GPU Acceleration**: Use GPU acceleration when available for significantly faster embedding generation.

7. **Text Truncation**: Handle long texts appropriately, either by truncating to model limits or by chunking and aggregating embeddings.

8. **Error Handling**: Gracefully handle empty or invalid inputs, as well as model errors.

9. **Versioning**: Track embedding model versions in metadata to handle model changes over time.

10. **Resource Management**: Close model resources when shutting down to prevent memory leaks.

## Example Embedder Implementations

Explore existing embedders for reference:
- `ici/adapters/embedders/sentence_transformer.py` - Uses sentence-transformers library
- OpenAI embeddings API integration (if available in the codebase)
