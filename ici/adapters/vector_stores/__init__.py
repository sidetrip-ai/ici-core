"""
Vector Store implementations for the ICI framework.

This package contains implementations of the VectorStore interface
for different vector database technologies.

Available implementations:
- ChromaDBStore: Vector store implementation using ChromaDB
"""

from ici.adapters.vector_stores.chroma import ChromaDBStore

__all__ = ["ChromaDBStore"] 