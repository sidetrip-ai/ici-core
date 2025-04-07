from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
import re

class VectorStore:
    """Class for managing document vectors using ChromaDB."""
    
    def __init__(self, collection_name: str = "documents"):
        """
        Initialize the vector store.
        
        Args:
            collection_name: Name of the ChromaDB collection
        """
        self.client = chromadb.Client(Settings(
            allow_reset=True,
            is_persistent=True
        ))
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Cache for document names
        self._document_names = set()
    
    def add_document(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a document to the vector store.
        
        Args:
            text: Document text
            metadata: Optional metadata for the document
        """
        if metadata and 'source' in metadata:
            self._document_names.add(metadata['source'])
            
        # Generate a unique ID for the document
        doc_id = str(hash(text))
        
        # Add the document to the collection
        self.collection.add(
            documents=[text],
            metadatas=[metadata or {}],
            ids=[doc_id]
        )
    
    def search(self, query: str, top_k: int = 5, search_type: str = "content") -> List[Dict[str, Any]]:
        """
        Search for documents by content or filename.
        
        Args:
            query: Search query
            top_k: Number of results to return
            search_type: Type of search ("content" or "filename")
            
        Returns:
            List of documents with their metadata and similarity scores
        """
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
                            'content': doc,
                            'metadata': metadata,
                            'similarity': 1.0  # Perfect match for filename search
                        })
            
            # Sort by filename similarity and limit results
            matching_docs.sort(key=lambda x: x['metadata']['source'])
            return matching_docs[:top_k]
        else:
            # Semantic search for content
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            # Format results
            formatted_results = []
            if results['documents']:
                for doc, metadata, distance in zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                ):
                    formatted_results.append({
                        'content': doc,
                        'metadata': metadata,
                        'similarity': 1 - distance  # Convert distance to similarity score
                    })
            
            return formatted_results
    
    def get_document_names(self) -> List[str]:
        """Get list of all document names in the store."""
        return sorted(list(self._document_names))
    
    def clear(self) -> None:
        """Clear all documents from the store."""
        # Get all documents to get their IDs
        all_docs = self.collection.get()
        
        if all_docs and all_docs['ids']:
            # Delete all documents by their IDs
            self.collection.delete(ids=all_docs['ids'])
            
        # Clear the document names cache
        self._document_names.clear() 