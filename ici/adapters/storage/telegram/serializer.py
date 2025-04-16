"""
Serialization utilities for Telegram conversation data.

This module provides functionality to convert between Python objects and JSON
representations of Telegram conversations, with validation against the schema.
"""

import json
import jsonschema
from typing import Dict, Any, Optional, List, Union

from ici.adapters.loggers import StructuredLogger
from ici.adapters.storage.telegram.schema import TELEGRAM_SCHEMA

class ConversationSerializer:
    """
    Handles serialization, deserialization, and validation of Telegram conversation data.
    """
    
    def __init__(self, logger: Optional[StructuredLogger] = None):
        """
        Initialize the serializer.
        
        Args:
            logger: Optional logger instance for reporting validation errors.
        """
        self.schema = TELEGRAM_SCHEMA
        newLogger = StructuredLogger(__name__)
        newLogger.initialize()
        self.logger = logger or newLogger
    
    def serialize_conversation(self, conversation: Dict[str, Any], pretty: bool = False) -> str:
        """
        Convert a conversation object to a JSON string.
        
        Args:
            conversation: Dictionary representing a Telegram conversation.
            pretty: Whether to format the JSON with indentation for readability.
            
        Returns:
            str: JSON string representation of the conversation.
            
        Raises:
            ValueError: If the conversation fails schema validation.
        """
        # Validate before serializing
        try:
            self.validate_conversation(conversation)
        except jsonschema.exceptions.ValidationError as e:
            self.logger.error({
                "action": "CONVERSATION_VALIDATION_FAILED",
                "message": f"Conversation validation failed: {str(e)}",
                "data": {
                    "error_type": "validation_error",
                    "schema": "telegram_conversation"
                },
                "exception": e
            })
            raise ValueError(f"Invalid conversation structure: {str(e)}")
        
        # Serialize to JSON
        indent = 2 if pretty else None
        return json.dumps(conversation, indent=indent, sort_keys=True, ensure_ascii=False)
    
    def deserialize_conversation(self, json_string: str) -> Dict[str, Any]:
        """
        Convert a JSON string to a conversation object.
        
        Args:
            json_string: JSON string representing a Telegram conversation.
            
        Returns:
            Dict[str, Any]: Dictionary representation of the conversation.
            
        Raises:
            ValueError: If the JSON string is malformed or fails schema validation.
        """
        try:
            conversation = json.loads(json_string)
        except json.JSONDecodeError as e:
            self.logger.error({
                "action": "JSON_PARSING_FAILED",
                "message": f"JSON parsing failed: {str(e)}",
                "data": {
                    "error_type": "json_decode_error"
                },
                "exception": e
            })
            raise ValueError(f"Malformed JSON: {str(e)}")
        
        # Validate after deserializing
        try:
            self.validate_conversation(conversation)
        except jsonschema.exceptions.ValidationError as e:
            self.logger.error({
                "action": "DESERIALIZED_VALIDATION_FAILED",
                "message": f"Deserialized conversation validation failed: {str(e)}",
                "data": {
                    "error_type": "validation_error",
                    "schema": "telegram_conversation"
                },
                "exception": e
            })
            raise ValueError(f"Invalid conversation structure: {str(e)}")
        
        return conversation
    
    def validate_conversation(self, conversation: Dict[str, Any]) -> None:
        """
        Validate a conversation object against the schema.
        
        Args:
            conversation: Dictionary representing a Telegram conversation.
            
        Raises:
            jsonschema.exceptions.ValidationError: If validation fails.
        """
        jsonschema.validate(instance=conversation, schema=self.schema)
    
    def extract_metadata(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract only the metadata portion of a conversation.
        
        Args:
            conversation: Dictionary representing a Telegram conversation.
            
        Returns:
            Dict[str, Any]: Metadata dictionary.
            
        Raises:
            ValueError: If the conversation doesn't contain metadata.
        """
        if 'metadata' not in conversation:
            raise ValueError("Conversation does not contain metadata")
        
        return conversation['metadata']
    
    def extract_messages(self, conversation: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Extract only the messages portion of a conversation.
        
        Args:
            conversation: Dictionary representing a Telegram conversation.
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of message ID to message data.
            
        Raises:
            ValueError: If the conversation doesn't contain messages.
        """
        if 'messages' not in conversation:
            raise ValueError("Conversation does not contain messages")
        
        return conversation['messages']
    
    def get_latest_message_date(self, conversation: Dict[str, Any]) -> Optional[str]:
        """
        Get the date of the latest message in the conversation.
        
        Args:
            conversation: Dictionary representing a Telegram conversation.
            
        Returns:
            Optional[str]: ISO-format date string of the latest message, or None if no messages.
        """
        try:
            metadata = self.extract_metadata(conversation)
            return metadata.get('last_message_date')
        except (ValueError, KeyError):
            # If metadata extraction fails or last_message_date isn't available
            return None 