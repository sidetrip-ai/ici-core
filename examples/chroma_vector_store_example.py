#!/usr/bin/env python3
"""
Example script demonstrating how to use the ChromaDB vector store.

This script shows how to:
1. Initialize a ChromaDBStore using config.yaml
2. Add documents with vectors to the store
3. Search for similar documents using a query vector
4. Use metadata filtering in searches
5. Delete documents and check counts

Usage:
    1. Create a config.yaml file with vector store settings
    2. Run the script

Example config.yaml:
```yaml
vector_store:
  type: "chroma"
  collection_name: "example_collection"
  persist_directory: "./data/chroma_db"
```
"""

import os
import sys
import json
import asyncio
import numpy as np
from datetime import datetime
from typing import Dict, List, Any

from ici.adapters.vector_stores.chroma import ChromaDBStore
from ici.adapters.loggers import StructuredLogger
from ici.core.exceptions import VectorStoreError


# Setup logging
logger = StructuredLogger(name="example.vector_store")


def pretty_print_json(data, title=None):
    """Print data as formatted JSON with optional title."""
    if title:
        print(f"\n{title}")
        print("=" * len(title))
    print(json.dumps(data, indent=2))
    print()


def generate_sample_embeddings(n_samples=5, dimension=384):
    """Generate random embeddings for demonstration purposes."""
    # In a real application, these would come from an embedding model
    vectors = []
    for _ in range(n_samples):
        # Generate random vector and normalize it
        vec = np.random.randn(dimension)
        vec = vec / np.linalg.norm(vec)
        vectors.append(vec.tolist())
    return vectors


async def main_async():
    """Run the ChromaDB vector store example asynchronously."""
    print("ChromaDB Vector Store Example")
    print("----------------------------")
    
    try:
        # Create sample config.yaml if it doesn't exist
        if not os.path.exists("config.yaml"):
            print("Creating sample config.yaml file. Please edit as needed.")
            with open("config.yaml", "w") as f:
                f.write("""# ICI Framework Configuration
vector_store:
  type: "chroma"
  collection_name: "example_collection"
  persist_directory: "./data/chroma_db"
""")
            
        # Step 1: Initialize the vector store
        print("\nInitializing ChromaDB vector store...")
        store = ChromaDBStore(logger_name="example.vector_store")
        await store.initialize()
        
        # Step 2: Check health
        health = store.healthcheck()
        pretty_print_json(health, "Health Check")
        
        if not health["healthy"]:
            print("Vector store is not healthy. Cannot proceed.")
            return 1
        
        # Step 3: Prepare sample documents and vectors
        print("\nPreparing sample documents and vectors...")
        
        documents = [
            {
                "text": "ChromaDB is a vector database designed for AI applications",
                "metadata": {"source": "docs", "category": "database", "date": "2023-01-15"}
            },
            {
                "text": "Vector databases store embeddings for similarity search",
                "metadata": {"source": "article", "category": "database", "date": "2023-02-20"}
            },
            {
                "text": "Machine learning models convert text to vector embeddings",
                "metadata": {"source": "blog", "category": "ml", "date": "2023-03-10"}
            },
            {
                "text": "Python is a popular programming language for data science",
                "metadata": {"source": "tutorial", "category": "programming", "date": "2023-04-05"}
            },
            {
                "text": "Vector similarity is measured using cosine distance or dot products",
                "metadata": {"source": "paper", "category": "math", "date": "2023-05-18"}
            }
        ]
        
        # Generate sample embeddings (normally from an embedding model)
        vectors = generate_sample_embeddings(len(documents))
        
        # Step 4: Add documents to the vector store
        print(f"\nAdding {len(documents)} documents to vector store...")
        document_ids = store.add_documents(documents, vectors)
        print(f"Added documents with IDs: {document_ids}")
        
        # Step 5: Count documents
        total_count = store.count()
        print(f"\nTotal documents in store: {total_count}")
        
        # Count with filter
        db_count = store.count(filters={"category": "database"})
        print(f"Documents with category 'database': {db_count}")
        
        # Step 6: Search for similar documents
        print("\nSearching for documents similar to 'database' concept...")
        
        # Create a query vector (in practice, this would come from an embedding model)
        # We'll just use one of our existing vectors modified slightly for demo
        query_vector = vectors[0].copy()
        # Add some random noise to make it different but similar
        query_vector = [v + 0.1 * np.random.randn() for v in query_vector]
        
        # Search without filters
        results = store.search(query_vector=query_vector, num_results=3)
        pretty_print_json(results, "Search Results (No Filter)")
        
        # Search with metadata filter
        filtered_results = store.search(
            query_vector=query_vector,
            num_results=3,
            filters={"source": "docs"}
        )
        pretty_print_json(filtered_results, "Search Results (Filtered by source='docs')")
        
        # Step 7: Delete documents
        print("\nDeleting a document by ID...")
        delete_id = document_ids[0]
        deleted_count = store.delete(document_ids=[delete_id])
        print(f"Deleted {deleted_count} document(s) with ID: {delete_id}")
        
        print("\nDeleting documents by filter...")
        deleted_by_filter = store.delete(filters={"category": "ml"})
        print(f"Deleted {deleted_by_filter} document(s) with category 'ml'")
        
        # Final count
        final_count = store.count()
        print(f"\nFinal document count: {final_count}")
        
        print("\nExample completed successfully!")
        return 0
        
    except VectorStoreError as e:
        print(f"Vector store error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


def main():
    """Run the async main function."""
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main()) 