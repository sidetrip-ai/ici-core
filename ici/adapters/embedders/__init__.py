"""
Embedder implementations for the ICI Framework.

This module contains adapter implementations for the Embedder interface,
providing embedding functionality for text data.
"""

# Import adapters
from .sentence_transformer import SentenceTransformerEmbedder 

__all__ = ["SentenceTransformerEmbedder"]