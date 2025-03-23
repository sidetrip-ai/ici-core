"""
Adapters module for the ICI framework.

This module contains concrete implementations of the interfaces defined in the core module.
"""

# Import logger implementations
from ici.adapters.loggers import StructuredLogger

# Import embedder implementations
from ici.adapters.embedders import SentenceTransformerEmbedder

# Import preprocessor implementations
from ici.adapters.preprocessors import TelegramPreprocessor

# Export all implementations
__all__ = [
    # Logger implementations
    "StructuredLogger",
    
    # Embedder implementations
    "SentenceTransformerEmbedder",
    
    # Preprocessor implementations
    "TelegramPreprocessor",
]
