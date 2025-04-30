from pathlib import Path
from typing import List, Optional, Union, Dict, Any
import chromadb
from chromadb.config import Settings
import yaml
from ..core.scraper import DocumentMetadata

class VectorStoreAdapter:
    """Adapter for managing document storage in ChromaDB."""
    
    def __init__(self, config_path: str = "config.yaml", use_persistent: bool = False):
        self.config = self._load_config(config_path)
        self.client = self._initialize_client(use_persistent)
        self.collection = self._get_collection()
        
    def _load_config(self, config_path: str) -> dict:
        """Load configuration from yaml file."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
        
    def _initialize_client(self, use_persistent: bool) -> chromadb.Client:
        """Initialize ChromaDB client."""
        if use_persistent:
            vector_config = self.config["vector_stores"]["chroma"]
            persist_directory = vector_config["persist_directory"]
            return chromadb.Client(Settings(
                persist_directory=persist_directory,
                is_persistent=True
            ))
        else:
            # Use in-memory client for testing
            return chromadb.Client()
        
    def _get_collection(self) -> chromadb.Collection:
        """Get or create the collection for storing documents."""
        vector_config = self.config["vector_stores"]["chroma"]
        collection_name = vector_config["collection_name"]
        
        try:
            collection = self.client.get_collection(collection_name)
        except ValueError:
            collection = self.client.create_collection(collection_name)
            
        return collection
        
    def add_document(self, content: str, metadata: DocumentMetadata, document_id: Optional[str] = None) -> str:
        """
        Add a document to the vector store.
        
        Args:
            content: The text content to store
            metadata: Document metadata
            document_id: Optional unique identifier for the document
            
        Returns:
            str: The document ID
        """
        if document_id is None:
            document_id = str(hash(content + metadata.file_path))
            
        self.collection.add(
            documents=[content],
            metadatas=[{
                "source": metadata.source,
                "file_path": metadata.file_path,
                "file_type": metadata.file_type
            }],
            ids=[document_id]
        )
        
        return document_id
        
    def search_similar(self, query: str, n_results: int = 5) -> Dict[str, List[Any]]:
        """
        Search for similar documents.
        
        Args:
            query: The search query
            n_results: Number of results to return
            
        Returns:
            Dict with keys:
                - documents: List of document contents
                - metadatas: List of document metadata dictionaries
                - distances: List of similarity scores
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            include=["metadatas", "documents", "distances"]
        )
        
        # Flatten the nested lists in the results
        return {
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else []
        }
        
    def delete_document(self, document_id: str) -> None:
        """Delete a document from the vector store."""
        self.collection.delete(ids=[document_id])
        
    def get_document(self, document_id: str) -> Optional[dict]:
        """Get a document by its ID."""
        try:
            result = self.collection.get(ids=[document_id])
            if result["documents"]:
                return {
                    "content": result["documents"][0],
                    "metadata": result["metadatas"][0]
                }
        except ValueError:
            return None 