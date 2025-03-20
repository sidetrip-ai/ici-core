#!/usr/bin/env python
"""
Example script that demonstrates how to query the ChromaDB vector store.

This script:
1. Loads the configuration from config.yaml
2. Initializes the ChromaDB vector store and the sentence transformer embedder
3. Queries the vector store using a text query
4. Displays the results
"""

import os
import asyncio
import argparse
from typing import List, Dict, Any

from ici.adapters.vector_stores.chroma import ChromaDBStore
from ici.adapters.embedders.sentence_transformer import SentenceTransformerEmbedder
from ici.utils.config import load_config
from ici.adapters.loggers import StructuredLogger

# Set up logger
logger = StructuredLogger(name="vector_store_query")

async def query_vector_store(query: str, top_k: int = 5, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Query the vector store with a text query.
    
    Args:
        query: The text query to search for
        top_k: Number of results to return
        filters: Optional metadata filters to apply to the search
        
    Returns:
        List of documents matching the query
    """
    # Initialize the vector store
    vector_store = ChromaDBStore()
    await vector_store.initialize()
    
    # Initialize the embedder
    embedder = SentenceTransformerEmbedder()
    await embedder.initialize()
    
    # Generate embedding for the query
    query_embedding, _ = await embedder.embed(query)
    
    # Search the vector store
    logger.info({
        "action": "QUERY_VECTOR_STORE",
        "message": f"Searching for: '{query}'",
        "data": {"top_k": top_k, "filters": filters}
    })
    
    results = vector_store.search(
        query_vector=query_embedding,
        num_results=top_k,
        filters=filters
    )
    
    logger.info({
        "action": "QUERY_RESULTS",
        "message": f"Found {len(results)} results",
        "data": {"result_count": len(results)}
    })
    
    return results

def format_results(results: List[Dict[str, Any]]) -> None:
    """
    Format and print the search results.
    
    Args:
        results: The search results from the vector store
    """
    print(f"\n{'='*80}\n{'SEARCH RESULTS':^80}\n{'='*80}")
    
    for i, result in enumerate(results, 1):
        print(f"\n--- Result {i} ---")
        print(f"Document ID: {result.get('id', 'N/A')}")
        print(f"Score: {result.get('score', 0):.4f}")
        
        # Print metadata
        print("\nMetadata:")
        metadata = result.get('metadata', {})
        for key, value in metadata.items():
            if key != 'text':  # Avoid duplicating the text content
                print(f"  {key}: {value}")
        
        # Print the text content
        print("\nContent:")
        print(f"{result.get('text', 'No content available')[:500]}...")
        
        if i < len(results):
            print("\n" + "-"*80)
    
    print("\n" + "="*80)

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Query the ChromaDB vector store")
    parser.add_argument("query", help="The text query to search for")
    parser.add_argument("--top_k", type=int, default=5, help="Number of results to return")
    parser.add_argument("--conversation_id", help="Filter by conversation ID")
    parser.add_argument("--date_from", help="Filter by date (format: YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    # Prepare filters based on command line arguments
    filters = {}
    if args.conversation_id:
        filters["conversation_id"] = args.conversation_id
    
    # Execute the query
    results = await query_vector_store(args.query, args.top_k, filters if filters else None)
    
    # Format and display the results
    format_results(results)

if __name__ == "__main__":
    # Ensure ICI_CONFIG_PATH is set to use the config.yaml in the current directory
    if not os.environ.get("ICI_CONFIG_PATH"):
        os.environ["ICI_CONFIG_PATH"] = os.path.join(os.getcwd(), "config.yaml")
    
    # Run the main async function
    asyncio.run(main()) 