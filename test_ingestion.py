from ici.utils.file_utils import ingest_directory
from ici.adapters.vector_store import VectorStoreAdapter

def main():
    print("Testing file ingestion and vector search functionality...")
    
    # Create vector store with persistent storage
    vector_store = VectorStoreAdapter(use_persistent=True)
    
    # Ingest all text files from the test directory
    print("\n1. Ingesting files from test_data directory...")
    document_ids = ingest_directory("test_data", file_extensions=[".txt"], vector_store=vector_store)
    print(f"Successfully ingested {len(document_ids)} documents")
    
    # Test different search queries
    test_queries = [
        "What is Python used for?",
        "Tell me about machine learning",
        "What technologies are used in web development?"
    ]
    
    print("\n2. Testing search functionality...")
    for query in test_queries:
        print(f"\nQuery: {query}")
        results = vector_store.search_similar(query, n_results=2)
        
        # Print results
        if results["documents"]:
            for i in range(len(results["documents"])):
                print(f"\nResult {i + 1}:")
                print(f"Document: {results['metadatas'][i]['file_path']}")
                print(f"Content: {results['documents'][i]}")
        else:
            print("No results found.")

if __name__ == "__main__":
    main() 