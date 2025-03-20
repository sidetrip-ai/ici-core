"""
Intelligent Consciousness Interface (ICI)

A modular framework for creating a personal AI assistant that is context-aware,
style-aware, personality-aware, and security-aware. The system processes data 
through an Ingestion Pipeline and responds to queries via a Query Pipeline,
leveraging vector databases for efficient retrieval.
"""

__version__ = "0.1.0"

# Import core interfaces and exceptions
from ici.core import (
    # Interfaces
    Ingestor,
    Preprocessor,
    Embedder,
    VectorStore,
    Validator,
    PromptBuilder,
    Generator,
    Orchestrator,
    IngestionPipeline,
    Logger,
    # Exceptions
    ICIError,
    IngestionError,
    IngestorError,
    APIAuthenticationError,
    APIRateLimitError,
    DataFetchError,
    PreprocessorError,
    IngestionPipelineError,
    QueryError,
    ValidationError,
    EmbeddingError,
    VectorStoreError,
    PromptBuilderError,
    GenerationError,
    OrchestratorError,
    ConfigurationError,
    LoggerError,
)

# Import utilities
from ici.utils import (
    load_config,
    get_component_config,
)

# Export core interfaces and exceptions
__all__ = [
    # Interfaces
    "Ingestor",
    "Preprocessor",
    "Embedder",
    "VectorStore",
    "Validator",
    "PromptBuilder",
    "Generator",
    "Orchestrator",
    "IngestionPipeline",
    "Logger",
    # Exceptions
    "ICIError",
    "IngestionError",
    "IngestorError",
    "APIAuthenticationError",
    "APIRateLimitError",
    "DataFetchError",
    "PreprocessorError",
    "IngestionPipelineError",
    "QueryError",
    "ValidationError",
    "EmbeddingError",
    "VectorStoreError",
    "PromptBuilderError",
    "GenerationError",
    "OrchestratorError",
    "ConfigurationError",
    "LoggerError",
    # Utilities
    "load_config",
    "get_component_config",
]
