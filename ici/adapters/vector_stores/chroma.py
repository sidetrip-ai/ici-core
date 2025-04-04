"""
ChromaDB implementation of the VectorStore interface.

This module provides a concrete implementation of the VectorStore interface
using ChromaDB as the underlying vector database technology.
"""

import os
import uuid
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings

from ici.adapters.loggers import StructuredLogger
from ici.core.interfaces.vector_store import VectorStore
from ici.core.exceptions import VectorStoreError, ConfigurationError
from ici.utils.config import get_component_config


class ChromaDBStore(VectorStore):
    """
    ChromaDB implementation of the VectorStore interface.
    
    This implementation supports both in-memory and persistent storage.
    It does not use ChromaDB's embedding capabilities, instead relying
    on pre-computed embeddings.
    """
    
    def __init__(self, logger_name: str = "vector_store.chroma"):
        """
        Initialize the ChromaDB vector store.
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = StructuredLogger(name=logger_name)
        self._client = None
        self._collection = None
        self._is_initialized = False
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
    
    async def initialize(self) -> None:
        """
        Initialize the vector store with configuration parameters.
        
        This method loads configuration from the config.yaml file and sets up
        the ChromaDB client and collection.
        
        Returns:
            None
            
        Raises:
            VectorStoreError: If initialization fails
        """
        try:
            self.logger.info({
                "action": "VECTOR_STORE_INIT_START",
                "message": "Initializing ChromaDB vector store",
                "data": {"config_path": self._config_path}
            })
            
            # Load vector store configuration from new path
            vector_store_config = get_component_config("vector_stores.chroma", self._config_path)
            
            # Validate configuration
            if vector_store_config.get("type", "").lower() != "chroma":
                self.logger.warning({
                    "action": "VECTOR_STORE_CONFIG_WARNING",
                    "message": "Vector store type not specified as 'chroma'",
                    "data": {"configured_type": vector_store_config.get("type")}
                })
            
            # Extract parameters with defaults
            collection_name = vector_store_config.get("collection_name", "default_collection")
            persist_directory = vector_store_config.get("persist_directory")

            self.logger.info({
                "action": "VECTOR_STORE_CONFIG_VALIDATED",
                "message": "Vector store configuration validated",
                "data": {"collection_name": collection_name, "persist_directory": persist_directory}
            })
            
            # Initialize ChromaDB client (persistent or in-memory)
            if persist_directory:
                # Ensure directory exists
                os.makedirs(persist_directory, exist_ok=True)
                self._client = chromadb.PersistentClient(path=persist_directory)
                self.logger.info({
                    "action": "VECTOR_STORE_CLIENT_INIT",
                    "message": "Initialized persistent ChromaDB client",
                    "data": {"persist_directory": persist_directory}
                })
            else:
                self._client = chromadb.Client()
                self.logger.info({
                    "action": "VECTOR_STORE_CLIENT_INIT",
                    "message": "Initialized in-memory ChromaDB client"
                })
            
            # Create or get collection (without embedding function)
            self._collection = self._client.get_or_create_collection(
                name=collection_name
            )
            
            self._is_initialized = True
            
            self.logger.info({
                "action": "VECTOR_STORE_INIT_SUCCESS",
                "message": f"ChromaDB vector store initialized with collection '{collection_name}'",
                "data": {
                    "collection": collection_name,
                    "persistent": persist_directory is not None
                }
            })
            
        except ConfigurationError as e:
            self.logger.error({
                "action": "VECTOR_STORE_CONFIG_ERROR",
                "message": f"Configuration error: {str(e)}",
                "data": {"error": str(e)}
            })
            raise VectorStoreError(f"Vector store configuration error: {str(e)}") from e
        except Exception as e:
            self.logger.error({
                "action": "VECTOR_STORE_INIT_ERROR",
                "message": f"Failed to initialize ChromaDB vector store: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise VectorStoreError(f"Vector store initialization failed: {str(e)}") from e
    
    def add_documents(
        self, documents: List[Dict[str, Any]], vectors: List[List[float]]
    ) -> List[str]:
        """
        Store documents with their vector embeddings.
        
        Args:
            documents: List of documents, each containing 'text' and optional 'metadata'
            vectors: List of vector embeddings for the documents
            
        Returns:
            List[str]: List of document IDs
            
        Raises:
            VectorStoreError: If document storage fails
        """
        if not self._is_initialized:
            raise VectorStoreError("Vector store not initialized. Call initialize() first.")
        
        if len(documents) != len(vectors):
            raise VectorStoreError(
                f"Number of documents ({len(documents)}) does not match number of vectors ({len(vectors)})"
            )
        
        try:
            # Extract document texts and metadata
            texts = []
            metadatas = []
            
            for doc in documents:
                texts.append(doc.get("text", ""))
                metadatas.append(doc.get("metadata", {}))
            
            # Generate IDs if not already present
            ids = [str(uuid.uuid4()) for _ in range(len(documents))]

            self.logger.info({
                "action": "VECTOR_STORE_ADD",
                "message": f"Adding {len(documents)} documents to vector store",
                "data": {"ids": ids, "documents": texts, "vectors": vectors, "this_is_metadata": metadatas}
            })
            
            # Add to collection
            self._collection.add(
                embeddings=vectors,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            # self.logger.info({
            #     "action": "VECTOR_STORE_ADD",
            #     "message": f"Added {len(documents)} documents to vector store",
            #     "data": {"count": len(documents), "collection_count": self._client.count_collections(), "get_settings": self._client.get_settings() }
            # })
            
            return ids
            
        except Exception as e:
            self.logger.error({
                "action": "VECTOR_STORE_ADD_ERROR",
                "message": f"Failed to add documents: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise VectorStoreError(f"Document storage failed: {str(e)}") from e
    
    def search(
        self,
        query_vector: List[float],
        num_results: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the most similar documents based on the query vector.
        
        Args:
            query_vector: Vector embedding of the query
            num_results: Maximum number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of documents with similarity scores
            
        Raises:
            VectorStoreError: If search fails
        """
        if not self._is_initialized:
            raise VectorStoreError("Vector store not initialized. Call initialize() first.")
        
        try:
            # Query the collection using the query vector
            results = self._collection.query(
                query_embeddings=[query_vector],
                n_results=num_results,
                where=filters
            )
            
            # Format the results according to the interface
            formatted_results = []
            
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    formatted_results.append({
                        "text": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"][0] else {},
                        "score": results["distances"][0][i] if "distances" in results and results["distances"][0] else None
                    })
            
            self.logger.info({
                "action": "VECTOR_STORE_SEARCH",
                "message": f"Search returned {len(formatted_results)} results",
                "data": {"query_results": len(formatted_results), "num_requested": num_results}
            })
            
            return formatted_results
            
        except Exception as e:
            self.logger.error({
                "action": "VECTOR_STORE_SEARCH_ERROR",
                "message": f"Search failed: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise VectorStoreError(f"Search operation failed: {str(e)}") from e
    
    def delete(
        self,
        document_ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Delete documents from the vector store by ID or filter.
        
        Args:
            document_ids: List of document IDs to delete
            filters: Metadata filters to select documents for deletion
            
        Returns:
            Number of documents deleted
            
        Raises:
            VectorStoreError: If deletion fails
        """
        if not self._is_initialized:
            raise VectorStoreError("Vector store not initialized. Call initialize() first.")
        
        if not document_ids and not filters:
            raise VectorStoreError("Either document_ids or filters must be provided")
        
        try:
            # Record the initial count to determine how many were deleted
            initial_count = self.count()
            
            # Delete by ID if provided
            if document_ids:
                self._collection.delete(ids=document_ids)
                
            # Delete by filter if provided
            elif filters:
                self._collection.delete(where=filters)
            
            # Calculate number of deleted documents
            final_count = self.count()
            deleted_count = initial_count - final_count
            
            self.logger.info({
                "action": "VECTOR_STORE_DELETE",
                "message": f"Deleted {deleted_count} documents from vector store",
                "data": {
                    "deleted_count": deleted_count,
                    "by_ids": document_ids is not None,
                    "by_filters": filters is not None
                }
            })
            
            return deleted_count
            
        except Exception as e:
            self.logger.error({
                "action": "VECTOR_STORE_DELETE_ERROR",
                "message": f"Document deletion failed: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise VectorStoreError(f"Delete operation failed: {str(e)}") from e
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count documents in the vector store, optionally filtered by metadata.
        
        Args:
            filters: Optional metadata filters
            
        Returns:
            Number of documents matching the filter
            
        Raises:
            VectorStoreError: If count operation fails
        """
        if not self._is_initialized:
            raise VectorStoreError("Vector store not initialized. Call initialize() first.")
        
        try:
            if filters:
                # For filtered count, we need to get all IDs that match the filter
                result = self._collection.get(where=filters)
                count = len(result["ids"]) if result["ids"] else 0
            else:
                # Get all document IDs (unfiltered count)
                result = self._collection.get()
                count = len(result["ids"]) if result["ids"] else 0
            
            self.logger.debug({
                "action": "VECTOR_STORE_COUNT",
                "message": f"Counted {count} documents in vector store",
                "data": {"count": count, "with_filters": filters is not None}
            })
            
            return count
            
        except Exception as e:
            self.logger.error({
                "action": "VECTOR_STORE_COUNT_ERROR",
                "message": f"Count operation failed: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise VectorStoreError(f"Count operation failed: {str(e)}") from e
    
    def healthcheck(self) -> Dict[str, Any]:
        """
        Check if the vector store is properly configured and functioning.
        
        Returns:
            Dictionary with health status information
            
        Raises:
            VectorStoreError: If health check fails
        """
        health_result = {
            "healthy": False,
            "message": "Vector store health check failed",
            "details": {}
        }
        
        try:
            # Check if initialized
            if not self._is_initialized:
                health_result["message"] = "Vector store not initialized"
                return health_result
            
            # Check if client and collection are available
            if not self._client or not self._collection:
                health_result["message"] = "ChromaDB client or collection not available"
                return health_result
            
            # Try a simple operation to verify functionality
            collection_name = self._collection.name
            count = self.count()
            
            # Check if persistent (safely)
            is_persistent = False
            try:
                from chromadb.api.client import PersistentClient
                is_persistent = isinstance(self._client, PersistentClient)
            except (ImportError, TypeError):
                # Handle case where chromadb import fails or PersistentClient isn't available
                is_persistent = hasattr(self._client, 'persist_directory')
            
            # Update health status
            health_result["healthy"] = True
            health_result["message"] = "Vector store is healthy"
            health_result["details"] = {
                "collection": collection_name,
                "document_count": count,
                "persistent": is_persistent
            }
            
            self.logger.info({
                "action": "VECTOR_STORE_HEALTH_CHECK",
                "message": "Vector store health check successful",
                "data": health_result
            })
            
        except Exception as e:
            health_result["message"] = f"Health check failed: {str(e)}"
            health_result["details"] = {
                "error": str(e),
                "error_type": type(e).__name__
            }
            
            self.logger.error({
                "action": "VECTOR_STORE_HEALTH_CHECK_ERROR",
                "message": f"Health check failed: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
        
        return health_result
    
    # This method is intentionally not implemented as it's being deprecated
    def store_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        This method is deprecated and should not be used.
        
        Raises:
            NotImplementedError: Always raises this exception
        """
        raise NotImplementedError(
            "store_documents is deprecated. Use add_documents method instead."
        ) 