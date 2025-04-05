#!/usr/bin/env python
"""
Memory Finder

A web interface for searching through your conversation history using the
advanced vector query capabilities. Features include keyword highlighting,
date filtering, and conversation context viewing.
"""

import os
import asyncio
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
from typing import List, Dict, Any, Optional

from ici.adapters.vector_stores.chroma import ChromaDBStore
from ici.adapters.embedders.sentence_transformer import SentenceTransformerEmbedder
from ici.utils.config import load_config
from ici.utils.datetime_utils import from_isoformat, ensure_tz_aware
from ici.adapters.loggers import StructuredLogger

# Set up logger
logger = StructuredLogger(name="memory_finder")

# Initialize session state for storing components
if 'vector_store' not in st.session_state:
    st.session_state.vector_store = None
if 'embedder' not in st.session_state:
    st.session_state.embedder = None

async def initialize_components():
    """Initialize the vector store and embedder components."""
    # Initialize vector store
    vector_store = ChromaDBStore()
    await vector_store.initialize()
    
    # Initialize embedder
    embedder = SentenceTransformerEmbedder()
    await embedder.initialize()
    
    return vector_store, embedder

async def generate_query_embedding(embedder, query: str) -> List[float]:
    """Generate an embedding for the query text."""
    embedding, _ = await embedder.embed(query)
    return embedding

def build_filters(search_params) -> Dict[str, Any]:
    """Build filter dictionary based on search parameters."""
    filters = {}
    
    # Parse conversation filter
    if search_params.get('conversation_id'):
        filters["conversation_id"] = search_params['conversation_id']
    
    # Parse sender filter
    if search_params.get('sender'):
        filters["sender"] = search_params['sender']
    
    # Parse outgoing filter
    if search_params.get('outgoing') is not None:
        filters["outgoing"] = search_params['outgoing']
    
    return filters if filters else None

def post_filter_results(results: List[Dict[str, Any]], search_params) -> List[Dict[str, Any]]:
    """Apply additional filters that ChromaDB doesn't support natively."""
    filtered_results = results.copy()
    
    # Apply date filtering
    if search_params.get('date_from') or search_params.get('date_to'):
        date_filtered = []
        for result in filtered_results:
            metadata = result.get('metadata', {})
            msg_date = metadata.get('date')
            
            if not msg_date:
                continue
                
            try:
                msg_datetime = from_isoformat(msg_date)
                
                # Apply date_from filter
                if search_params.get('date_from'):
                    date_from = search_params['date_from']
                    date_from = ensure_tz_aware(date_from)
                    if msg_datetime < date_from:
                        continue
                
                # Apply date_to filter
                if search_params.get('date_to'):
                    date_to = search_params['date_to']
                    date_to = ensure_tz_aware(date_to)
                    if msg_datetime > date_to:
                        continue
                
                date_filtered.append(result)
            except (ValueError, TypeError):
                # Skip messages with invalid dates
                continue
        
        filtered_results = date_filtered
    
    return filtered_results

def highlight_text(text, query_terms):
    """Highlight query terms in the text."""
    highlighted_text = text
    for term in query_terms:
        if term.strip():
            pattern = re.compile(re.escape(term.strip()), re.IGNORECASE)
            highlighted_text = pattern.sub(f"<mark>{term}</mark>", highlighted_text)
    return highlighted_text

def get_conversation_context(vector_store, message_id: str, window: int = 3):
    """Get conversation context around a specific message."""
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
        num_results=100,  # Get more messages for better context
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

async def perform_keyword_search(search_params):
    """Perform keyword-based search using the vector store's keyword capabilities."""
    # Get components from session state
    vector_store = st.session_state.vector_store
    
    # Build filters
    filters = build_filters(search_params)
    
    # Extract keywords from query
    keywords = search_params['query'].split()
    
    # Log the search action
    logger.info({
        "action": "KEYWORD_SEARCH",
        "message": f"Searching for keywords: '{search_params['query']}'",
        "data": {
            "top_k": search_params['top_k'],
            "filters": filters,
            "keywords": keywords
        }
    })
    
    # Get all messages that match the filters
    # We'll use a dummy vector since we're doing keyword search
    all_messages = vector_store.search(
        query_vector=[0] * 384,  # Dummy vector
        num_results=1000,  # Get more results for keyword filtering
        filters=filters
    )
    
    # Apply post-filtering for complex conditions (date, etc.)
    filtered_messages = post_filter_results(all_messages, search_params)
    
    # Perform keyword matching
    keyword_results = []
    for message in filtered_messages:
        text = message.get('text', '').lower()
        # Check if any keyword is in the message text
        if any(keyword.lower() in text for keyword in keywords if keyword.strip()):
            # Add score based on number of keyword matches
            score = sum(1 for keyword in keywords if keyword.strip() and keyword.lower() in text)
            message['score'] = score
            keyword_results.append(message)
    
    # Sort by score (number of keyword matches)
    keyword_results.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # Limit to top_k results
    keyword_results = keyword_results[:search_params['top_k']]
    
    # Highlight query terms in results
    for result in keyword_results:
        if 'text' in result:
            result['highlighted_text'] = highlight_text(result['text'], keywords)
    
    return keyword_results

async def perform_semantic_search(search_params):
    """Perform semantic search based on the provided parameters."""
    # Get components from session state
    vector_store = st.session_state.vector_store
    embedder = st.session_state.embedder
    
    # Build filters
    filters = build_filters(search_params)
    
    # Generate embedding for the query
    query_embedding = await generate_query_embedding(embedder, search_params['query'])
    
    # Search vector store
    logger.info({
        "action": "SEMANTIC_SEARCH",
        "message": f"Searching for: '{search_params['query']}'",
        "data": {
            "top_k": search_params['top_k'],
            "filters": filters
        }
    })
    
    results = vector_store.search(
        query_vector=query_embedding,
        num_results=search_params['top_k'],
        filters=filters
    )
    
    # Apply post-filtering for complex conditions
    results = post_filter_results(results, search_params)
    
    # Highlight query terms in results
    query_terms = search_params['query'].split()
    for result in results:
        if 'text' in result:
            result['highlighted_text'] = highlight_text(result['text'], query_terms)
    
    return results

async def perform_search(search_params):
    """Perform search based on the provided parameters.
    Combines both semantic and keyword search for better results."""
    search_type = search_params.get('search_type', 'combined')
    
    if search_type == 'keyword':
        # Keyword search only
        return await perform_keyword_search(search_params)
    elif search_type == 'semantic':
        # Semantic search only
        return await perform_semantic_search(search_params)
    else:
        # Combined search (default)
        semantic_results = await perform_semantic_search(search_params)
        keyword_results = await perform_keyword_search(search_params)
        
        # Combine results, removing duplicates
        combined_results = semantic_results.copy()
        seen_ids = {result.get('id') for result in combined_results}
        
        for result in keyword_results:
            if result.get('id') not in seen_ids:
                combined_results.append(result)
                seen_ids.add(result.get('id'))
        
        # Sort by score
        combined_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # Limit to top_k results
        return combined_results[:search_params['top_k']]
    
    return results

def display_results(results, query_terms):
    """Display search results in the Streamlit UI."""
    if not results:
        st.warning("No results found matching your search criteria.")
        return
    
    st.success(f"Found {len(results)} results")
    
    for i, result in enumerate(results, 1):
        with st.expander(f"Result {i}: {result.get('text', '')[:100]}..."):
            # Display metadata
            metadata = result.get('metadata', {})
            
            # Create two columns for metadata display
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Message Details:**")
                st.write(f"ID: {result.get('id', 'N/A')}")
                st.write(f"Score: {result.get('score', 0):.4f}")
                if 'date' in metadata:
                    st.write(f"Date: {metadata['date']}")
                if 'sender' in metadata:
                    st.write(f"Sender: {metadata['sender']}")
            
            with col2:
                st.write("**Conversation Details:**")
                if 'conversation_id' in metadata:
                    st.write(f"Conversation: {metadata['conversation_id']}")
                if 'outgoing' in metadata:
                    st.write(f"Outgoing: {'Yes' if metadata['outgoing'] else 'No'}")
                for key, value in metadata.items():
                    if key not in ['date', 'sender', 'conversation_id', 'outgoing', 'text']:
                        st.write(f"{key}: {value}")
            
            # Display content with highlighting
            st.markdown("**Content:**")
            if 'highlighted_text' in result:
                st.markdown(result['highlighted_text'], unsafe_allow_html=True)
            else:
                st.write(result.get('text', 'No content available'))
            
            # Add button to view conversation context
            if st.button(f"View Conversation Context", key=f"context_{result.get('id')}"):
                context_messages = get_conversation_context(
                    st.session_state.vector_store,
                    result.get('id'),
                    window=5  # Show more context in the UI
                )
                
                if context_messages:
                    st.markdown("### Conversation Context")
                    for msg in context_messages:
                        is_current = msg.get('id') == result.get('id')
                        msg_metadata = msg.get('metadata', {})
                        
                        # Format the message with different styling for the current message
                        if is_current:
                            st.markdown(f"""
                            <div style="background-color: #e6f7ff; padding: 10px; border-radius: 5px; margin: 5px 0;">
                                <strong>{msg_metadata.get('sender', 'Unknown')} ({msg_metadata.get('date', 'Unknown date')}):</strong><br>
                                {highlight_text(msg.get('text', ''), query_terms)}
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                            <div style="padding: 10px; border-radius: 5px; margin: 5px 0; border: 1px solid #ddd;">
                                <strong>{msg_metadata.get('sender', 'Unknown')} ({msg_metadata.get('date', 'Unknown date')}):</strong><br>
                                {msg.get('text', '')}
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("No conversation context available for this message.")

def main():
    st.set_page_config(
        page_title="Memory Finder",
        page_icon="🔍",
        layout="wide"
    )
    
    st.title("Memory Finder")
    st.markdown("""
    Search through your conversation history with advanced filtering and highlighting.
    Find those important moments and see them in context!
    """)
    
    # Initialize components if not already done
    if st.session_state.vector_store is None or st.session_state.embedder is None:
        with st.spinner("Initializing components..."):
            # Ensure ICI_CONFIG_PATH is set
            if not os.environ.get("ICI_CONFIG_PATH"):
                os.environ["ICI_CONFIG_PATH"] = os.path.join(os.getcwd(), "config.yaml")
            
            # Run async initialization
            vector_store, embedder = asyncio.run(initialize_components())
            st.session_state.vector_store = vector_store
            st.session_state.embedder = embedder
        st.success("Components initialized!")
    
    # Create search form
    with st.form("search_form"):
        st.subheader("Search Parameters")
        
        # Basic search
        query = st.text_input("Search Query", help="Enter keywords or phrases to search for")
        top_k = st.slider("Number of Results", min_value=1, max_value=50, value=10)
        
        # Advanced filters in an expander
        with st.expander("Advanced Filters"):
            col1, col2 = st.columns(2)
            
            with col1:
                conversation_id = st.text_input("Conversation ID", help="Filter by specific conversation")
                sender = st.text_input("Sender", help="Filter by sender name/ID")
                outgoing = st.radio("Message Direction", 
                                    options=[None, True, False], 
                                    format_func=lambda x: "Any" if x is None else ("Outgoing" if x else "Incoming"),
                                    index=0)
            
            with col2:
                date_from = st.date_input("Date From", value=None, help="Filter messages from this date")
                date_to = st.date_input("Date To", value=None, help="Filter messages until this date")
                
                # Convert date inputs to datetime objects if they're not None
                if date_from:
                    date_from = datetime.combine(date_from, datetime.min.time())
                if date_to:
                    date_to = datetime.combine(date_to, datetime.max.time())
        
        # Submit button
        search_button = st.form_submit_button("Search")
    
    # Handle search
    if search_button and query:
        # Prepare search parameters
        search_params = {
            'query': query,
            'top_k': top_k,
            'conversation_id': conversation_id if 'conversation_id' in locals() and conversation_id else None,
            'sender': sender if 'sender' in locals() and sender else None,
            'outgoing': outgoing if 'outgoing' in locals() and outgoing is not None else None,
            'date_from': date_from if 'date_from' in locals() and date_from else None,
            'date_to': date_to if 'date_to' in locals() and date_to else None,
        }
        
        # Perform search
        with st.spinner("Searching..."):
            results = asyncio.run(perform_search(search_params))
        
        # Display results
        display_results(results, query.split())
    
    # Show some tips at the bottom
    st.markdown("---")
    st.markdown("""
    ### Tips
    - Use specific keywords for better results
    - Filter by date range to narrow down your search
    - Click "View Conversation Context" to see the message in its original conversation
    - The search uses semantic matching, so you can search for concepts, not just exact words
    """)

if __name__ == "__main__":
    main()