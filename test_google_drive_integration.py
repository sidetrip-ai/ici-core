import os
from pathlib import Path
from ici.adapters.google_drive import GoogleDriveAdapter
from ici.core.document_processor import DocumentProcessor
from ici.core.vector_store import VectorStore
from ici.utils.text_processor import TextPreprocessor

def test_google_drive_integration():
    """Test the integration of Google Drive with our document processing system."""
    
    # Initialize components
    drive_adapter = GoogleDriveAdapter()
    text_processor = TextPreprocessor()
    vector_store = VectorStore()
    doc_processor = DocumentProcessor(text_processor=text_processor, vector_store=vector_store)
    
    # Supported file types
    file_types = ['.txt', '.pdf', '.docx']
    
    print("Fetching files from Google Drive...")
    # You can specify a folder_id to fetch files from a specific folder
    downloaded_files = drive_adapter.process_files(file_types=file_types)
    
    if not downloaded_files:
        print("No files found in Google Drive matching the specified types.")
        return
    
    print(f"\nFound {len(downloaded_files)} files:")
    for file_path in downloaded_files:
        print(f"- {file_path.name}")
    
    print("\nProcessing and ingesting files...")
    for file_path in downloaded_files:
        try:
            doc_processor.process_document(str(file_path))
            print(f"Successfully processed: {file_path.name}")
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")
    
    print("\nTesting search functionality...")
    # Example search queries
    test_queries = [
        "artificial intelligence",
        "machine learning",
        "data science",
        "neural networks"
    ]
    
    for query in test_queries:
        print(f"\nSearching for: '{query}'")
        results = vector_store.search(query, top_k=2)
        
        if results:
            print("Top results:")
            for i, result in enumerate(results, 1):
                print(f"\n{i}. Document: {result['metadata']['source']}")
                print(f"   Content: {result['content'][:200]}...")
        else:
            print("No results found.")
    
    print("\nCleanup: Removing temporary files...")
    for file_path in downloaded_files:
        try:
            os.remove(file_path)
            print(f"Removed: {file_path.name}")
        except Exception as e:
            print(f"Error removing {file_path.name}: {e}")

if __name__ == "__main__":
    test_google_drive_integration() 