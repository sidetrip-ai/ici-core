"""
Utility functions for handling metadata operations.

This module provides helper functions for working with metadata
across different components, especially for vector store compatibility.
"""

import json
from typing import Any, Dict


def sanitize_metadata_for_vector_store(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize metadata to ensure compatibility with vector stores.
    
    Converts complex data types to formats compatible with vector stores
    like ChromaDB that only support str, int, float, and bool metadata values.
    
    Args:
        metadata: Original metadata dictionary
        
    Returns:
        Dict[str, Any]: Sanitized metadata with only supported types
    """
    sanitized = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            # Already supported types
            sanitized[key] = value
        elif isinstance(value, list):
            # Convert lists to comma-separated strings
            sanitized[key] = ",".join(str(item) for item in value)
        elif isinstance(value, set):
            # Convert sets to comma-separated strings
            sanitized[key] = ",".join(str(item) for item in value)
        elif isinstance(value, dict):
            # Convert dictionaries to JSON strings
            sanitized[key] = json.dumps(value)
        elif value is None:
            # Convert None to empty string
            sanitized[key] = ""
        else:
            # Fallback for any other types
            sanitized[key] = str(value)
    
    return sanitized 