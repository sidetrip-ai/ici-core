"""
Core module for the Intelligent Consciousness Interface (ICI).

This module contains the core interfaces and exceptions that define the
architecture of the ICI framework, establishing the contract that all
implementations must follow.
"""

# Import all interfaces
from ici.core.interfaces import (
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
)

# Import all exceptions
from ici.core.exceptions import (
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

# Export all interfaces and exceptions
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
]
