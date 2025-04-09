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

# Import chat history implementations
from ici.adapters.chat import JSONChatHistoryManager

# Import user ID generator implementations
from ici.adapters.user_id import DefaultUserIDGenerator

# Import orchestrator implementations
from ici.adapters.orchestrators import DefaultOrchestrator

# Export all implementations
__all__ = [
    # Logger implementations
    "StructuredLogger",
    
    # Embedder implementations
    "SentenceTransformerEmbedder",
    
    # Preprocessor implementations
    "TelegramPreprocessor",
    
    # Chat history implementations
    "JSONChatHistoryManager",
    
    # User ID generator implementations
    "DefaultUserIDGenerator",
    
    # Orchestrator implementations
    "DefaultOrchestrator",
]
