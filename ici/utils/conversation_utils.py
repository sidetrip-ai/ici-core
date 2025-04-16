"""
Conversation type detection and filtering utilities for Telegram.

This module provides functions to detect and filter Telegram conversations
based on type (personal chats, bot chats, private groups) as specified in the PRD.
"""

from typing import Dict, Any, List, Optional, Callable

from ici.adapters.loggers import StructuredLogger
from ici.utils.config import get_component_config

# Logger for this module
logger = StructuredLogger(__name__)
logger.initialize()
def is_personal_chat(conversation: Dict[str, Any]) -> bool:
    """
    Determine if a conversation is a personal chat.
    
    A personal chat is defined as:
    - not a group
    - chat_type is "private"
    
    Args:
        conversation: Conversation metadata dictionary
        
    Returns:
        bool: True if the conversation is a personal chat, False otherwise
    """
    if not conversation or "metadata" not in conversation:
        return False
    
    metadata = conversation["metadata"]
    return (not metadata.get("is_group", False) and 
            metadata.get("chat_type", "") == "private")


def is_bot_chat(conversation: Dict[str, Any]) -> bool:
    """
    Determine if a conversation is with a bot.
    
    A bot chat is defined as:
    - username ends with "bot"
    
    Args:
        conversation: Conversation metadata dictionary
        
    Returns:
        bool: True if the conversation is with a bot, False otherwise
    """
    if not conversation or "metadata" not in conversation:
        return False
    
    metadata = conversation["metadata"]
    username = metadata.get("username", "")
    
    if not username:
        return False
    
    return username.lower().endswith("bot")


def is_private_group(conversation: Dict[str, Any]) -> bool:
    """
    Determine if a conversation is a private group.
    
    A private group is defined as:
    - is a group
    - not a channel
    - chat_type is not "channel"
    
    Args:
        conversation: Conversation metadata dictionary
        
    Returns:
        bool: True if the conversation is a private group, False otherwise
    """
    if not conversation or "metadata" not in conversation:
        return False
    
    metadata = conversation["metadata"]
    return (metadata.get("is_group", False) and 
            not metadata.get("is_channel", False) and 
            metadata.get("chat_type", "") != "channel")


def filter_conversations(
    conversations: Dict[str, Any],
    fetch_mode: str = "initial") -> Dict[str, Any]:
    """
    Filter conversations based on the fetch mode.
    
    Args:
        conversations: Dictionary of conversations keyed by conversation_id
        fetch_mode: Either "initial" (personal, bot chats, private groups) or "all"
    
    Returns:
        Dict[str, Any]: Filtered conversations
    """
    if fetch_mode.lower() == "all":
        return conversations
    
    filtered_conversations = {}
    
    for conv_id, conversation in conversations.items():
        # For initial mode, only include personal chats, bot chats, and private groups
        if fetch_mode.lower() == "initial":
            if (is_personal_chat(conversation) or 
                is_bot_chat(conversation) or 
                is_private_group(conversation)):
                filtered_conversations[conv_id] = conversation
                
                # Add metadata tag for the conversation type
                if "metadata" in conversation:
                    metadata = conversation["metadata"]
                    metadata["conversation_types"] = []
                    
                    if is_personal_chat(conversation):
                        metadata["conversation_types"].append("personal_chat")
                    if is_bot_chat(conversation):
                        metadata["conversation_types"].append("bot_chat")
                    if is_private_group(conversation):
                        metadata["conversation_types"].append("private_group")
        else:
            # Unknown fetch mode, just return the original data
            return conversations
    
    return filtered_conversations


def get_fetch_mode_from_config() -> str:
    """
    Get the configured fetch mode from config.yaml.
    
    Returns:
        str: The fetch mode ("initial" or "all")
    """
    try:
        telegram_config = get_component_config("ingestors.telegram")
        fetch_mode = telegram_config.get("fetch_mode", "initial")
        
        # Validate fetch mode
        if fetch_mode.lower() not in ["initial", "all"]:
            logger.warning({
                "action": "INVALID_FETCH_MODE",
                "message": "Invalid fetch_mode",
                "data": {
                    "fetch_mode": fetch_mode
                }
            })
            fetch_mode = "initial"
            
        return fetch_mode
        
    except Exception as e:
        logger.warning({
            "action": "ERROR_GETTING_FETCH_MODE",
            "message": "Error getting fetch_mode from config",
            "data": {
                "error": str(e)
            }
        })
        return "initial"


def add_conversation_type_metadata(conversations: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add conversation type metadata to each conversation.
    
    This function adds a "conversation_types" field to the metadata of each
    conversation, containing a list of applicable types.
    
    Args:
        conversations: Dictionary of conversations keyed by conversation_id
    
    Returns:
        Dict[str, Any]: Updated conversations with type metadata
    """
    for conv_id, conversation in conversations.items():
        if "metadata" in conversation:
            metadata = conversation["metadata"]
            metadata["conversation_types"] = []
            
            if is_personal_chat(conversation):
                metadata["conversation_types"].append("personal_chat")
            if is_bot_chat(conversation):
                metadata["conversation_types"].append("bot_chat")
            if is_private_group(conversation):
                metadata["conversation_types"].append("private_group")
    
    return conversations 