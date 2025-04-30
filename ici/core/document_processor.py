from pathlib import Path
from typing import Optional, Dict, Any, List
from ici.utils.text_processor import TextPreprocessor
from ici.core.vector_store import VectorStore
from ici.core.exceptions import VectorStoreError

class DocumentProcessor:
    """Class for processing documents and storing them in the vector store."""
    
    def __init__(self, text_processor: TextPreprocessor, vector_store: VectorStore):
        """
        Initialize the document processor.
        
        Args:
            text_processor: TextPreprocessor instance for text preprocessing
            vector_store: VectorStore instance for storing document vectors
        """
        self.text_processor = text_processor
        self.vector_store = vector_store
    
    def process_document(self, file_path: str) -> bool:
        """
        Process a document and store it in the vector store.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            # Read and preprocess the document
            processed_text = self.text_processor.process_file(file_path)
            
            if not processed_text:
                print(f"No text content extracted from {file_path}")
                return False
            
            # Create document with metadata
            document = {
                'text': processed_text,
                'metadata': {
                    'source': Path(file_path).name,
                    'file_path': str(file_path),
                    'file_type': Path(file_path).suffix.lower()[1:]  # Remove the dot from extension
                }
            }
            
            # Store the document
            self.vector_store.store_documents([document])
            
            return True
            
        except Exception as e:
            print(f"Error processing document {file_path}: {e}")
            return False
            
    def process_documents(self, file_paths: List[str]) -> Dict[str, bool]:
        """
        Process multiple documents in batch.
        
        Args:
            file_paths: List of paths to document files
            
        Returns:
            Dictionary mapping file paths to success status
        """
        results = {}
        for file_path in file_paths:
            results[file_path] = self.process_document(file_path)
        return results 