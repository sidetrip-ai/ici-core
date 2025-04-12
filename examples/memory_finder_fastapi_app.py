#!/usr/bin/env python
"""
Memory Finder FastAPI App

A FastAPI implementation of the memory finder application with REST API endpoints
for searching through conversation history using advanced vector query capabilities.
Features include keyword highlighting, date filtering, and conversation context viewing.
"""

import os
import asyncio
import pandas as pd
from datetime import datetime, timedelta
import re
from typing import List, Dict, Any, Optional, Union
from fastapi import FastAPI, Query, HTTPException, Request, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv

# Import ICI components
try:
    from ici.adapters.vector_stores.chroma import ChromaDBStore
    from ici.adapters.embedders.sentence_transformer import SentenceTransformerEmbedder
    from ici.utils.config import load_config
    from ici.utils.datetime_utils import from_isoformat, ensure_tz_aware
    from ici.adapters.loggers import StructuredLogger
except ImportError as e:
    raise ImportError(f"Failed to import ICI components: {e}. Make sure the ici-core package is installed.")

# Set up logger
logger = StructuredLogger(name="memory_finder")

# Create FastAPI app
app = FastAPI(
    title="Memory Finder API",
    description="API for searching through conversation history using vector queries",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directory for templates if it doesn't exist
os.makedirs(os.path.join(os.path.dirname(__file__), "templates"), exist_ok=True)

# Set up templates
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# Set up static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Global components
vector_store = None
embedder = None

# Pydantic models for request/response
class SearchParams(BaseModel):
    query: str = Field(..., description="Search query text")
    top_k: int = Field(10, description="Number of results to return")
    conversation_id: Optional[str] = Field(None, description="Filter by conversation ID")
    sender: Optional[str] = Field(None, description="Filter by sender name/ID")
    outgoing: Optional[bool] = Field(None, description="Filter by message direction")
    date_from: Optional[datetime] = Field(None, description="Filter messages from this date")
    date_to: Optional[datetime] = Field(None, description="Filter messages until this date")
    search_type: str = Field("combined", description="Search type: 'semantic', 'keyword', or 'combined'")

class SearchResult(BaseModel):
    id: str
    text: str
    highlighted_text: Optional[str] = None
    score: float
    metadata: Dict[str, Any]

class SearchResponse(BaseModel):
    results: List[SearchResult]
    count: int

class ContextResponse(BaseModel):
    messages: List[Dict[str, Any]]
    count: int

# Load environment variables from .env file
load_dotenv()

# Configuration variables with defaults
API_HOST = os.getenv("MEMORY_FINDER_HOST", "0.0.0.0")
API_PORT = int(os.getenv("MEMORY_FINDER_PORT", "8002"))
DEBUG_MODE = os.getenv("MEMORY_FINDER_DEBUG", "False").lower() == "true"

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    global vector_store, embedder
    
    # Ensure ICI_CONFIG_PATH is set
    if not os.environ.get("ICI_CONFIG_PATH"):
        os.environ["ICI_CONFIG_PATH"] = os.path.join(os.getcwd(), "config.yaml")
    
    try:
        # Get vector store configuration from environment variables
        vector_store_path = os.getenv("VECTOR_STORE_PATH", "./data/chroma")
        vector_store_collection = os.getenv("VECTOR_STORE_COLLECTION", "chat_history")
        
        # Initialize vector store with configuration from environment
        vector_store = ChromaDBStore(collection_name=vector_store_collection, persist_directory=vector_store_path)
        await vector_store.initialize()
        
        # Get embedder configuration from environment variables
        embedder_model = os.getenv("EMBEDDER_MODEL", "all-MiniLM-L6-v2")
        
        # Initialize embedder with configuration from environment
        embedder = SentenceTransformerEmbedder(model_name=embedder_model)
        await embedder.initialize()
        
        logger.info({
            "action": "API_STARTUP",
            "message": "Successfully initialized components",
            "data": {
                "host": API_HOST,
                "port": API_PORT,
                "debug": DEBUG_MODE
            }
        })
    except Exception as e:
        logger.error({
            "action": "API_STARTUP_ERROR",
            "message": f"Failed to initialize components: {str(e)}",
            "data": {"error": str(e)}
        })
        raise

async def generate_query_embedding(query: str) -> List[float]:
    """Generate an embedding for the query text."""
    global embedder
    embedding, _ = await embedder.embed(query)
    return embedding

def build_filters(search_params: SearchParams) -> Dict[str, Any]:
    """Build filter dictionary based on search parameters."""
    filters = {}
    
    # Parse conversation filter
    if search_params.conversation_id:
        filters["conversation_id"] = search_params.conversation_id
    
    # Parse sender filter
    if search_params.sender:
        filters["sender"] = search_params.sender
    
    # Parse outgoing filter
    if search_params.outgoing is not None:
        filters["outgoing"] = search_params.outgoing
    
    return filters if filters else None

def post_filter_results(results: List[Dict[str, Any]], search_params: SearchParams) -> List[Dict[str, Any]]:
    """Apply additional filters that ChromaDB doesn't support natively."""
    filtered_results = results.copy()
    
    # Apply date filtering
    if search_params.date_from or search_params.date_to:
        date_filtered = []
        for result in filtered_results:
            metadata = result.get('metadata', {})
            msg_date = metadata.get('date')
            
            if not msg_date:
                continue
                
            try:
                msg_datetime = from_isoformat(msg_date)
                
                # Apply date_from filter
                if search_params.date_from:
                    date_from = ensure_tz_aware(search_params.date_from)
                    if msg_datetime < date_from:
                        continue
                
                # Apply date_to filter
                if search_params.date_to:
                    date_to = ensure_tz_aware(search_params.date_to)
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

def get_conversation_context(message_id: str, window: int = 3) -> List[Dict[str, Any]]:
    """Get conversation context around a specific message."""
    global vector_store
    
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

async def perform_keyword_search(search_params: SearchParams) -> List[Dict[str, Any]]:
    """Perform keyword-based search using the vector store's keyword capabilities."""
    global vector_store
    
    # Build filters
    filters = build_filters(search_params)
    
    # Extract keywords from query
    keywords = search_params.query.split()
    
    # Log the search action
    logger.info({
        "action": "KEYWORD_SEARCH",
        "message": f"Searching for keywords: '{search_params.query}'",
        "data": {
            "top_k": search_params.top_k,
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
    keyword_results = keyword_results[:search_params.top_k]
    
    # Highlight query terms in results
    for result in keyword_results:
        if 'text' in result:
            result['highlighted_text'] = highlight_text(result['text'], keywords)
    
    return keyword_results

async def perform_semantic_search(search_params: SearchParams) -> List[Dict[str, Any]]:
    """Perform semantic search based on the provided parameters."""
    global vector_store, embedder
    
    # Build filters
    filters = build_filters(search_params)
    
    # Generate embedding for the query
    query_embedding = await generate_query_embedding(search_params.query)
    
    # Search vector store
    logger.info({
        "action": "SEMANTIC_SEARCH",
        "message": f"Searching for: '{search_params.query}'",
        "data": {
            "top_k": search_params.top_k,
            "filters": filters
        }
    })
    
    results = vector_store.search(
        query_vector=query_embedding,
        num_results=search_params.top_k,
        filters=filters
    )
    
    # Apply post-filtering for complex conditions
    results = post_filter_results(results, search_params)
    
    # Highlight query terms in results
    query_terms = search_params.query.split()
    for result in results:
        if 'text' in result:
            result['highlighted_text'] = highlight_text(result['text'], query_terms)
    
    return results

async def perform_search(search_params: SearchParams) -> List[Dict[str, Any]]:
    """Perform search based on the provided parameters.
    Combines both semantic and keyword search for better results."""
    if search_params.search_type == "keyword":
        # Keyword search only
        return await perform_keyword_search(search_params)
    elif search_params.search_type == "semantic":
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
        return combined_results[:search_params.top_k]

@app.get("/", response_class=HTMLResponse)
async def get_home(request: Request):
    """Render the home page"""
    # Get API base URL from environment or use default
    api_host = os.getenv("MEMORY_FINDER_HOST", "0.0.0.0")
    api_port = os.getenv("MEMORY_FINDER_PORT", "8002")
    api_base_url = os.getenv("MEMORY_FINDER_API_BASE_URL", f"http://{api_host}:{api_port}")
    
    # Pass API base URL to template
    return templates.TemplateResponse("index.html", {
        "request": request,
        "api_base_url": api_base_url
    })

@app.post("/api/search", response_model=SearchResponse)
async def search(search_params: SearchParams):
    """Search endpoint for finding messages based on query and filters"""
    try:
        results = await perform_search(search_params)
        
        # Convert results to response model format
        formatted_results = []
        for result in results:
            formatted_results.append(SearchResult(
                id=result.get('id', ''),
                text=result.get('text', ''),
                highlighted_text=result.get('highlighted_text', result.get('text', '')),
                score=result.get('score', 0.0),
                metadata=result.get('metadata', {})
            ))
        
        return SearchResponse(results=formatted_results, count=len(formatted_results))
    except Exception as e:
        logger.error({
            "action": "SEARCH_ERROR",
            "message": f"Error during search: {str(e)}",
            "data": {"error": str(e), "search_params": search_params.dict()}
        })
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@app.get("/api/context/{message_id}", response_model=ContextResponse)
async def get_context(message_id: str, window: int = Query(3, ge=1, le=10)):
    """Get conversation context around a specific message"""
    try:
        context_messages = get_conversation_context(message_id, window)
        
        # Add highlighted text for the target message
        for msg in context_messages:
            if msg.get('id') == message_id and 'highlighted_text' not in msg:
                msg['highlighted_text'] = msg.get('text', '')
        
        return ContextResponse(messages=context_messages, count=len(context_messages))
    except Exception as e:
        logger.error({
            "action": "CONTEXT_ERROR",
            "message": f"Error getting context: {str(e)}",
            "data": {"error": str(e), "message_id": message_id}
        })
        raise HTTPException(status_code=500, detail=f"Context error: {str(e)}")

if __name__ == "__main__":
    # This is for direct execution, not when imported by uvicorn
    uvicorn.run("memory_finder_fastapi_app:app", host=API_HOST, port=API_PORT, reload=DEBUG_MODE)