#!/usr/bin/env python
"""
Advanced Vector Store Query Tool

This script provides an advanced interface for querying the ChromaDB vector store
with sophisticated filtering options, result formatting, and export capabilities.

Features:
- Full text semantic search with embedding
- Metadata filtering (conversation, date range, sender, etc.)
- Result formatting options (JSON, text)
- Export to file
- Conversation context retrieval
"""

import os
import asyncio
import argparse
import json
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union

from ici.adapters.vector_stores.chroma import ChromaDBStore
from ici.adapters.embedders.sentence_transformer import SentenceTransformerEmbedder
from ici.utils.config import load_config
from ici.utils.datetime_utils import from_isoformat, ensure_tz_aware
from ici.adapters.loggers import StructuredLogger

# Set up logger
logger = StructuredLogger(name="advanced_vector_query")

async def initialize_components():
    """
    Initialize the vector store and embedder components.
    
    Returns:
        Tuple of (vector_store, embedder)
    """
    # Initialize vector store
    vector_store = ChromaDBStore()
    await vector_store.initialize()
    
    # Initialize embedder
    embedder = SentenceTransformerEmbedder()
    await embedder.initialize()
    
    return vector_store, embedder

async def generate_query_embedding(embedder, query: str) -> List[float]:
    """
    Generate an embedding for the query text.
    
    Args:
        embedder: The initialized embedder
        query: Text to convert to embedding
        
    Returns:
        The embedding vector
    """
    embedding, _ = await embedder.embed(query)
    return embedding

def build_filters(args) -> Dict[str, Any]:
    """
    Build filter dictionary based on command line arguments.
    
    Args:
        args: Command line arguments
        
    Returns:
        Dictionary of metadata filters for ChromaDB
    """
    filters = {}
    
    # Parse conversation filter
    if args.conversation_id:
        filters["conversation_id"] = args.conversation_id
    
    # Parse sender filter
    if args.sender:
        filters["sender"] = args.sender
    
    # Parse outgoing filter (messages sent by the user)
    if args.outgoing is not None:
        filters["outgoing"] = args.outgoing
    
    # Parse date range filters
    if args.date_from or args.date_to:
        # ChromaDB doesn't support range queries directly, so we'll filter results after
        pass
    
    return filters if filters else None

def post_filter_results(results: List[Dict[str, Any]], args) -> List[Dict[str, Any]]:
    """
    Apply additional filters that ChromaDB doesn't support natively.
    
    Args:
        results: Results from the vector store
        args: Command line arguments
        
    Returns:
        Filtered results
    """
    filtered_results = results.copy()
    
    # Apply date filtering
    if args.date_from or args.date_to:
        date_filtered = []
        for result in filtered_results:
            metadata = result.get('metadata', {})
            msg_date = metadata.get('date')
            
            if not msg_date:
                continue
                
            try:
                msg_datetime = from_isoformat(msg_date)
                
                # Apply date_from filter
                if args.date_from:
                    date_from = datetime.fromisoformat(args.date_from)
                    date_from = ensure_tz_aware(date_from)
                    if msg_datetime < date_from:
                        continue
                
                # Apply date_to filter
                if args.date_to:
                    date_to = datetime.fromisoformat(args.date_to)
                    date_to = ensure_tz_aware(date_to)
                    if msg_datetime > date_to:
                        continue
                
                date_filtered.append(result)
            except (ValueError, TypeError):
                # Skip messages with invalid dates
                continue
        
        filtered_results = date_filtered
    
    return filtered_results

def get_conversation_context(vector_store: ChromaDBStore, message_id: str, window: int = 3):
    """
    Get conversation context around a specific message.
    
    Args:
        vector_store: The initialized vector store
        message_id: The ID of the message to get context for
        window: Number of messages before and after to include
        
    Returns:
        List of messages in context
    """
    # First, get the target message to find its conversation_id
    target_result = vector_store.search(
        query_vector=[0] * 384,  # Dummy vector, we'll filter by ID
        num_results=1,
        filters={"id": message_id}
    )
    
    if not target_result:
        return []
    
    # Get conversation ID and date
    conversation_id = target_result[0].get('metadata', {}).get('conversation_id')
    if not conversation_id:
        return []
    
    # Search for messages in the same conversation
    conversation_messages = vector_store.search(
        query_vector=[0] * 384,  # Dummy vector
        num_results=50,  # Get a bunch of messages to sort
        filters={"conversation_id": conversation_id}
    )
    
    # Sort by date
    try:
        conversation_messages.sort(
            key=lambda x: from_isoformat(x.get('metadata', {}).get('date', '1970-01-01T00:00:00'))
        )
    except (ValueError, TypeError):
        # If date sorting fails, return as is
        return conversation_messages
    
    # Find the position of target message
    target_idx = -1
    for i, msg in enumerate(conversation_messages):
        if msg.get('id') == message_id:
            target_idx = i
            break
    
    if target_idx == -1:
        return []
    
    # Get window of messages around target
    start_idx = max(0, target_idx - window)
    end_idx = min(len(conversation_messages), target_idx + window + 1)
    
    return conversation_messages[start_idx:end_idx]

def format_results(results: List[Dict[str, Any]], args) -> str:
    """
    Format search results according to the specified format.
    
    Args:
        results: The search results
        args: Command line arguments
        
    Returns:
        Formatted results as a string
    """
    if args.format == 'json':
        return json.dumps(results, indent=2)
    
    # Default to text format
    output = []
    output.append(f"\n{'='*80}\n{'SEARCH RESULTS':^80}\n{'='*80}")
    
    for i, result in enumerate(results, 1):
        output.append(f"\n--- Result {i} ---")
        output.append(f"Document ID: {result.get('id', 'N/A')}")
        output.append(f"Score: {result.get('score', 0):.4f}")
        
        # Format metadata
        output.append("\nMetadata:")
        metadata = result.get('metadata', {})
        for key, value in metadata.items():
            if key != 'text':  # Avoid duplicating the text content
                output.append(f"  {key}: {value}")
        
        # Format content
        output.append("\nContent:")
        content = result.get('text', 'No content available')
        if args.full_text:
            output.append(content)
        else:
            output.append(f"{content[:500]}...")
        
        # Add separator between results
        if i < len(results):
            output.append("\n" + "-"*80)
    
    output.append("\n" + "="*80)
    return "\n".join(output)

def export_results(results: List[Dict[str, Any]], args):
    """
    Export results to a file.
    
    Args:
        results: The search results
        args: Command line arguments
    """
    if not args.export:
        return
    
    export_path = args.export
    
    # Determine export format based on file extension
    format_type = export_path.split('.')[-1].lower()
    
    if format_type == 'json':
        with open(export_path, 'w') as f:
            json.dump(results, f, indent=2)
    elif format_type == 'csv':
        # Flatten the results for CSV export
        flattened = []
        for result in results:
            metadata = result.get('metadata', {})
            flat_result = {
                'id': result.get('id', ''),
                'score': result.get('score', 0),
                'text': result.get('text', ''),
            }
            flat_result.update(metadata)
            flattened.append(flat_result)
        
        if flattened:
            fieldnames = flattened[0].keys()
            with open(export_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(flattened)
    else:
        # Default to text format
        with open(export_path, 'w') as f:
            f.write(format_results(results, args))
    
    logger.info({
        "action": "EXPORT_RESULTS",
        "message": f"Exported results to {export_path}",
        "data": {"path": export_path, "format": format_type}
    })

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Advanced Vector Store Query Tool")
    
    # Search parameters
    parser.add_argument("query", help="The text query to search for", nargs='?', default=None)
    parser.add_argument("--top_k", type=int, default=5, help="Number of results to return")
    parser.add_argument("--list_all", action="store_true", help="List all documents instead of searching")
    
    # Filters
    parser.add_argument("--conversation_id", help="Filter by conversation ID")
    parser.add_argument("--sender", help="Filter by sender (user ID)")
    parser.add_argument("--outgoing", type=bool, help="Filter by outgoing messages (True/False)")
    parser.add_argument("--date_from", help="Filter by date from (format: YYYY-MM-DD)")
    parser.add_argument("--date_to", help="Filter by date to (format: YYYY-MM-DD)")
    
    # Context options
    parser.add_argument("--message_id", help="Get conversation context around a message ID")
    parser.add_argument("--context_window", type=int, default=3, help="Number of messages before/after for context")
    
    # Output options
    parser.add_argument("--format", choices=['text', 'json'], default='text', help="Output format")
    parser.add_argument("--full_text", action="store_true", help="Show full text content")
    parser.add_argument("--export", help="Export results to file (format determined by extension)")
    
    args = parser.parse_args()
    
    # Initialize components
    vector_store, embedder = await initialize_components()
    
    # Process the request based on mode
    if args.list_all:
        # List all documents (limited to top_k)
        # Create a dummy vector filled with zeros
        dummy_vector = [0] * 384  # Length of the sentence transformer embeddings
        results = vector_store.search(
            query_vector=dummy_vector,
            num_results=args.top_k or 100
        )
    elif args.message_id:
        # Get conversation context
        results = get_conversation_context(
            vector_store=vector_store,
            message_id=args.message_id,
            window=args.context_window
        )
    elif args.query:
        # Normal search mode
        # Build filters based on arguments
        filters = build_filters(args)
        
        # Generate embedding for the query
        query_embedding = await generate_query_embedding(embedder, args.query)
        
        # Search vector store
        logger.info({
            "action": "QUERY_VECTOR_STORE",
            "message": f"Searching for: '{args.query}'",
            "data": {
                "top_k": args.top_k,
                "filters": filters
            }
        })
        
        results = vector_store.search(
            query_vector=query_embedding,
            num_results=args.top_k,
            filters=filters
        )
        
        # Apply post-filtering for complex conditions
        results = post_filter_results(results, args)
    else:
        parser.print_help()
        return
    
    # Format results
    formatted_output = format_results(results, args)
    print(formatted_output)
    
    # Export if requested
    if args.export:
        export_results(results, args)
    
    logger.info({
        "action": "QUERY_COMPLETE",
        "message": f"Found {len(results)} results",
        "data": {"result_count": len(results)}
    })

if __name__ == "__main__":
    # Ensure ICI_CONFIG_PATH is set to use the config.yaml in the current directory
    if not os.environ.get("ICI_CONFIG_PATH"):
        os.environ["ICI_CONFIG_PATH"] = os.path.join(os.getcwd(), "config.yaml")
    
    # Run the main async function
    asyncio.run(main()) 