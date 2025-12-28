from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
import re
from ici.core.interfaces.vector_store import VectorStore as VectorStoreInterface
from ici.core.exceptions import VectorStoreError

class VectorStore(VectorStoreInterface):
    """Class for managing document vectors using ChromaDB."""
    
    def __init__(self, collection_name: str = "documents"):
        """
        Initialize the vector store.
        
        Args:
            collection_name: Name of the ChromaDB collection
        """
        self.collection_name = collection_name
        self._is_initialized = False
        self._document_names = set()
        
    async def initialize(self) -> None:
        """Initialize the vector store with ChromaDB client and collection."""
        try:
            self.client = chromadb.Client(Settings(
                allow_reset=True,
                is_persistent=True
            ))
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            self._is_initialized = True
            
        except Exception as e:
            raise VectorStoreError(f"Failed to initialize vector store: {str(e)}")
    
    def store_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Store documents with their vectors, text, and metadata."""
        if not self._is_initialized:
            raise VectorStoreError("Vector store not initialized. Call initialize() first.")
            
        try:
            for doc in documents:
                if 'source' in doc.get('metadata', {}):
                    self._document_names.add(doc['metadata']['source'])
                
                # Generate a unique ID for the document
                doc_id = str(hash(doc['text']))
                
                # Add the document to the collection
                self.collection.add(
                    documents=[doc['text']],
                    metadatas=[doc['metadata']],
                    ids=[doc_id]
                )
        except Exception as e:
            raise VectorStoreError(f"Failed to store documents: {str(e)}")
    
    def search(
        self,
        query: str,
        num_results: int = 5,
        search_type: str = "content",
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for documents by content or filename.
        
        Args:
            query: Search query (text or filename)
            num_results: Number of results to return
            search_type: Type of search ("content" or "filename")
            filters: Optional metadata filters
            
        Returns:
            List of documents with their metadata and similarity scores
        """
        if not self._is_initialized:
            raise VectorStoreError("Vector store not initialized. Call initialize() first.")
            
        try:
            if search_type == "filename":
                # Search by filename using regex pattern matching
                pattern = re.compile(query, re.IGNORECASE)
                matching_docs = []
                
                # Get all documents
                all_docs = self.collection.get()
                
                # Filter documents by filename
                for doc, metadata in zip(all_docs['documents'], all_docs['metadatas']):
                    if metadata and 'source' in metadata:
                        filename = metadata['source']
                        if pattern.search(filename):
                            matching_docs.append({
                                'text': doc,
                                'metadata': metadata,
                                'score': 1.0  # Perfect match for filename search
                            })
                
                # Sort by filename similarity and limit results
                matching_docs.sort(key=lambda x: x['metadata']['source'])
                return matching_docs[:num_results]
            else:
                # Content-based search
                results = self.collection.query(
                    query_texts=[query],
                    n_results=num_results,
                    where=filters
                )
                
                formatted_results = []
                if results['documents']:
                    for doc, metadata, distance in zip(
                        results['documents'][0],
                        results['metadatas'][0],
                        results['distances'][0]
                    ):
                        formatted_results.append({
                            'text': doc,
                            'metadata': metadata,
                            'score': 1 - distance  # Convert distance to similarity score
                        })
                
                return formatted_results
                
        except Exception as e:
            raise VectorStoreError(f"Search operation failed: {str(e)}")
    
    def delete(
        self,
        document_ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Delete documents from the store."""
        if not self._is_initialized:
            raise VectorStoreError("Vector store not initialized. Call initialize() first.")
            
        try:
            if document_ids:
                self.collection.delete(ids=document_ids)
                return len(document_ids)
            elif filters:
                # Get matching documents first to count them
                matching = self.collection.get(where=filters)
                if matching['ids']:
                    self.collection.delete(ids=matching['ids'])
                    return len(matching['ids'])
            return 0
            
        except Exception as e:
            raise VectorStoreError(f"Delete operation failed: {str(e)}")
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count documents in the store."""
        if not self._is_initialized:
            raise VectorStoreError("Vector store not initialized. Call initialize() first.")
            
        try:
            if filters:
                return len(self.collection.get(where=filters)['ids'])
            return len(self.collection.get()['ids'])
            
        except Exception as e:
            raise VectorStoreError(f"Count operation failed: {str(e)}")
    
    def healthcheck(self) -> Dict[str, Any]:
        """Check if the vector store is functioning properly."""
        try:
            is_healthy = self._is_initialized and self.collection is not None
            return {
                'healthy': is_healthy,
                'message': "Vector store is operational" if is_healthy else "Vector store not initialized",
                'details': {
                    'initialized': self._is_initialized,
                    'collection_name': self.collection_name if self._is_initialized else None,
                    'document_count': self.count() if is_healthy else 0
                }
            }
        except Exception as e:
            return {
                'healthy': False,
                'message': f"Vector store health check failed: {str(e)}",
                'details': {'error': str(e)}
            }
    
    def add_documents(
        self, documents: List[Dict[str, Any]], vectors: List[List[float]]
    ) -> List[str]:
        """Add documents with their vector embeddings."""
        if not self._is_initialized:
            raise VectorStoreError("Vector store not initialized. Call initialize() first.")
            
        try:
            doc_ids = [str(hash(doc['text'])) for doc in documents]
            
            self.collection.add(
                documents=[doc['text'] for doc in documents],
                metadatas=[doc.get('metadata', {}) for doc in documents],
                embeddings=vectors,
                ids=doc_ids
            )
            
            # Update document names cache
            for doc in documents:
                if 'source' in doc.get('metadata', {}):
                    self._document_names.add(doc['metadata']['source'])
            
            return doc_ids
            
        except Exception as e:
            raise VectorStoreError(f"Failed to add documents with vectors: {str(e)}")
    
    def clear(self) -> None:
        """Clear all documents from the store."""
        if not self._is_initialized:
            raise VectorStoreError("Vector store not initialized. Call initialize() first.")
            
        try:
            # Get all documents to get their IDs
            all_docs = self.collection.get()
            
            if all_docs and all_docs['ids']:
                # Delete all documents by their IDs
                self.collection.delete(ids=all_docs['ids'])
                
            # Clear the document names cache
            self._document_names.clear()
            
        except Exception as e:
            raise VectorStoreError(f"Failed to clear vector store: {str(e)}")
    
    def get_document_names(self) -> List[str]:
        """Get list of all document names in the store."""
        if not self._is_initialized:
            raise VectorStoreError("Vector store not initialized. Call initialize() first.")
        return sorted(list(self._document_names)) 