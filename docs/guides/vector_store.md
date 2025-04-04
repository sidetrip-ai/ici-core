# Vector Store Component Guide

## Overview

A Vector Store is responsible for storing, retrieving, and searching vector embeddings and their associated documents. It enables semantic search capabilities by finding documents whose embeddings are most similar to a query embedding.

Vector Store is primarily an infrastructure component - you only need to implement a custom Vector Store if you want to change the underlying storage system or improve performance. If you're simply connecting a new data source, you don't need to focus on implementing a Vector Store component at all.

## Interface

All vector stores must implement the `VectorStore` interface defined in `ici/core/interfaces/vector_store.py`:

```python
class VectorStore(ABC):
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the vector store with configuration parameters."""
        pass
        
    @abstractmethod
    async def add_documents(
        self, 
        documents: List[Dict[str, Any]], 
        vectors: List[List[float]], 
        collection_name: str = "default"
    ) -> List[str]:
        """
        Add documents and their embeddings to the vector store.
        
        Args:
            documents: List of document dictionaries
            vectors: List of embedding vectors
            collection_name: Name of the collection to add to
            
        Returns:
            List[str]: List of document IDs
        """
        pass
        
    @abstractmethod
    def search(
        self, 
        query_vector: List[float], 
        num_results: int = 5, 
        filters: Optional[Dict[str, Any]] = None,
        collection_name: str = "default"
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.
        
        Args:
            query_vector: The query embedding vector
            num_results: Maximum number of results to return
            filters: Optional metadata filters
            collection_name: Name of the collection to search
            
        Returns:
            List[Dict[str, Any]]: List of documents with similarity scores
        """
        pass
```

## Expected Input and Output

### Add Documents

**Input:**
- `documents`: List of document dictionaries with text and metadata
- `vectors`: List of embedding vectors corresponding to each document
- `collection_name`: Collection to store the documents in

```python
documents = [
    {
        "id": "doc1",
        "text": "This is document 1",
        "metadata": {
            "source": "example",
            "creation_date": "2023-06-15T12:00:00Z"
        }
    },
    {
        "id": "doc2",
        "text": "This is document 2",
        "metadata": {
            "source": "example",
            "creation_date": "2023-06-15T13:00:00Z"
        }
    }
]

vectors = [
    [0.1, 0.2, 0.3, ...],  # Embedding for document 1
    [0.4, 0.5, 0.6, ...]   # Embedding for document 2
]

collection_name = "example_collection"
```

**Output:**
- List of document IDs

```python
["doc1", "doc2"]  # IDs of the added documents
```

### Search

**Input:**
- `query_vector`: Embedding vector of the search query
- `num_results`: Maximum number of results to return
- `filters`: Optional metadata filters to narrow search
- `collection_name`: Collection to search in

```python
query_vector = [0.2, 0.3, 0.4, ...]  # Query embedding
num_results = 3
filters = {"metadata.source": "example"}  # Only return documents with source=example
collection_name = "example_collection"
```

**Output:**
- List of document dictionaries with similarity scores

```python
[
    {
        "id": "doc2",
        "text": "This is document 2",
        "metadata": {
            "source": "example",
            "creation_date": "2023-06-15T13:00:00Z"
        },
        "score": 0.92  # Similarity score (higher is more similar)
    },
    {
        "id": "doc1",
        "text": "This is document 1",
        "metadata": {
            "source": "example",
            "creation_date": "2023-06-15T12:00:00Z"
        },
        "score": 0.85
    }
]
```

## Implementing a Custom Vector Store

Here's a step-by-step guide to implementing a custom vector store:

### 1. Create a new class

Create a new file in `ici/adapters/vector_stores/` for your custom vector store:

```python
"""
CustomDB vector store implementation.
"""

import os
from typing import Dict, Any, List, Optional, Tuple

from ici.core.interfaces.vector_store import VectorStore
from ici.core.exceptions import VectorStoreError
from ici.adapters.loggers import StructuredLogger
from ici.utils.config import get_component_config

class CustomDBStore(VectorStore):
    """
    Vector store implementation using CustomDB.
    
    This vector store provides storage and semantic search capabilities
    for document embeddings using the CustomDB database.
    
    Configuration options:
    - connection_string: Connection string for the database
    - index_type: Type of index to use (e.g., "hnsw", "flat")
    - dimensions: Vector dimensions
    """
    
    def __init__(self, logger_name: str = "custom_vector_store"):
        """
        Initialize the CustomDB vector store.
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = StructuredLogger(name=logger_name)
        self._is_initialized = False
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        
        # Default configuration
        self._connection_string = "localhost:8080"
        self._index_type = "hnsw"
        self._dimensions = 768
        self._db_client = None
        self._collections = {}
```

### 2. Implement the initialize method

Load your configuration from config.yaml and initialize the connection:

```python
async def initialize(self) -> None:
    """
    Initialize the vector store with configuration parameters.
    
    Loads configuration from config.yaml and establishes a connection
    to the underlying database.
    
    Returns:
        None
        
    Raises:
        VectorStoreError: If initialization fails
    """
    try:
        self.logger.info({
            "action": "VECTOR_STORE_INIT_START",
            "message": "Initializing CustomDB vector store"
        })
        
        # Load vector store configuration
        try:
            store_config = get_component_config("vector_stores.custom_db", self._config_path)
            
            # Extract configuration with defaults
            if store_config:
                self._connection_string = store_config.get("connection_string", self._connection_string)
                self._index_type = store_config.get("index_type", self._index_type)
                self._dimensions = int(store_config.get("dimensions", self._dimensions))
                
                # Additional configuration options can be extracted here
                
                self.logger.info({
                    "action": "VECTOR_STORE_CONFIG_LOADED",
                    "message": "Loaded vector store configuration",
                    "data": {
                        "connection_string": self._connection_string,
                        "index_type": self._index_type,
                        "dimensions": self._dimensions
                    }
                })
            
        except Exception as e:
            # Use defaults if configuration loading fails
            self.logger.warning({
                "action": "VECTOR_STORE_CONFIG_WARNING",
                "message": f"Failed to load configuration: {str(e)}. Using defaults.",
                "data": {"error": str(e)}
            })
        
        # Initialize the database connection
        try:
            # Here you would use a client library to connect to your database
            # For example:
            # from custom_db_client import CustomDBClient
            # self._db_client = CustomDBClient(self._connection_string)
            
            # Placeholder for database connection
            self._db_client = self._initialize_client()
            
            self.logger.info({
                "action": "VECTOR_STORE_CONNECTION_ESTABLISHED",
                "message": "Connected to CustomDB",
                "data": {"connection_string": self._connection_string}
            })
            
        except Exception as e:
            self.logger.error({
                "action": "VECTOR_STORE_CONNECTION_ERROR",
                "message": f"Failed to connect to CustomDB: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise VectorStoreError(f"Failed to connect to CustomDB: {str(e)}") from e
        
        self._is_initialized = True
        
        self.logger.info({
            "action": "VECTOR_STORE_INIT_SUCCESS",
            "message": "CustomDB vector store initialized successfully"
        })
        
    except Exception as e:
        self.logger.error({
            "action": "VECTOR_STORE_INIT_ERROR",
            "message": f"Failed to initialize vector store: {str(e)}",
            "data": {"error": str(e), "error_type": type(e).__name__}
        })
        raise VectorStoreError(f"Vector store initialization failed: {str(e)}") from e

def _initialize_client(self):
    """
    Initialize the actual database client.
    
    This is a placeholder method - implement with your specific database client.
    
    Returns:
        The initialized database client
    """
    # Replace with actual client initialization
    # Example:
    # from custom_db_client import CustomDBClient
    # return CustomDBClient(
    #     connection_string=self._connection_string,
    #     index_type=self._index_type
    # )
    
    # Return a placeholder for now
    return "db_client_placeholder"
```

### 3. Implement the add_documents method

Implement the method to store documents and their embeddings:

```python
async def add_documents(
    self, 
    documents: List[Dict[str, Any]], 
    vectors: List[List[float]], 
    collection_name: str = "default"
) -> List[str]:
    """
    Add documents and their embeddings to the vector store.
    
    Args:
        documents: List of document dictionaries with text and metadata
        vectors: List of embedding vectors corresponding to documents
        collection_name: Name of the collection to add documents to
        
    Returns:
        List[str]: List of document IDs
        
    Raises:
        VectorStoreError: If adding documents fails
    """
    if not self._is_initialized:
        raise VectorStoreError("Vector store not initialized. Call initialize() first.")
    
    if len(documents) != len(vectors):
        raise VectorStoreError(f"Number of documents ({len(documents)}) does not match number of vectors ({len(vectors)})")
    
    if not documents:
        return []
    
    try:
        # Ensure the collection exists
        collection = await self._get_or_create_collection(collection_name)
        
        # Prepare documents for insertion
        document_ids = []
        
        # Add each document with its embedding
        for i, (doc, vector) in enumerate(zip(documents, vectors)):
            # Generate ID if not provided
            doc_id = doc.get("id") or f"{collection_name}_{int(time.time())}_{i}"
            document_ids.append(doc_id)
            
            # Add document to the collection
            await self._add_document_to_collection(collection, doc_id, doc, vector)
        
        self.logger.info({
            "action": "VECTOR_STORE_DOCUMENTS_ADDED",
            "message": f"Added {len(documents)} documents to collection '{collection_name}'",
            "data": {
                "collection_name": collection_name,
                "document_count": len(documents)
            }
        })
        
        return document_ids
        
    except Exception as e:
        self.logger.error({
            "action": "VECTOR_STORE_ADD_ERROR",
            "message": f"Failed to add documents to vector store: {str(e)}",
            "data": {
                "collection_name": collection_name,
                "error": str(e),
                "error_type": type(e).__name__
            }
        })
        raise VectorStoreError(f"Failed to add documents: {str(e)}") from e

async def _get_or_create_collection(self, collection_name: str):
    """
    Get or create a collection.
    
    This is a placeholder method - implement with your specific database.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        The collection object
    """
    # Check if collection already exists in cache
    if collection_name in self._collections:
        return self._collections[collection_name]
    
    # In a real implementation, you would check if the collection exists
    # in the database and create it if not
    # Example:
    # if not await self._db_client.collection_exists(collection_name):
    #     collection = await self._db_client.create_collection(
    #         name=collection_name,
    #         vector_dimension=self._dimensions,
    #         index_type=self._index_type
    #     )
    # else:
    #     collection = await self._db_client.get_collection(collection_name)
    
    # Create a placeholder collection
    collection = f"collection_{collection_name}"
    
    # Cache the collection
    self._collections[collection_name] = collection
    
    return collection

async def _add_document_to_collection(self, collection, doc_id: str, doc: Dict[str, Any], vector: List[float]):
    """
    Add a document and its embedding to a collection.
    
    This is a placeholder method - implement with your specific database.
    
    Args:
        collection: The collection object
        doc_id: Document ID
        doc: Document dictionary
        vector: Embedding vector
    """
    # In a real implementation, you would add the document and embedding to your database
    # Example:
    # await self._db_client.insert(
    #     collection=collection,
    #     id=doc_id,
    #     vector=vector,
    #     metadata=doc
    # )
    
    # For this placeholder, we just log
    self.logger.debug({
        "action": "VECTOR_STORE_DOC_ADDED",
        "message": f"Added document {doc_id} to collection",
        "data": {"doc_id": doc_id}
    })
```

### 4. Implement the search method

Implement the method to search for similar documents:

```python
def search(
    self, 
    query_vector: List[float], 
    num_results: int = 5, 
    filters: Optional[Dict[str, Any]] = None,
    collection_name: str = "default"
) -> List[Dict[str, Any]]:
    """
    Search for similar documents.
    
    Args:
        query_vector: The query embedding vector
        num_results: Maximum number of results to return
        filters: Optional metadata filters to narrow search
        collection_name: Name of the collection to search
        
    Returns:
        List[Dict[str, Any]]: List of documents with similarity scores
        
    Raises:
        VectorStoreError: If search fails
    """
    if not self._is_initialized:
        raise VectorStoreError("Vector store not initialized. Call initialize() first.")
    
    try:
        # Get the collection
        if collection_name not in self._collections:
            self.logger.warning({
                "action": "VECTOR_STORE_COLLECTION_NOT_FOUND",
                "message": f"Collection '{collection_name}' not found",
                "data": {"collection_name": collection_name}
            })
            return []
        
        collection = self._collections[collection_name]
        
        # Perform the search
        results = self._search_collection(collection, query_vector, num_results, filters)
        
        self.logger.info({
            "action": "VECTOR_STORE_SEARCH_COMPLETE",
            "message": f"Search returned {len(results)} results",
            "data": {
                "collection_name": collection_name,
                "num_results": len(results),
                "requested_results": num_results
            }
        })
        
        return results
        
    except Exception as e:
        self.logger.error({
            "action": "VECTOR_STORE_SEARCH_ERROR",
            "message": f"Failed to search vector store: {str(e)}",
            "data": {
                "collection_name": collection_name,
                "error": str(e),
                "error_type": type(e).__name__
            }
        })
        raise VectorStoreError(f"Failed to search: {str(e)}") from e

def _search_collection(self, collection, query_vector: List[float], num_results: int, filters: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Search a collection for similar documents.
    
    This is a placeholder method - implement with your specific database.
    
    Args:
        collection: The collection object
        query_vector: The query embedding vector
        num_results: Maximum number of results to return
        filters: Optional metadata filters to narrow search
        
    Returns:
        List[Dict[str, Any]]: List of documents with similarity scores
    """
    # In a real implementation, you would search your database
    # Example:
    # search_results = self._db_client.search(
    #     collection=collection,
    #     query_vector=query_vector,
    #     top_k=num_results,
    #     filters=filters
    # )
    # return search_results
    
    # Return a placeholder result for demonstration
    import random
    
    # Generate some random results
    results = []
    for i in range(min(num_results, 3)):  # Return fewer than requested for demo
        results.append({
            "id": f"doc_{i}",
            "text": f"This is document {i}",
            "metadata": {
                "source": "example",
                "creation_date": "2023-06-15T12:00:00Z"
            },
            "score": random.random()  # Random similarity score
        })
    
    # Sort by score (higher is better)
    results.sort(key=lambda x: x["score"], reverse=True)
    
    return results
```

### 5. Implement utility methods (optional)

Add useful utility methods for managing your vector store:

```python
async def delete_documents(self, document_ids: List[str], collection_name: str = "default") -> int:
    """
    Delete documents from the vector store.
    
    Args:
        document_ids: List of document IDs to delete
        collection_name: Name of the collection to delete from
        
    Returns:
        int: Number of documents deleted
        
    Raises:
        VectorStoreError: If deletion fails
    """
    if not self._is_initialized:
        raise VectorStoreError("Vector store not initialized. Call initialize() first.")
    
    if not document_ids:
        return 0
    
    try:
        # Get the collection
        if collection_name not in self._collections:
            return 0
        
        collection = self._collections[collection_name]
        
        # Delete the documents
        deleted_count = await self._delete_documents_from_collection(collection, document_ids)
        
        self.logger.info({
            "action": "VECTOR_STORE_DOCUMENTS_DELETED",
            "message": f"Deleted {deleted_count} documents from collection '{collection_name}'",
            "data": {
                "collection_name": collection_name,
                "document_count": deleted_count
            }
        })
        
        return deleted_count
        
    except Exception as e:
        self.logger.error({
            "action": "VECTOR_STORE_DELETE_ERROR",
            "message": f"Failed to delete documents: {str(e)}",
            "data": {
                "collection_name": collection_name,
                "error": str(e),
                "error_type": type(e).__name__
            }
        })
        raise VectorStoreError(f"Failed to delete documents: {str(e)}") from e

async def _delete_documents_from_collection(self, collection, document_ids: List[str]) -> int:
    """
    Delete documents from a collection.
    
    This is a placeholder method - implement with your specific database.
    
    Args:
        collection: The collection object
        document_ids: List of document IDs to delete
        
    Returns:
        int: Number of documents deleted
    """
    # In a real implementation, you would delete the documents from your database
    # Example:
    # deleted_count = await self._db_client.delete(
    #     collection=collection,
    #     ids=document_ids
    # )
    # return deleted_count
    
    # For this placeholder, we just return the number of IDs
    return len(document_ids)

async def create_collection(self, collection_name: str) -> bool:
    """
    Create a new collection.
    
    Args:
        collection_name: Name of the collection to create
        
    Returns:
        bool: True if collection was created, False if it already existed
        
    Raises:
        VectorStoreError: If creation fails
    """
    if not self._is_initialized:
        raise VectorStoreError("Vector store not initialized. Call initialize() first.")
    
    try:
        # Check if collection already exists
        if collection_name in self._collections:
            return False
        
        # Create the collection
        collection = await self._create_collection_in_db(collection_name)
        
        # Cache the collection
        self._collections[collection_name] = collection
        
        self.logger.info({
            "action": "VECTOR_STORE_COLLECTION_CREATED",
            "message": f"Created collection '{collection_name}'",
            "data": {"collection_name": collection_name}
        })
        
        return True
        
    except Exception as e:
        self.logger.error({
            "action": "VECTOR_STORE_CREATE_COLLECTION_ERROR",
            "message": f"Failed to create collection: {str(e)}",
            "data": {
                "collection_name": collection_name,
                "error": str(e),
                "error_type": type(e).__name__
            }
        })
        raise VectorStoreError(f"Failed to create collection: {str(e)}") from e

async def _create_collection_in_db(self, collection_name: str):
    """
    Create a collection in the database.
    
    This is a placeholder method - implement with your specific database.
    
    Args:
        collection_name: Name of the collection to create
        
    Returns:
        The created collection object
    """
    # In a real implementation, you would create the collection in your database
    # Example:
    # collection = await self._db_client.create_collection(
    #     name=collection_name,
    #     vector_dimension=self._dimensions,
    #     index_type=self._index_type
    # )
    # return collection
    
    # Return a placeholder collection
    return f"collection_{collection_name}"

async def healthcheck(self) -> Dict[str, Any]:
    """
    Check the health of the vector store.
    
    Returns:
        Dict[str, Any]: Health status information
        
    Raises:
        VectorStoreError: If the health check fails
    """
    if not self._is_initialized:
        return {
            "healthy": False,
            "message": "Vector store not initialized"
        }
    
    try:
        # Check connection to the database
        is_connected = await self._check_connection()
        
        if is_connected:
            return {
                "healthy": True,
                "message": "Vector store is healthy",
                "collections": list(self._collections.keys()),
                "connection": self._connection_string
            }
        else:
            return {
                "healthy": False,
                "message": "Vector store is not connected to the database"
            }
            
    except Exception as e:
        return {
            "healthy": False,
            "message": f"Health check failed: {str(e)}",
            "error": str(e)
        }

async def _check_connection(self) -> bool:
    """
    Check the connection to the database.
    
    This is a placeholder method - implement with your specific database.
    
    Returns:
        bool: True if connected, False otherwise
    """
    # In a real implementation, you would check the connection to your database
    # Example:
    # return await self._db_client.ping()
    
    # Return True for this placeholder
    return True
```

## Configuration Setup

In your `config.yaml` file, add a section for your vector store:

```yaml
vector_stores:
  custom_db:
    connection_string: "localhost:8080"
    index_type: "hnsw"
    dimensions: 768
    # Additional configuration options specific to your vector store
    distance_metric: "cosine"
    ef_search: 128
    m: 16
```

## Vector Store Pipeline Integration

Your vector store will be used by the ingestion pipeline:

```python
# In DefaultIngestionPipeline._initialize_components:
custom_vector_store = CustomDBStore()
await custom_vector_store.initialize()

# Set as pipeline vector store
self._vector_store = custom_vector_store
```

## Best Practices

1. **Indexing Strategy**: Choose appropriate indexing methods (e.g., HNSW, IVF) based on your scale and performance requirements.

2. **Connection Management**: Handle connection pooling and reconnection for robustness.

3. **Collection Management**: Support multiple collections to organize data logically.

4. **Metadata Filtering**: Implement efficient filtering on metadata to narrow search results.

5. **Error Handling**: Gracefully handle database errors and connection issues.

6. **Bulk Operations**: Support batch operations for better performance.

7. **Cache Management**: Consider caching frequent queries or collection handles.

8. **Resource Cleanup**: Properly close connections and clean up resources when shutting down.

9. **Distance Metrics**: Support appropriate distance metrics for your use case (cosine, euclidean, dot product).

10. **Scalability**: Design for horizontal scaling if needed for large document collections.

## Example Vector Store Implementations

Explore existing vector stores for reference:
- `ici/adapters/vector_stores/chroma.py` - Uses ChromaDB
- `ici/adapters/vector_stores/pinecone.py` - Uses Pinecone (if available in the codebase)
