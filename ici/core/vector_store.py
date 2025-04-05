from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings

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
    
    def add_document(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a document to the vector store.
        
        Args:
            text: Document text
            metadata: Optional metadata for the document
        """
        # Generate a unique ID for the document
        doc_id = str(hash(text))
        
        # Add the document to the collection
        self.collection.add(
            documents=[text],
            metadatas=[metadata or {}],
            ids=[doc_id]
        )
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar documents.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of documents with their metadata and similarity scores
        """
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