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
import time
import json
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional, Set, Tuple

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings

from ici.adapters.loggers import StructuredLogger
from ici.core.interfaces.vector_store import VectorStore
from ici.core.exceptions import VectorStoreError, ConfigurationError
from ici.utils.config import get_component_config, load_config


class IndexingState(Enum):
    """Represents the state of the BM25 index operations."""
    IDLE = "idle"
    BUILDING = "building"
    UPDATING = "updating"
    SAVING = "saving"
    LOADING = "loading"


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
        self._doc_id_map = {}  # Maps document IDs to ChromaDB IDs
        self._tokenizer_pattern = r'\b\w+\b'  # Default word tokenizer
        self._bm25_lock = asyncio.Lock()  # Lock for BM25 index operations
        self._bm25_indexing_state = IndexingState.IDLE # Track BM25 state
        
        # BM25 parameters
        self._k1 = 1.5
        self._b = 0.75
        
        # Source to collection name mapping
        self._source_collection_map = {}
    
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
                
                # Load pipeline configurations to get collection mappings
                try:
                    # Load full config to access pipeline configurations
                    full_config = load_config(self._config_path)
                    
                    # Initialize source to collection mapping
                    if "pipelines" in full_config:
                        pipelines_config = full_config["pipelines"]
                        
                        # Process each pipeline configuration
                        for source, pipeline_config in pipelines_config.items():
                            if isinstance(pipeline_config, dict) and "vector_store" in pipeline_config:
                                vs_config = pipeline_config["vector_store"]
                                if "collection_name" in vs_config:
                                    self._source_collection_map[source] = vs_config["collection_name"]
                                    self.logger.info({
                                        "action": "VECTOR_STORE_COLLECTION_MAPPING",
                                        "message": f"Mapped source '{source}' to collection '{vs_config['collection_name']}'",
                                        "data": {"source": source, "collection": vs_config["collection_name"]}
                                    })
                    
                    self.logger.info({
                        "action": "VECTOR_STORE_COLLECTION_MAPPINGS_LOADED",
                        "message": f"Loaded {len(self._source_collection_map)} source-to-collection mappings",
                        "data": {"mappings": self._source_collection_map}
                    })
                    
                except Exception as e:
                    self.logger.warning({
                        "action": "VECTOR_STORE_COLLECTION_MAPPINGS_WARNING",
                        "message": f"Failed to load collection mappings: {str(e)}. Using defaults.",
                        "data": {"error": str(e)}
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

            # Mark as initialized *after* client is created
            self._is_initialized = True
            
            # Get or create collection
            try:
                self._collection = self._client.get_collection(name=self._collection_name)
                self.logger.info({
                    "action": "VECTOR_STORE_COLLECTION_EXISTS",
                    "message": f"Collection '{self._collection_name}' exists"
                })

            except Exception:
                # Create new collection if it doesn't exist
                self._collection = self._create_collection(name=self._collection_name)
                self.logger.info({
                    "action": "VECTOR_STORE_COLLECTION_CREATED",
                    "message": f"Created new collection '{self._collection_name}'"
                })
                
            # BM25 index initialization
            if self._enable_bm25:
                # Try to load saved BM25 index first
                loaded = await self.load_bm25_index()
                
                # If loading failed or index doesn't exist, build it
                if not loaded:
                    self.logger.info({
                        "action": "VECTOR_STORE_BM25_INDEX_BUILDING",
                        "message": "No valid saved BM25 index found, building from scratch."
                    })
                    built = await self._build_bm25_index()
                    if built:
                        await self.save_bm25_index()
            
            # Initialize all mapped collections
            for source, collection_name in self._source_collection_map.items():
                try:
                    self._client.get_collection(name=collection_name)
                    self.logger.info({
                        "action": "VECTOR_STORE_MAPPED_COLLECTION_EXISTS",
                        "message": f"Mapped collection '{collection_name}' for source '{source}' exists"
                    })
                except Exception:
                    self._create_collection(name=collection_name)
                    self.logger.info({
                        "action": "VECTOR_STORE_MAPPED_COLLECTION_CREATED",
                        "message": f"Created mapped collection '{collection_name}' for source '{source}'"
                    })
              
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
            
    def _create_collection(self, name: str, **kwargs) -> Collection:
        """Standard method for creating collections with consistent parameters"""
        return self._client.create_collection(
            name=name,
            metadata={
                "hnsw:space": "cosine",
                "hnsw:search_ef": 150,
                "hnsw:construction_ef": 150
            },
            **kwargs
        )
            
    async def _store_documents_internal(
        self,
        documents: List[Dict[str, Any]],
        vectors: Optional[List[List[float]]] = None,
        collection_name: Optional[str] = None,
        return_ids: bool = False
    ) -> Optional[List[str]]:
        """
        Internal method for storing documents in the vector store.
        
        Args:
            documents: List of documents to store
            vectors: Optional list of vector embeddings (if None, vectors must be in documents)
            collection_name: Optional name of collection to store in
            return_ids: Whether to return document IDs
            
        Returns:
            List of document IDs if return_ids is True, otherwise None
            
        Raises:
            VectorStoreError: If storage fails
        """
        if not self._is_initialized:
            self.logger.error({
                "action": "VECTOR_STORE_NOT_INITIALIZED",
                "message": "Vector store not initialized before storing documents"
            })
            raise VectorStoreError("Vector store not initialized. Call initialize() first.")
        
        if not documents:
            self.logger.warning({
                "action": "VECTOR_STORE_EMPTY_INPUT",
                "message": "No documents provided to store"
            })
            return [] if return_ids else None
        
        try:
            # Use provided collection name or default
            target_collection_name = collection_name or self._collection_name
            
            # Prepare data for ChromaDB
            ids = []
            metadatas = []
            documents_text = []
            embeddings = []
            
            # Process documents based on input format
            if vectors is not None:
                # Handle separate documents and vectors (add_documents format)
                if len(documents) != len(vectors):
                    self.logger.error({
                        "action": "VECTOR_STORE_MISMATCH",
                        "message": "Document and vector counts don't match",
                        "data": {"documents_count": len(documents), "vectors_count": len(vectors)}
                    })
                    raise VectorStoreError(
                        f"Number of documents ({len(documents)}) must match number of vectors ({len(vectors)})"
                    )
                
                embeddings = vectors
                
                for doc in documents:
                    # Generate ID if not provided
                    doc_id = doc.get("id", str(uuid.uuid4()))
                    ids.append(doc_id)
                    
                    # Extract text
                    if "text" in doc:
                        documents_text.append(doc["text"])
                    elif "content" in doc:
                        documents_text.append(doc["content"])
                    else:
                        documents_text.append("")
                    
                    # Extract metadata
                    metadata = doc.get("metadata", {})
                    metadatas.append(metadata)
            else:
                # Handle documents with embedded vectors (store_documents format)
                for doc in documents:
                    if "vector" not in doc:
                        self.logger.error({
                            "action": "VECTOR_STORE_MISSING_VECTOR",
                            "message": "Document missing vector field"
                        })
                        raise VectorStoreError("Document missing vector field")
                    
                    embeddings.append(doc["vector"])
                    
                    # Generate ID if not provided
                    doc_id = doc.get("id", str(uuid.uuid4()))
                    ids.append(doc_id)
                    
                    # Extract text
                    if "text" in doc:
                        documents_text.append(doc["text"])
                    elif "content" in doc:
                        documents_text.append(doc["content"])
                    else:
                        documents_text.append("")
                    
                    # Extract metadata
                    metadata = doc.get("metadata", {})
                    metadatas.append(metadata)
            
            self.logger.info({
                "action": "VECTOR_STORE_PREPARE_DATA",
                "message": "Preparing document data for ChromaDB",
                "data": {"document_count": len(documents), "collection_name": target_collection_name}
            })
            
            # Get or create the specified collection
            try:
                collection = self._client.get_collection(name=target_collection_name)
                self.logger.info({
                    "action": "VECTOR_STORE_COLLECTION_FOUND",
                    "message": f"Found existing collection '{target_collection_name}'"
                })
            except:
                collection = self._create_collection(name=target_collection_name)
                self.logger.info({
                    "action": "VECTOR_STORE_COLLECTION_CREATED",
                    "message": f"Created new collection '{target_collection_name}'"
                })
            
            # Add to BM25 doc_id_map if enabled and this is the default collection
            if self._enable_bm25 and target_collection_name == self._collection_name:
                async with self._bm25_lock:
                    for i, doc_id in enumerate(ids):
                        # Map the unique ID to the ChromaDB ID (might be the same)
                        self._doc_id_map[doc_id] = ids[i]
            
            # Store documents in ChromaDB (use upsert to handle updates)
            self.logger.info({
                "action": "VECTOR_STORE_UPSERT_TO_CHROMA",
                "message": f"Upserting {len(documents)} documents to ChromaDB collection",
                "data": {"collection_name": collection.name}
            })
            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents_text
            )
            
            self.logger.info({
                "action": "VECTOR_STORE_DOCUMENTS_UPSERTED",
                "message": f"Upserted {len(documents)} documents to collection",
                "data": {"collection_name": collection.name, "count": len(documents)}
            })
            
            # Update BM25 index if enabled and this is the default collection
            if self._enable_bm25 and target_collection_name == self._collection_name:
                updated = await self._update_bm25_index(ids, documents_text)
                if updated:
                    await self.save_bm25_index() # Save after successful update
            
            return ids if return_ids else None
            
        except Exception as e:
            self.logger.error({
                "action": "VECTOR_STORE_DOCUMENT_STORAGE_ERROR",
                "message": f"Failed to store documents: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise VectorStoreError(f"Failed to store documents: {str(e)}") from e
            
    async def add_documents(
        self, 
        documents: List[Dict[str, Any]], 
        vectors: List[List[float]],
        collection_name: Optional[str] = None
    ) -> List[str]:
        """
        Stores documents along with their vector embeddings.

        Args:
            documents: List of documents to store
            vectors: List of vector embeddings for the documents
            collection_name: Optional name of the collection to store documents in.
                             If None, the default collection will be used.

        Returns:
            List[str]: List of document IDs

        Raises:
            VectorStoreError: If document storage fails
        """
        if not documents or not vectors:
            self.logger.warning({
                "action": "VECTOR_STORE_EMPTY_INPUT",
                "message": "No documents or vectors provided to add_documents",
                "data": {"documents_count": len(documents) if documents else 0, "vectors_count": len(vectors) if vectors else 0}
            })
            return []
            
        # Use the internal method with return_ids=True
        return await self._store_documents_internal(
            documents=documents,
            vectors=vectors,
            collection_name=collection_name,
            return_ids=True
        ) or []
            
    async def store_documents(self, documents: List[Dict[str, Any]], collection_name: Optional[str] = None) -> None:
        """
        Store documents with their vectors, text, and metadata.
        
        Args:
            documents: List of documents to store
            collection_name: Optional name of the collection to store documents in.
                             If None, the default collection will be used.
            
        Raises:
            VectorStoreError: If storage fails
        """
        if not documents:
            self.logger.warning({
                "action": "VECTOR_STORE_EMPTY_INPUT",
                "message": "No documents provided to store_documents"
            })
            return
        
        # Use the internal method with return_ids=False
        await self._store_documents_internal(
            documents=documents,
            vectors=None,  # Vectors are in the documents
            collection_name=collection_name,
            return_ids=False
        )
    
    async def search(
        self,
        query_vector: List[float],
        num_results: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the most similar documents based on the query vector.
        
        Args:
            query_vector: Vector embedding of the query
            num_results: Maximum number of results to return
            filters: Optional metadata filters
            collection_name: Optional name of the collection to search in.
                             If None, the default collection will be used.
            
        Returns:
            List of documents with similarity scores
            
        Raises:
            VectorStoreError: If search fails
        """
        if not self._is_initialized:
            raise VectorStoreError("Vector store not initialized. Call initialize() first.")
        
        try:
            # Use provided collection name or default
            target_collection_name = collection_name or self._collection_name
            
            # Get the specified collection
            try:
                collection = self._client.get_collection(name=target_collection_name)
                self.logger.info({
                    "action": "VECTOR_STORE_COLLECTION_FOUND",
                    "message": f"Found collection '{target_collection_name}' for search"
                })
            except Exception as e:
                self.logger.warning({
                    "action": "VECTOR_STORE_COLLECTION_NOT_FOUND",
                    "message": f"Collection '{target_collection_name}' not found for search",
                    "data": {"error": str(e)}
                })
                return []
            
            # Query the collection using the query vector
            results = collection.query(
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
                "data": {
                    "query_results": len(formatted_results), 
                    "num_requested": num_results,
                    "collection_name": target_collection_name
                }
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
        collection_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform keyword-based search using BM25 algorithm.
        
        Args:
            query: The keyword query string
            num_results: Maximum number of results to return
            filters: Optional metadata filters
            collection_name: Optional name of the collection to search in.
                             If None, the default collection will be used.
            
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
            
        # Note: Currently BM25 search only works with the default collection
        # If a different collection is specified, log a warning
        if collection_name and collection_name != self._collection_name:
            self.logger.warning({
                "action": "VECTOR_STORE_BM25_COLLECTION_WARNING",
                "message": f"BM25 search only works with default collection '{self._collection_name}', ignoring specified collection '{collection_name}'",
                "data": {"specified_collection": collection_name, "default_collection": self._collection_name}
            })
            
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
            
            # Apply filters if provided
            filtered_docs = []
            
            # Convert to standard format
            results = []
            
            # Get the collection to retrieve document content
            collection = self._client.get_collection(name=self._collection_name)
            
            # Add top results
            count = 0
            for doc_id, score in sorted_docs:
                if count >= num_results:
                    break
                    
                # Look up the ChromaDB ID for this document
                chroma_id = self._doc_id_map.get(doc_id, doc_id)
                
                # Get the document from ChromaDB
                try:
                    doc_data = collection.get(ids=[chroma_id])
                    
                    if not doc_data["documents"] or not doc_data["documents"][0]:
                        continue
                        
                    text = doc_data["documents"][0]
                    metadata = doc_data["metadatas"][0] if "metadatas" in doc_data and doc_data["metadatas"] else {}
                    
                    # Apply filters if provided
                    if filters:
                        # Simple filtering implementation
                        match = True
                        for key, value in filters.items():
                            if key not in metadata or metadata[key] != value:
                                match = False
                                break
                                
                        if not match:
                            continue
                    
                    # Add to results
                    results.append({
                        "text": text,
                        "metadata": metadata,
                        "score": score,
                        "id": doc_id
                    })
                    
                    count += 1
                    
                except Exception as e:
                    self.logger.warning({
                        "action": "VECTOR_STORE_BM25_DOC_RETRIEVAL_ERROR",
                        "message": f"Failed to retrieve document {doc_id}: {str(e)}",
                        "data": {"doc_id": doc_id, "error": str(e)}
                    })
                    continue
            
            self.logger.info({
                "action": "VECTOR_STORE_BM25_SEARCH",
                "message": f"BM25 search returned {len(results)} results",
                "data": {
                    "query": query,
                    "results_count": len(results)
                }
            })
            
            return results
            
        except Exception as e:
            self.logger.error({
                "action": "VECTOR_STORE_BM25_ERROR",
                "message": f"Failed to perform keyword search: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise VectorStoreError(f"Failed to perform keyword search: {str(e)}") from e
            
    async def keyword_search_async(
        self,
        query: str,
        num_results: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        collection_name: Optional[str] = None,
        max_wait_time: int = 60  # Maximum time to wait for indexing (seconds)
    ) -> List[Dict[str, Any]]:
        """
        Perform keyword-based search asynchronously, waiting for indexing to complete.
        
        This method will wait if BM25 indexing is in progress, up to the max_wait_time limit.
        
        Args:
            query: The keyword query string
            num_results: Maximum number of results to return
            filters: Optional metadata filters
            collection_name: Optional name of the collection to search in.
                             If None, the default collection will be used.
            max_wait_time: Maximum time to wait for indexing to complete (seconds)
            
        Returns:
            List of documents with BM25 scores
            
        Raises:
            VectorStoreError: If search fails or times out
        """
        if not self._is_initialized:
            raise VectorStoreError("Vector store not initialized. Call initialize() first.")
            
        if not self._enable_bm25:
            self.logger.warning({
                "action": "VECTOR_STORE_BM25_NOT_ENABLED",
                "message": "BM25 search not enabled"
            })
            return []
            
        # Wait for indexing to be IDLE
        start_time = time.time()
        while True:
            async with self._bm25_lock:
                if self._bm25_indexing_state == IndexingState.IDLE:
                    break # Index is ready for searching
            
            # Check if we've exceeded the wait time
            if time.time() - start_time > max_wait_time:
                self.logger.warning({
                    "action": "VECTOR_STORE_BM25_WAIT_TIMEOUT",
                    "message": f"Exceeded maximum wait time ({max_wait_time}s) for BM25 index to become IDLE. State: {self._bm25_indexing_state.value}"
                })
                # Optionally, raise an error or return empty results
                raise VectorStoreError(f"BM25 index busy for more than {max_wait_time}s")
                
            # Wait a bit before checking again
            await asyncio.sleep(0.5)
            
        # Perform the search (now that state is IDLE)
        return self.keyword_search(
            query=query,
            num_results=num_results,
            filters=filters,
            collection_name=collection_name
        )
            
    async def _build_bm25_index(self) -> bool:
        """
        Build a BM25 index from existing documents in the collection.
        Acquires lock and sets state.
        
        Returns:
            bool: True if index was built, False otherwise.
        """
        async with self._bm25_lock:
            if self._bm25_indexing_state != IndexingState.IDLE:
                self.logger.warning({
                    "action": "VECTOR_STORE_BM25_BUILD_BUSY",
                    "message": f"Cannot build BM25 index, current state is {self._bm25_indexing_state.value}"
                })
                return False
                
            self._bm25_indexing_state = IndexingState.BUILDING
        
        try:
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
            self._doc_id_map = {} # Reset doc id map
            
            # Get all documents from collection
            all_docs = self._collection.get() # This might be slow for large collections
            
            if not all_docs or not all_docs.get("ids"):
                self.logger.info({
                    "action": "VECTOR_STORE_BM25_INDEX_EMPTY",
                    "message": "No documents to index for BM25"
                })
                return True # Successfully built an empty index
                
            # Process each document
            doc_ids = all_docs["ids"]
            doc_texts = all_docs["documents"]

            # Map document IDs to ChromaDB IDs
            for doc_id in doc_ids:
                self._doc_id_map[doc_id] = doc_id
            
            self.logger.info({
                "action": "VECTOR_STORE_BM25_INDEX_START",
                "message": f"Building BM25 index for {len(doc_ids)} documents"
            })
            
            # Call update logic without lock/state change
            await self._update_bm25_index_internal(doc_ids, doc_texts)
            
            self.logger.info({
                "action": "VECTOR_STORE_BM25_INDEX_COMPLETE",
                "message": "BM25 index built successfully",
                "data": {
                    "total_docs": self._bm25_index["total_docs"],
                    "avg_length": self._bm25_index["avg_doc_length"],
                    "unique_terms": len(self._bm25_index["term_doc_freq"])
                }
            })
            return True
            
        except Exception as e:
            self.logger.error({
                "action": "VECTOR_STORE_BM25_INDEX_ERROR",
                "message": f"Failed to build BM25 index: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            return False
        finally:
            async with self._bm25_lock:
                self._bm25_indexing_state = IndexingState.IDLE

    async def _update_bm25_index(self, doc_ids: List[str], doc_texts: List[str]) -> bool:
        """
        Update the BM25 index with new documents. Acquires lock and sets state.
        
        Args:
            doc_ids: List of document IDs
            doc_texts: List of document texts
            
        Returns:
            bool: True if update was successful, False otherwise.
        """
        async with self._bm25_lock:
            if self._bm25_indexing_state != IndexingState.IDLE:
                self.logger.warning({
                    "action": "VECTOR_STORE_BM25_UPDATE_BUSY",
                    "message": f"Cannot update BM25 index, current state is {self._bm25_indexing_state.value}"
                })
                return False
            self._bm25_indexing_state = IndexingState.UPDATING
            
        try:
            return await self._update_bm25_index_internal(doc_ids, doc_texts)
        except Exception as e:
             self.logger.error({
                "action": "VECTOR_STORE_BM25_INDEX_UPDATE_ERROR",
                "message": f"Failed to update BM25 index: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
             return False
        finally:
            async with self._bm25_lock:
                 self._bm25_indexing_state = IndexingState.IDLE

    async def _update_bm25_index_internal(self, doc_ids: List[str], doc_texts: List[str]) -> bool:
        """
        Internal logic to update the BM25 index. Does not manage lock or state.
        Assumes index exists or is initialized.
        
        Args:
            doc_ids: List of document IDs
            doc_texts: List of document texts
            
        Returns:
            bool: True if update was successful.
        """
        if not self._bm25_index:
            self.logger.warning({"action": "BM25_UPDATE_NO_INDEX", "message": "BM25 index not initialized for update."})
            # Initialize if it doesn't exist (e.g., first call after load)
            self._bm25_index = {
                "term_doc_freq": {}, "doc_lengths": {}, "avg_doc_length": 0, "total_docs": 0
            }
            
        # Calculate existing total token count and doc count
        # Use .get() to safely access potentially missing keys
        existing_total_docs = self._bm25_index.get("total_docs", 0)
        existing_avg_len = self._bm25_index.get("avg_doc_length", 0)
        total_tokens = existing_avg_len * existing_total_docs

        # Track which docs are actually new or updated for length/token calculations
        updated_doc_count = 0
        added_token_count = 0
        removed_token_count = 0
        
        # Process each document
        for i, (doc_id, doc_text) in enumerate(zip(doc_ids, doc_texts)):
            if not doc_text:
                doc_text = "" # Treat empty text as zero tokens
                
            # Tokenize document
            tokens = self._tokenize(doc_text)
            new_doc_length = len(tokens)
            
            # Get previous length if doc exists
            old_doc_length = self._bm25_index["doc_lengths"].get(doc_id, None)

            # If doc is new or length changed, update counts
            if old_doc_length is None: # New document
                updated_doc_count += 1
                added_token_count += new_doc_length
            elif old_doc_length != new_doc_length: # Existing doc, length changed
                removed_token_count += old_doc_length
                added_token_count += new_doc_length
                # updated_doc_count remains the same

            # Update document length in index
            self._bm25_index["doc_lengths"][doc_id] = new_doc_length
            
            # --- Update Term Frequencies --- 
            # 1. Remove old term frequencies for this document (if it existed)
            # This part needs optimization - requires iterating through all terms.
            # For now, we assume upsert means we overwrite, but IDF needs correct doc counts.
            # A more robust solution would track terms per doc.
            # Simple approach: If doc existed, iterate terms and remove this doc_id entry.
            # This is inefficient. Let's skip full removal for now and accept potential
            # slight inaccuracies in IDF until a better term tracking is implemented.
            # TODO: Implement efficient removal of old term frequencies.
            
            # 2. Add new term frequencies
            term_freq = {}
            for token in tokens:
                term_freq[token] = term_freq.get(token, 0) + 1
            
            # Update term-document frequency index
            for token, freq in term_freq.items():
                if token not in self._bm25_index["term_doc_freq"]:
                    self._bm25_index["term_doc_freq"][token] = {}
                # Store/overwrite frequency for this doc
                self._bm25_index["term_doc_freq"][token][doc_id] = freq
        
        # Update total docs and average document length
        new_total_docs = existing_total_docs + updated_doc_count
        total_tokens = total_tokens - removed_token_count + added_token_count
        
        self._bm25_index["total_docs"] = new_total_docs
        if new_total_docs > 0:
            self._bm25_index["avg_doc_length"] = total_tokens / new_total_docs
        else:
             self._bm25_index["avg_doc_length"] = 0
        
        self.logger.info({
            "action": "VECTOR_STORE_BM25_INDEX_UPDATED",
            "message": f"BM25 index internal update completed for {len(doc_ids)} documents",
            "data": {
                "documents_processed": len(doc_ids),
                "total_docs": self._bm25_index["total_docs"],
                "avg_length": self._bm25_index["avg_doc_length"]
            }
        })
        return True
            
    async def save_bm25_index(self, file_path: Optional[str] = None) -> bool:
        """
        Save the BM25 index to a file for persistence. Acquires lock and sets state.
        
        Args:
            file_path: Optional path to save the index to.
                       If None, will use a default path in the persist directory.
                       
        Returns:
            bool: True if save was successful, False otherwise
            
        Raises:
            VectorStoreError: If saving fails
        """
        async with self._bm25_lock:
            # Allow saving even if state is not IDLE (e.g., called after build/update)
            # but log a warning if it's unexpectedly busy with something else.
            if self._bm25_indexing_state not in [IndexingState.IDLE, IndexingState.BUILDING, IndexingState.UPDATING]:
                 self.logger.warning({
                    "action": "VECTOR_STORE_BM25_SAVE_BUSY",
                    "message": f"Saving BM25 index while state is {self._bm25_indexing_state.value}"
                })
                 
            previous_state = self._bm25_indexing_state
            self._bm25_indexing_state = IndexingState.SAVING
            
        try:
            if not self._enable_bm25 or not self._bm25_index:
                self.logger.warning({
                    "action": "VECTOR_STORE_BM25_SAVE_WARNING",
                    "message": "No BM25 index to save",
                    "data": {"enable_bm25": self._enable_bm25}
                })
                return False
            
            # Use default path if not provided
            if file_path is None:
                file_path = os.path.join(self._persist_directory, f"bm25_index_{self._collection_name}.json")
            
            # Prepare data to save
            save_data = {
                "bm25_index": self._bm25_index,
                "doc_id_map": self._doc_id_map,
                "parameters": {
                    "k1": self._k1,
                    "b": self._b,
                    "tokenizer_pattern": self._tokenizer_pattern
                },
                "collection_name": self._collection_name,
                "created_at": datetime.now().isoformat()
            }
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write to a temporary file first, then rename for atomicity
            temp_path = f"{file_path}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2)
            
            # Set file permissions (consider platform compatibility)
            try:
                os.chmod(temp_path, 0o600)
            except OSError as chmod_err:
                 self.logger.warning({"action":"BM25_CHMOD_ERROR", "message": f"Could not set permissions on {temp_path}: {chmod_err}"})
            
            # Rename (atomic operation on most filesystems)
            os.replace(temp_path, file_path)
            
            self.logger.info({
                "action": "VECTOR_STORE_BM25_SAVE_SUCCESS",
                "message": "Saved BM25 index to file",
                "data": {
                    "file_path": file_path,
                    "index_size": len(self._bm25_index.get("term_doc_freq", {})), 
                    "doc_count": self._bm25_index.get("total_docs", 0)
                }
            })
            
            return True
            
        except Exception as e:
            self.logger.error({
                "action": "VECTOR_STORE_BM25_SAVE_ERROR",
                "message": f"Failed to save BM25 index: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            # Don't re-raise from save, allow process to continue if possible
            return False
        finally:
            async with self._bm25_lock:
                # Restore state to IDLE only if we were the ones changing it to SAVING
                # If it was BUILDING/UPDATING before, let the outer function restore IDLE.
                if self._bm25_indexing_state == IndexingState.SAVING:
                     self._bm25_indexing_state = IndexingState.IDLE
                # If it was BUILDING or UPDATING, restore that state so the outer finally block
                # can set it back to IDLE correctly.
                elif previous_state in [IndexingState.BUILDING, IndexingState.UPDATING]:
                     self._bm25_indexing_state = previous_state

    async def load_bm25_index(self, file_path: Optional[str] = None) -> bool:
        """
        Load the BM25 index from a file. Acquires lock and sets state.
        
        Args:
            file_path: Optional path to load the index from.
                       If None, will use a default path in the persist directory.
                       
        Returns:
            bool: True if load was successful, False otherwise
        """
        async with self._bm25_lock:
            if self._bm25_indexing_state != IndexingState.IDLE:
                self.logger.warning({
                    "action": "VECTOR_STORE_BM25_LOAD_BUSY",
                    "message": f"Cannot load BM25 index, current state is {self._bm25_indexing_state.value}"
                })
                return False
            self._bm25_indexing_state = IndexingState.LOADING

        try:
            if not self._enable_bm25:
                self.logger.warning({
                    "action": "VECTOR_STORE_BM25_LOAD_WARNING",
                    "message": "BM25 not enabled, skipping index load"
                })
                return False # Not an error, just skipped
            
            # Use default path if not provided
            if file_path is None:
                file_path = os.path.join(self._persist_directory, f"bm25_index_{self._collection_name}.json")
            
            # Check if file exists
            if not os.path.exists(file_path):
                self.logger.info({
                    "action": "VECTOR_STORE_BM25_LOAD_FILE_NOT_FOUND",
                    "message": f"BM25 index file not found, will build if needed: {file_path}",
                    "data": {"file_path": file_path}
                })
                return False # Index needs to be built
            
            # Load the file
            self.logger.info({"action":"BM25_LOAD_START", "message":f"Loading BM25 index from {file_path}"})
            with open(file_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            # Validate data structure
            required_keys = ["bm25_index", "doc_id_map", "parameters", "collection_name"]
            for key in required_keys:
                if key not in loaded_data:
                    self.logger.warning({
                        "action": "VECTOR_STORE_BM25_LOAD_INVALID_FORMAT",
                        "message": f"Invalid BM25 index file format, missing key: {key}",
                        "data": {"file_path": file_path, "missing_key": key}
                    })
                    return False # Invalid file, needs rebuild
            
            # Check if the index is for the correct collection
            if loaded_data["collection_name"] != self._collection_name:
                self.logger.warning({
                    "action": "VECTOR_STORE_BM25_LOAD_COLLECTION_MISMATCH",
                    "message": "BM25 index file is for a different collection",
                    "data": {
                        "file_collection": loaded_data["collection_name"],
                        "current_collection": self._collection_name
                    }
                })
                return False # Wrong collection, needs rebuild
            
            # Load the index data
            self._bm25_index = loaded_data["bm25_index"]
            self._doc_id_map = loaded_data["doc_id_map"]
            
            # Optionally update parameters if needed
            if "parameters" in loaded_data:
                params = loaded_data["parameters"]
                self._k1 = params.get("k1", self._k1)
                self._b = params.get("b", self._b)
                self._tokenizer_pattern = params.get("tokenizer_pattern", self._tokenizer_pattern)
            
            self.logger.info({
                "action": "VECTOR_STORE_BM25_LOAD_SUCCESS",
                "message": "Loaded BM25 index from file",
                "data": {
                    "file_path": file_path,
                    "index_size": len(self._bm25_index.get("term_doc_freq", {})), 
                    "doc_count": self._bm25_index.get("total_docs", 0)
                }
            })
            
            return True # Successfully loaded
            
        except json.JSONDecodeError as e:
            self.logger.error({
                "action": "VECTOR_STORE_BM25_LOAD_JSON_ERROR",
                "message": f"Failed to parse BM25 index file: {str(e)}",
                "data": {"error": str(e), "file_path": file_path}
            })
            return False # Needs rebuild
        except Exception as e:
            self.logger.error({
                "action": "VECTOR_STORE_BM25_LOAD_ERROR",
                "message": f"Failed to load BM25 index: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            # Raise for unexpected errors during load
            raise VectorStoreError(f"Failed to load BM25 index: {str(e)}") from e
        finally:
             async with self._bm25_lock:
                 self._bm25_indexing_state = IndexingState.IDLE

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
        collection_name: Optional[str] = None,
    ) -> int:
        """
        Delete documents from the vector store.
        
        Args:
            document_ids: Optional list of document IDs to delete
            filters: Optional metadata filters to select documents for deletion
            collection_name: Optional name of the collection to delete from.
                             If None, the default collection will be used.
            
        Returns:
            Number of documents deleted
            
        Raises:
            VectorStoreError: If deletion fails
        """
        if not self._is_initialized:
            raise VectorStoreError("Vector store not initialized. Call initialize() first.")
        
        if not document_ids and not filters:
            self.logger.warning({
                "action": "VECTOR_STORE_EMPTY_DELETE",
                "message": "No document IDs or filters provided for deletion"
            })
            return 0
        
        try:
            # Use provided collection name or default
            target_collection_name = collection_name or self._collection_name
            
            # Get the specified collection
            try:
                collection = self._client.get_collection(name=target_collection_name)
                self.logger.info({
                    "action": "VECTOR_STORE_COLLECTION_FOUND",
                    "message": f"Found collection '{target_collection_name}' for delete operation"
                })
            except Exception as e:
                self.logger.warning({
                    "action": "VECTOR_STORE_COLLECTION_NOT_FOUND",
                    "message": f"Collection '{target_collection_name}' not found for delete operation",
                    "data": {"error": str(e)}
                })
                return 0
            
            # Handle ID-based deletion
            if document_ids:
                self.logger.info({
                    "action": "VECTOR_STORE_DELETE_IDS",
                    "message": f"Deleting {len(document_ids)} documents by ID",
                    "data": {"collection_name": target_collection_name, "count": len(document_ids)}
                })
                collection.delete(ids=document_ids)
                
                # If this is the default collection, update BM25 index
                if self._enable_bm25 and target_collection_name == self._collection_name:
                    # Remove from BM25 index
                    for doc_id in document_ids:
                        if doc_id in self._doc_id_map:
                            del self._doc_id_map[doc_id]
                
                return len(document_ids)
            
            # Handle filter-based deletion
            elif filters:
                # First get matching documents to count them
                results = collection.get(where=filters)
                matched_ids = results.get("ids", [])
                matched_count = len(matched_ids)
                
                if matched_count > 0:
                    self.logger.info({
                        "action": "VECTOR_STORE_DELETE_FILTERS",
                        "message": f"Deleting {matched_count} documents by filter",
                        "data": {"collection_name": target_collection_name, "count": matched_count}
                    })
                    collection.delete(where=filters)
                    
                    # If this is the default collection, update BM25 index
                    if self._enable_bm25 and target_collection_name == self._collection_name:
                        # Remove from BM25 index
                        for doc_id in matched_ids:
                            if doc_id in self._doc_id_map:
                                del self._doc_id_map[doc_id]
                    
                return matched_count
            
        except Exception as e:
            self.logger.error({
                "action": "VECTOR_STORE_DELETE_ERROR",
                "message": f"Failed to delete documents: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise VectorStoreError(f"Failed to delete documents: {str(e)}") from e
    
    async def count(self, filters: Optional[Dict[str, Any]] = None, collection_name: Optional[str] = None) -> int:
        """
        Count documents in the vector store.
        
        Args:
            filters: Optional metadata filters to apply
            collection_name: Optional name of the collection to count in.
                             If None, the default collection will be used.
            
        Returns:
            Number of documents matching the filter
            
        Raises:
            VectorStoreError: If counting fails
        """
        if not self._is_initialized:
            raise VectorStoreError("Vector store not initialized. Call initialize() first.")
        
        try:
            # Use provided collection name or default
            target_collection_name = collection_name or self._collection_name
            
            # Get the specified collection
            try:
                collection = self._client.get_collection(name=target_collection_name)
                self.logger.info({
                    "action": "VECTOR_STORE_COLLECTION_FOUND",
                    "message": f"Found collection '{target_collection_name}' for count operation"
                })
            except Exception as e:
                self.logger.warning({
                    "action": "VECTOR_STORE_COLLECTION_NOT_FOUND",
                    "message": f"Collection '{target_collection_name}' not found for count operation",
                    "data": {"error": str(e)}
                })
                return 0
            
            # Count with or without filters
            if filters:
                results = collection.get(where=filters, include=[])
                count = len(results["ids"]) if "ids" in results else 0
            else:
                results = collection.get(include=[])
                count = len(results["ids"]) if "ids" in results else 0
            
            self.logger.info({
                "action": "VECTOR_STORE_COUNT",
                "message": f"Counted {count} documents in collection '{target_collection_name}'",
                "data": {
                    "count": count,
                    "collection_name": target_collection_name,
                    "has_filters": filters is not None
                }
            })
            
            return count
            
        except Exception as e:
            self.logger.error({
                "action": "VECTOR_STORE_COUNT_ERROR",
                "message": f"Failed to count documents: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise VectorStoreError(f"Failed to count documents: {str(e)}") from e
    
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

    def find_collection_name(self, source: str) -> str:
        """
        Get the collection name for a given source.
        
        Args:
            source: Source identifier (e.g., "telegram", "whatsapp")
            
        Returns:
            Collection name to use for this source
        """
        if not self._is_initialized:
            self.logger.warning({
                "action": "VECTOR_STORE_NOT_INITIALIZED",
                "message": "Vector store not initialized when finding collection name"
            })
            return self._collection_name
        
        collection_name = self._source_collection_map.get(source, self._collection_name)
        
        self.logger.debug({
            "action": "VECTOR_STORE_FIND_COLLECTION",
            "message": f"Source '{source}' mapped to collection '{collection_name}'",
            "data": {"source": source, "collection": collection_name}
        })
        
        return collection_name 