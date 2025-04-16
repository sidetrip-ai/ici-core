"""
Incremental message fetching utilities for Telegram.

This module provides functionality to enable incremental message fetching
to minimize API usage, improve performance, and reduce redundant data processing.
"""

import os
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import pytz

from ici.adapters.loggers import StructuredLogger
from ici.adapters.storage.telegram.file_manager import FileManager

# Logger for this module
logger = StructuredLogger(__name__)
logger.initialize()

def get_latest_message_timestamp(conversation: Dict[str, Any]) -> Optional[datetime]:
    """
    Get the timestamp of the latest message in a conversation.
    
    Args:
        conversation: The conversation dictionary
        
    Returns:
        Optional[datetime]: Timestamp of the latest message, or None if no messages
    """
    if not conversation or "messages" not in conversation:
        return None
    
    messages = conversation.get("messages", {})
    if not messages:
        return None
    
    # Find latest message by comparing timestamps
    latest_timestamp = None
    latest_date = None
    
    for message_id, message in messages.items():
        if "date" not in message:
            continue
            
        try:
            # Parse the ISO date string
            msg_date = datetime.fromisoformat(message["date"].replace('Z', '+00:00'))
            
            if latest_date is None or msg_date > latest_date:
                latest_date = msg_date
                latest_timestamp = message.get("timestamp")
        except (ValueError, TypeError):
            logger.warning({
                "action": "FAILED_TO_PARSE_DATE",
                "message": "Failed to parse date in message",
                "data": {
                    "message_id": message_id
                }
            })
            continue
    
    return latest_date

def update_conversation_metadata(conversation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update conversation metadata with last message date and update timestamp.
    
    Args:
        conversation: The conversation dictionary
        
    Returns:
        Dict[str, Any]: Updated conversation
    """
    if not conversation or "metadata" not in conversation:
        return conversation
    
    metadata = conversation["metadata"]
    
    # Get latest message timestamp
    latest_date = get_latest_message_timestamp(conversation)
    
    # Update metadata
    if latest_date:
        metadata["last_message_date"] = latest_date.isoformat()
    
    # Always update the last_update field
    metadata["last_update"] = datetime.now(pytz.UTC).isoformat()
    
    return conversation

def should_fetch_incrementally(conversation_id: str, file_manager: FileManager) -> Tuple[bool, Optional[datetime]]:
    """
    Determine if incremental fetching should be used for this conversation,
    and return the timestamp to fetch from.
    
    Args:
        conversation_id: ID of the conversation
        file_manager: FileManager instance to load existing conversation
        
    Returns:
        Tuple[bool, Optional[datetime]]: 
            - Boolean indicating if incremental fetching should be used
            - Timestamp to fetch messages from (if incremental)
    """
    try:
        # Check if we have an existing conversation file
        conversation = file_manager.load_conversation(conversation_id)
        
        # Get latest message timestamp
        latest_date = get_latest_message_timestamp(conversation)
        
        if latest_date:
            # If we have messages, use incremental fetching
            return True, latest_date
        else:
            # If no messages, use full fetch
            return False, None
            
    except FileNotFoundError:
        # If file doesn't exist, use full fetch
        return False, None
    except Exception as e:
        logger.warning({
            "action": "ERROR_CHECKING_INCREMENTAL_STATUS",
            "message": "Error checking incremental status for conversation",
            "data": {
                "conversation_id": conversation_id,
                "error": str(e)
            }
        })
        # Default to full fetch if any error
        return False, None

def merge_conversations(
    existing_conversation: Dict[str, Any], 
    new_messages: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Merge new messages into an existing conversation, handling duplicates.
    
    Args:
        existing_conversation: Existing conversation dictionary
        new_messages: List of new messages to add
        
    Returns:
        Dict[str, Any]: Updated conversation with merged messages
    """
    if not existing_conversation or "messages" not in existing_conversation:
        return existing_conversation
    
    if not new_messages:
        return existing_conversation
    
    # Extract existing messages
    messages = existing_conversation.get("messages", {})
    
    # Add new messages, avoiding duplicates
    for message in new_messages:
        message_id = str(message.get("id"))
        if not message_id:
            continue
            
        # Skip if message already exists
        if message_id in messages:
            # Handle edits by comparing timestamps if available
            if ("timestamp" in message and "timestamp" in messages[message_id] and
                message.get("timestamp") > messages[message_id].get("timestamp")):
                # Update the message if it's newer (edited)
                messages[message_id] = message
            # Otherwise keep existing message
            continue
        
        # Add new message
        messages[message_id] = message
    
    # Update the conversation
    existing_conversation["messages"] = messages
    
    # Update metadata with latest timestamps
    return update_conversation_metadata(existing_conversation)

def prepare_min_id_for_fetch(latest_date: datetime, messages: List[Dict[str, Any]]) -> Optional[int]:
    """
    Determine the min_id parameter for fetching based on timestamp.
    
    Args:
        latest_date: The latest message date from existing data
        messages: List of messages to search for matching date
        
    Returns:
        Optional[int]: Message ID to use as min_id, or None
    """
    if not latest_date or not messages:
        return None
    
    # Find a message with a timestamp that matches or is just after the latest_date
    # This helps establish an appropriate min_id for fetching
    matching_id = None
    matching_date = None
    
    for message in messages:
        try:
            if "date" not in message:
                continue
                
            msg_date = datetime.fromisoformat(message["date"].replace('Z', '+00:00'))
            
            # If this message is newer than our latest date
            if msg_date >= latest_date:
                # Either we haven't found a match yet, or this one is closer to latest_date
                if matching_date is None or msg_date < matching_date:
                    matching_date = msg_date
                    matching_id = message.get("id")
        except (ValueError, TypeError):
            continue
    
    return matching_id

def get_latest_message_id(conversation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Get the ID and date of the latest message in a conversation.
    
    Args:
        conversation: The conversation dictionary
        
    Returns:
        Optional[Dict[str, Any]]: Dict with id and date of latest message, or None
    """
    if not conversation or "messages" not in conversation:
        return None
    
    messages = conversation.get("messages", {})
    if not messages:
        return None
    
    # Find latest message by comparing timestamps
    latest_msg = None
    latest_date = None
    
    for message_id, message in messages.items():
        if "date" not in message or "id" not in message:
            continue
            
        try:
            # Parse the ISO date string
            msg_date = datetime.fromisoformat(message["date"].replace('Z', '+00:00'))
            
            if latest_date is None or msg_date > latest_date:
                latest_date = msg_date
                latest_msg = {
                    "id": int(message["id"]),
                    "date": message["date"]
                }
        except (ValueError, TypeError):
            logger.warning({
                "action": "FAILED_TO_PARSE_MESSAGE_DATA",
                "message": "Failed to parse date or ID in message",
                "data": {
                    "message_id": message_id
                }
            })
            continue
    
    return latest_msg

def should_fetch_incrementally_by_id(conversation_id: str, file_manager: FileManager) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Determine if ID-based incremental fetching should be used for this conversation,
    and return the latest message ID to fetch from.
    
    Args:
        conversation_id: ID of the conversation
        file_manager: FileManager instance to load existing conversation
        
    Returns:
        Tuple[bool, Optional[Dict[str, Any]]]:
            - Boolean indicating if incremental fetching should be used
            - Dict with id and date of latest message (if incremental)
    """
    try:
        # Check if we have an existing conversation file
        conversation = file_manager.load_conversation(conversation_id)
        
        # Get latest message ID and date
        latest_msg = get_latest_message_id(conversation)
        
        if latest_msg and latest_msg["id"]:
            # If we have messages with IDs, use incremental fetching
            return True, latest_msg
        else:
            # If no valid message IDs, use full fetch
            return False, None
            
    except FileNotFoundError:
        # If file doesn't exist, use full fetch
        return False, None
    except Exception as e:
        logger.warning({
            "action": "ERROR_CHECKING_INCREMENTAL_STATUS_BY_ID",
            "message": "Error checking ID-based incremental status for conversation",
            "data": {
                "conversation_id": conversation_id,
                "error": str(e)
            }
        })
        # Default to full fetch if any error
        return False, None 