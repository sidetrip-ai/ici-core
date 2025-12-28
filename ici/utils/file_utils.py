from pathlib import Path
from typing import List, Optional, Union
from ..core.scraper import scrape_file
from ..adapters.vector_store import VectorStoreAdapter

def ingest_file(file_path: Union[str, Path], vector_store: Optional[VectorStoreAdapter] = None) -> str:
    """
    Ingest a file into the vector store.
    
    Args:
        file_path: Path to the file to ingest
        vector_store: Optional VectorStoreAdapter instance. If not provided, a new one will be created.
        
    Returns:
        str: The document ID in the vector store
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If no scraper is available for the file type
    """
    # Create vector store if not provided
    if vector_store is None:
        vector_store = VectorStoreAdapter(use_persistent=True)
    
    # Scrape the file content
    content, metadata = scrape_file(file_path)
    
    # Add to vector store
    document_id = vector_store.add_document(content, metadata)
    
    return document_id

def ingest_directory(
    directory_path: Union[str, Path],
    recursive: bool = True,
    file_extensions: Optional[List[str]] = None,
    vector_store: Optional[VectorStoreAdapter] = None
) -> List[str]:
    """
    Ingest all files in a directory into the vector store.
    
    Args:
        directory_path: Path to the directory
        recursive: Whether to recursively process subdirectories
        file_extensions: Optional list of file extensions to process (e.g. ['.txt', '.md'])
        vector_store: Optional VectorStoreAdapter instance. If not provided, a new one will be created.
        
    Returns:
        List[str]: List of document IDs added to the vector store
    """
    directory = Path(directory_path)
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory_path}")
    
    # Create single vector store instance for all files if not provided
    if vector_store is None:
        vector_store = VectorStoreAdapter(use_persistent=True)
    
    document_ids = []
    pattern = "**/*" if recursive else "*"
    
    for file_path in directory.glob(pattern):
        if file_path.is_file():
            if file_extensions is None or file_path.suffix.lower() in file_extensions:
                try:
                    doc_id = ingest_file(file_path, vector_store)
                    document_ids.append(doc_id)
                except (ValueError, FileNotFoundError) as e:
                    # Log error but continue processing other files
                    print(f"Error processing {file_path}: {str(e)}")
    
    return document_ids 