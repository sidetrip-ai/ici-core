"""
ChromaDB implementation of the VectorStore interface.

This module provides a concrete implementation of the VectorStore interface
using ChromaDB as the underlying vector database technology.
"""

import os
import uuid
import re
import math
import asyncio
from typing import List, Dict, Any, Optional, Set, Tuple

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
        
        # ChromaDB configuration with defaults
        self._persist_directory = "./db/vector/chroma_db"
        self._collection_name = "documents"
        self._embedding_function = None
        
        # BM25 index for keyword search
        self._enable_bm25 = True
        self._bm25_index = None
        self._bm25_indexing_in_progress = False  # Flag to track if indexing is in progress
        self._doc_id_map = {}  # Maps document IDs to ChromaDB IDs
        self._tokenizer_pattern = r'\b\w+\b'  # Default word tokenizer
        
        # BM25 parameters
        self._k1 = 1.5
        self._b = 0.75
    
    async def initialize(self) -> None:
        """
        Initialize the ChromaDB vector store with configuration parameters.
        
        Loads vector store configuration from config.yaml and creates the ChromaDB client
        
        Returns:
            None
            
        Raises:
            VectorStoreError: If initialization fails
        """
        try:
            self.logger.info({
                "action": "VECTOR_STORE_INIT_START",
                "message": "Initializing ChromaDB vector store"
            })
            
            # Load vector store configuration
            try:
                store_config = get_component_config("vector_stores.chroma", self._config_path)
                
                # Extract configuration with defaults
                if store_config:
                    self._persist_directory = store_config.get("persist_directory", self._persist_directory)
                    self._collection_name = store_config.get("collection_name", self._collection_name)
                    
                    # BM25 configuration
                    self._enable_bm25 = store_config.get("enable_bm25", self._enable_bm25)
                    self._k1 = float(store_config.get("bm25_k1", self._k1))
                    self._b = float(store_config.get("bm25_b", self._b))
                    self._tokenizer_pattern = store_config.get("tokenizer_pattern", self._tokenizer_pattern)
                    
                    self.logger.info({
                        "action": "VECTOR_STORE_CONFIG_LOADED",
                        "message": "Loaded vector store configuration",
                        "data": {
                            "persist_directory": self._persist_directory,
                            "collection_name": self._collection_name,
                            "enable_bm25": self._enable_bm25
                        }
                    })
                
            except Exception as e:
                # Use defaults if configuration loading fails
                self.logger.warning({
                    "action": "VECTOR_STORE_CONFIG_WARNING",
                    "message": f"Failed to load configuration: {str(e)}. Using defaults.",
                    "data": {"error": str(e)}
                })
            
            # Create directory if it doesn't exist
            if not os.path.exists(self._persist_directory):
                os.makedirs(self._persist_directory, exist_ok=True)
            
            # Initialize the ChromaDB client
            self._client = chromadb.PersistentClient(path=self._persist_directory)
            
            # Get or create collection
            try:
                self._collection = self._client.get_collection(name=self._collection_name)
                self.logger.info({
                    "action": "VECTOR_STORE_COLLECTION_EXISTS",
                    "message": f"Collection '{self._collection_name}' exists"
                })
                
                # Build BM25 index for existing documents if enabled
                if self._enable_bm25:
                    await self._build_bm25_index()
                
            except Exception:
                # Create new collection if it doesn't exist
                self._collection = self._client.create_collection(name=self._collection_name)
                self.logger.info({
                    "action": "VECTOR_STORE_COLLECTION_CREATED",
                    "message": f"Created new collection '{self._collection_name}'"
                })
            
            self._is_initialized = True
            
            self.logger.info({
                "action": "VECTOR_STORE_INIT_SUCCESS",
                "message": "ChromaDB vector store initialized successfully"
            })
            
        except Exception as e:
            self.logger.error({
                "action": "VECTOR_STORE_INIT_ERROR",
                "message": f"Failed to initialize vector store: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise VectorStoreError(f"Vector store initialization failed: {str(e)}") from e
            
    async def add_documents(
        self, 
        documents: List[Dict[str, Any]], 
        vectors: List[List[float]]
    ) -> List[str]:
        """
        Stores documents along with their vector embeddings.

        Args:
            documents: List of documents to store
            vectors: List of vector embeddings for the documents
            collection_name: Optional collection name (uses default if None)

        Returns:
            List[str]: List of document IDs

        Raises:
            VectorStoreError: If document storage fails
        """
        if not self._is_initialized:
            self.logger.error({
                "action": "VECTOR_STORE_NOT_INITIALIZED",
                "message": "Vector store not initialized before adding documents"
            })
            raise VectorStoreError("Vector store not initialized. Call initialize() first.")
        
        if not documents or not vectors:
            self.logger.warning({
                "action": "VECTOR_STORE_EMPTY_INPUT",
                "message": "No documents or vectors provided to add_documents",
                "data": {"documents_count": len(documents), "vectors_count": len(vectors)}
            })
            print("--------------------------------")
            print("No Documents or Vectors found")
            print("--------------------------------")
            return []
            
        if len(documents) != len(vectors):
            self.logger.error({
                "action": "VECTOR_STORE_MISMATCH",
                "message": "Document and vector counts don't match",
                "data": {"documents_count": len(documents), "vectors_count": len(vectors)}
            })
            raise VectorStoreError(
                f"Number of documents ({len(documents)}) must match number of vectors ({len(vectors)})"
            )
        
        try:
            self.logger.info({
                "action": "VECTOR_STORE_ADD_DOCUMENTS_START",
                "message": "Starting to add documents to vector store",
                "data": {"document_count": len(documents), "collection_name": self._collection_name}
            })
            
            # Use the specified collection or default
            collection = self._collection
            try:
                self.logger.info({
                    "action": "VECTOR_STORE_GET_COLLECTION",
                    "message": f"Attempting to get collection '{self._collection_name}'"
                })
                collection = self._client.get_collection(name=self._collection_name)
                self.logger.info({
                    "action": "VECTOR_STORE_COLLECTION_FOUND",
                    "message": f"Found existing collection '{self._collection_name}'"
                })
            except:
                self.logger.info({
                    "action": "VECTOR_STORE_CREATE_COLLECTION",
                    "message": f"Creating new collection '{self._collection_name}'"
                })
                collection = self._client.create_collection(name=self._collection_name)
                self.logger.info({
                    "action": "VECTOR_STORE_COLLECTION_CREATED",
                    "message": f"Created new collection '{self._collection_name}'"
                })
            
            # Prepare data for ChromaDB
            self.logger.info({
                "action": "VECTOR_STORE_PREPARE_DATA",
                "message": "Preparing document data for ChromaDB"
            })
            ids = [str(uuid.uuid4()) for _ in range(len(documents))]
            metadatas = []
            documents_text = []
            
            for doc in documents:
                # Extract text and metadata
                if "text" in doc:
                    documents_text.append(doc["text"])
                elif "content" in doc:
                    documents_text.append(doc["content"])
                else:
                    documents_text.append("")
                
                # Extract metadata
                metadata = doc.get("metadata", {})
                metadatas.append(metadata)
                
                # Add to BM25 index if enabled
                if self._enable_bm25:
                    doc_id = doc.get("id", str(uuid.uuid4()))
                    self._doc_id_map[doc_id] = ids[len(metadatas) - 1]
            
            # Store documents in ChromaDB
            self.logger.info({
                "action": "VECTOR_STORE_ADD_TO_CHROMA",
                "message": f"Adding {len(documents)} documents to ChromaDB collection",
                "data": {"collection_name": collection.name}
            })
            collection.add(
                ids=ids,
                embeddings=vectors,
                metadatas=metadatas,
                documents=documents_text
            )
            
            self.logger.info({
                "action": "VECTOR_STORE_DOCUMENTS_ADDED",
                "message": f"Added {len(documents)} documents to collection",
                "data": {"collection_name": collection.name, "count": len(documents)}
            })
            
            # Update BM25 index if enabled
            if self._enable_bm25:
                self.logger.info({
                    "action": "VECTOR_STORE_UPDATE_BM25",
                    "message": "Updating BM25 index with new documents"
                })
                await self._update_bm25_index(ids, documents_text)
                self.logger.info({
                    "action": "VECTOR_STORE_BM25_UPDATED",
                    "message": "BM25 index updated successfully"
                })
            
            return ids
            
        except Exception as e:
            self.logger.error({
                "action": "VECTOR_STORE_ADD_ERROR",
                "message": f"Failed to add documents: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise VectorStoreError(f"Failed to add documents: {str(e)}") from e
    
    async def search(
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
                        "score": results["distances"][0][i] if "distances" in results and results["distances"][0] else None,
                        "id": results["ids"][0][i] if results["ids"][0] else None
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
                "message": f"Failed to search: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise VectorStoreError(f"Failed to search: {str(e)}") from e

    def keyword_search(
        self,
        query: str,
        num_results: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform keyword-based search using BM25 algorithm.
        
        Args:
            query: The keyword query string
            num_results: Maximum number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of documents with BM25 scores
            
        Raises:
            VectorStoreError: If search fails or BM25 is not enabled
        """
        if not self._is_initialized:
            raise VectorStoreError("Vector store not initialized. Call initialize() first.")
            
        if not self._enable_bm25 or not self._bm25_index:
            self.logger.warning({
                "action": "VECTOR_STORE_BM25_NOT_ENABLED",
                "message": "BM25 search not enabled or index not built",
                "data": {
                    "enable_bm25": self._enable_bm25,
                    "bm25_index": self._bm25_index
                }
            })
            return []
            
        try:
            # Tokenize the query
            query_tokens = self._tokenize(query)
            
            # Calculate scores for each document
            doc_scores = {}
            
            # Get total number of documents
            N = len(self._bm25_index["doc_lengths"])
            
            # For each query term, calculate BM25 score contribution
            for token in query_tokens:
                if token not in self._bm25_index["term_doc_freq"]:
                    continue
                    
                # Get document frequency (number of docs containing this term)
                df = len(self._bm25_index["term_doc_freq"][token])
                
                # Calculate IDF (inverse document frequency)
                idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
                
                # For each document containing this term
                for doc_id, freq in self._bm25_index["term_doc_freq"][token].items():
                    # Get document length
                    doc_len = self._bm25_index["doc_lengths"].get(doc_id, 0)
                    if doc_len == 0:
                        continue
                        
                    # Calculate the BM25 score for this term in this document
                    numerator = freq * (self._k1 + 1)
                    denominator = freq + self._k1 * (1 - self._b + self._b * doc_len / self._bm25_index["avg_doc_length"])
                    score = idf * numerator / denominator
                    
                    # Add score to document's total
                    if doc_id in doc_scores:
                        doc_scores[doc_id] += score
                    else:
                        doc_scores[doc_id] = score
            
            # Sort documents by score
            sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Apply filters if specified
            if filters:
                # Get all document IDs that match the filters
                results = self._collection.get(where=filters)
                filter_ids = set(results["ids"])
                
                # Filter sorted docs
                sorted_docs = [(doc_id, score) for doc_id, score in sorted_docs if doc_id in filter_ids]
            
            # Limit to top results
            top_results = sorted_docs[:num_results]
            
            # Get document content for top results
            formatted_results = []
            for doc_id, score in top_results:
                try:
                    # Get document from ChromaDB
                    result = self._collection.get(ids=[doc_id])
                    
                    if result["documents"] and len(result["documents"]) > 0:
                        formatted_results.append({
                            "id": doc_id,
                            "text": result["documents"][0],
                            "metadata": result["metadatas"][0] if result["metadatas"] else {},
                            "score": score  # BM25 score
                        })
                except Exception as e:
                    self.logger.warning({
                        "action": "VECTOR_STORE_BM25_DOC_ERROR",
                        "message": f"Failed to get document {doc_id}: {str(e)}"
                    })
            
            self.logger.info({
                "action": "VECTOR_STORE_BM25_SEARCH",
                "message": f"BM25 search returned {len(formatted_results)} results",
                "data": {"query": query, "results": len(formatted_results)}
            })
            
            return formatted_results
            
        except Exception as e:
            self.logger.error({
                "action": "VECTOR_STORE_BM25_ERROR",
                "message": f"Failed to perform keyword search: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise VectorStoreError(f"Failed to perform keyword search: {str(e)}") from e
            
    async def _build_bm25_index(self) -> None:
        """
        Build a BM25 index from existing documents in the collection.
        
        Returns:
            None
        """
        try:
            self._bm25_indexing_in_progress = True
            self.logger.info({
                "action": "VECTOR_STORE_BM25_INDEX_START",
                "message": "Started building BM25 index"
            })
            
            # Initialize BM25 index
            self._bm25_index = {
                "term_doc_freq": {},  # Maps terms to {doc_id: frequency}
                "doc_lengths": {},    # Maps doc_id to document length (token count)
                "avg_doc_length": 0,  # Average document length
                "total_docs": 0       # Total number of documents
            }
            
            # Get all documents from collection
            all_docs = self._collection.get()
            
            if not all_docs["ids"]:
                self.logger.info({
                    "action": "VECTOR_STORE_BM25_INDEX_EMPTY",
                    "message": "No documents to index for BM25"
                })
                self._bm25_indexing_in_progress = False
                return
                
            # Process each document
            doc_ids = all_docs["ids"]
            doc_texts = all_docs["documents"]
            
            self.logger.info({
                "action": "VECTOR_STORE_BM25_INDEX_START",
                "message": f"Building BM25 index for {len(doc_ids)} documents"
            })
            
            # Index documents
            await self._update_bm25_index(doc_ids, doc_texts)
            
            self.logger.info({
                "action": "VECTOR_STORE_BM25_INDEX_COMPLETE",
                "message": "BM25 index built successfully",
                "data": {
                    "total_docs": self._bm25_index["total_docs"],
                    "avg_length": self._bm25_index["avg_doc_length"],
                    "unique_terms": len(self._bm25_index["term_doc_freq"])
                }
            })
            
        except Exception as e:
            self.logger.error({
                "action": "VECTOR_STORE_BM25_INDEX_ERROR",
                "message": f"Failed to build BM25 index: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
        finally:
            self._bm25_indexing_in_progress = False

    async def _update_bm25_index(self, doc_ids: List[str], doc_texts: List[str]) -> None:
        """
        Update the BM25 index with new documents.
        
        Args:
            doc_ids: List of document IDs
            doc_texts: List of document texts
            
        Returns:
            None
        """
        self._bm25_indexing_in_progress = True
        
        try:
            if not self._bm25_index:
                self._bm25_index = {
                    "term_doc_freq": {},
                    "doc_lengths": {},
                    "avg_doc_length": 0,
                    "total_docs": 0
                }
                
            # Calculate existing total token count
            total_tokens = self._bm25_index["avg_doc_length"] * self._bm25_index["total_docs"]
            
            # Process each document
            for i, (doc_id, doc_text) in enumerate(zip(doc_ids, doc_texts)):
                if not doc_text:
                    continue
                    
                # Tokenize document
                tokens = self._tokenize(doc_text)
                
                # Update document length
                doc_length = len(tokens)
                self._bm25_index["doc_lengths"][doc_id] = doc_length
                
                # Update total tokens
                total_tokens += doc_length
                
                # Calculate term frequencies
                term_freq = {}
                for token in tokens:
                    if token in term_freq:
                        term_freq[token] += 1
                    else:
                        term_freq[token] = 1
                
                # Update term-document frequency
                for token, freq in term_freq.items():
                    if token not in self._bm25_index["term_doc_freq"]:
                        self._bm25_index["term_doc_freq"][token] = {}
                    
                    self._bm25_index["term_doc_freq"][token][doc_id] = freq
            
            # Update total docs and average document length
            self._bm25_index["total_docs"] = len(self._bm25_index["doc_lengths"])
            
            if self._bm25_index["total_docs"] > 0:
                self._bm25_index["avg_doc_length"] = total_tokens / self._bm25_index["total_docs"]
            
            self.logger.info({
                "action": "VECTOR_STORE_BM25_INDEX_UPDATED",
                "message": f"BM25 index updated with {len(doc_ids)} documents",
                "data": {
                    "documents_added": len(doc_ids),
                    "total_docs": self._bm25_index["total_docs"],
                    "avg_length": self._bm25_index["avg_doc_length"]
                }
            })
        except Exception as e:
            self.logger.error({
                "action": "VECTOR_STORE_BM25_INDEX_UPDATE_ERROR",
                "message": f"Failed to update BM25 index: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
        finally:
            self._bm25_indexing_in_progress = False

    async def keyword_search_async(
        self,
        query: str,
        num_results: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        max_wait_time: int = 60  # Maximum time to wait for indexing (seconds)
    ) -> List[Dict[str, Any]]:
        """
        Async version of keyword search that waits for BM25 index to be built.
        
        Args:
            query: The keyword query string
            num_results: Maximum number of results to return
            filters: Optional metadata filters
            max_wait_time: Maximum time to wait for indexing (seconds)
            
        Returns:
            List of documents with BM25 scores
        """
        if not self._is_initialized:
            raise VectorStoreError("Vector store not initialized. Call initialize() first.")
            
        if not self._enable_bm25:
            self.logger.warning({
                "action": "VECTOR_STORE_BM25_NOT_ENABLED",
                "message": "BM25 search not enabled"
            })
            return []
            
        # Wait for indexing to complete if in progress
        wait_time = 0
        while self._bm25_indexing_in_progress and wait_time < max_wait_time:
            # Print a message to console about waiting
            sleep_interval = 1
            print(f"Waiting for BM25 index to be built... (sleeping for {sleep_interval} seconds)")
            await asyncio.sleep(sleep_interval)
            wait_time += sleep_interval
            
        # If we're still indexing after max wait time, return empty results
        if self._bm25_indexing_in_progress:
            self.logger.warning({
                "action": "VECTOR_STORE_BM25_WAIT_TIMEOUT",
                "message": f"Exceeded maximum wait time ({max_wait_time}s) for BM25 indexing to complete"
            })
            return []
            
        # If no index after waiting, return empty results
        if not self._bm25_index:
            self.logger.warning({
                "action": "VECTOR_STORE_BM25_NO_INDEX",
                "message": "BM25 index not built"
            })
            return []
            
        # Use the existing keyword_search implementation
        return self.keyword_search(query, num_results, filters)
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text for BM25 indexing.
        
        Args:
            text: The text to tokenize
            
        Returns:
            List[str]: List of tokens
        """
        if not text:
            return []
            
        # Lowercase the text
        text = text.lower()
        
        # Extract tokens based on the tokenizer pattern
        tokens = re.findall(self._tokenizer_pattern, text)
        
        return tokens
    
    async def delete(
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
            initial_count = await self.count()
            
            # Delete by ID if provided
            if document_ids:
                self._collection.delete(ids=document_ids)
                
            # Delete by filter if provided
            elif filters:
                self._collection.delete(where=filters)
            
            # Calculate number of deleted documents
            final_count = await self.count()
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
    
    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
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
    async def store_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        This method is deprecated and should not be used.
        
        Raises:
            NotImplementedError: Always raises this exception
        """
        raise NotImplementedError(
            "store_documents is deprecated. Use add_documents method instead."
        ) 