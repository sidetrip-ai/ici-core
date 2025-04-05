from pathlib import Path
from typing import Optional
from ici.utils.text_processor import TextPreprocessor
from ici.core.vector_store import VectorStore

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
            
            # Store the processed text in the vector store
            self.vector_store.add_document(
                text=processed_text,
                metadata={"source": Path(file_path).name}
            )
            
            return True
            
        except Exception as e:
            print(f"Error processing document {file_path}: {e}")
            return False 