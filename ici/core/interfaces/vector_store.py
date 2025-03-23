from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class VectorStore(ABC):
    """
    Interface for components that store processed documents with embeddings and
    retrieve relevant data based on vector similarity.

    The VectorStore abstracts the underlying storage technology, allowing flexibility
    in scaling from local to distributed systems while supporting advanced metadata filtering.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the vector store with configuration parameters.
        
        This method should be called after the vector store instance is created,
        before any other methods are used. Configuration should be loaded from
        a central configuration source (e.g., config.yaml).
        
        Returns:
            None
        
        Raises:
            Exception: If initialization fails for any reason.
        """
        pass

    @abstractmethod
    def store_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Stores documents with their vectors, text, and metadata.

        Input documents should have the following structure:
        - 'vector': List[float] - Embedding vector
        - 'text': str - Original text content
        - 'metadata': Dict[str, Any] - Contextual data (e.g., source, timestamp)

        Args:
            documents: List of documents to store

        Raises:
            VectorStoreError: If document storage fails for any reason
        """
        pass

    @abstractmethod
    def search(
        self,
        query_vector: List[float],
        num_results: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves the most similar documents based on the query vector.

        Supports advanced metadata filtering with comparison operators:
        - Equality: {'source': 'Twitter'}
        - Greater than/less than: {'timestamp': {'gte': 1698777600}}
        - Array containment: {'tags': {'in': ['important', 'urgent']}}
        - Logical combinations: {'$and': [{'source': 'Twitter'}, {'timestamp': {'gte': 1698777600}}]}

        Args:
            query_vector: The vector to search for
            num_results: Number of results to return
            filters: Optional metadata filters to apply during search

        Returns:
            List[Dict[str, Any]]: List of documents, each containing:
                - 'text': Original text content
                - 'metadata': Original metadata
                - 'score': Similarity score (higher is more similar)

        Raises:
            VectorStoreError: If the search operation fails for any reason
        """
        pass

    @abstractmethod
    def delete(
        self,
        document_ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Deletes documents from the vector store by ID or filter.

        Args:
            document_ids: Optional list of document IDs to delete
            filters: Optional metadata filters to select documents for deletion

        Returns:
            int: Number of documents deleted

        Raises:
            VectorStoreError: If the delete operation fails for any reason
        """
        pass

    @abstractmethod
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Counts documents in the vector store, optionally filtered by metadata.

        Args:
            filters: Optional metadata filters to apply

        Returns:
            int: Number of documents matching the filter

        Raises:
            VectorStoreError: If the count operation fails for any reason
        """
        pass

    @abstractmethod
    def healthcheck(self) -> Dict[str, Any]:
        """
        Checks if the vector store is properly configured and functioning.

        Returns:
            Dict[str, Any]: A dictionary containing health status information:
                {
                    'healthy': bool,  # Whether the vector store is functioning properly
                    'message': str,   # Optional message providing more details
                    'details': dict   # Optional additional details about the health check
                }

        Raises:
            VectorStoreError: If the health check itself encounters an error
        """
        pass

    @abstractmethod
    def add_documents(
        self, documents: List[Dict[str, Any]], vectors: List[List[float]]
    ) -> List[str]:
        """
        Stores documents along with their vector embeddings.

        Args:
            documents: List of documents to store
            vectors: List of vector embeddings for the documents

        Returns:
            List[str]: List of document IDs

        Raises:
            VectorStoreError: If document storage fails for any reason
        """
        pass
