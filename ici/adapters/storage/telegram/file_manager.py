"""
File management system for Telegram conversation storage.

This module provides functionality to save, load, and manage JSON files for
Telegram conversations, implementing the filename-based approach for tracking
processing status.
"""

import os
import json
import fnmatch
import shutil
from typing import Dict, Any, List, Optional, Tuple, Iterator
from pathlib import Path
import tempfile

from ici.adapters.loggers import StructuredLogger
from ici.adapters.storage.telegram.serializer import ConversationSerializer
from ici.utils.config import get_component_config

class FileManager:
    """
    Manages the storage and retrieval of Telegram conversation files with
    filename-based processing status tracking.
    """
    
    # File status constants
    STATUS_UNPROCESSED = "unprocessed"
    STATUS_PROCESSED = "processed"
    
    def __init__(self, 
                 storage_dir: Optional[str] = None, 
                 serializer: Optional[ConversationSerializer] = None,
                 logger: Optional[StructuredLogger] = None):
        """
        Initialize the file manager.
        
        Args:
            storage_dir: Directory for storing conversation files. If None, uses config.
            serializer: Serializer for conversation data. If None, creates a new one.
            logger: Logger instance for reporting operations. If None, creates a new one.
        """
        newLogger = StructuredLogger(__name__)
        newLogger.initialize()
        self.logger = logger or newLogger
        
        
        # Load storage directory from config if not provided
        if storage_dir is None:
            try:
                config = get_component_config("ingestors.telegram", "config.yaml")
                # Use chat_history_dir from preprocessor if available
                preprocessor_config = get_component_config("preprocessors.telegram", "config.yaml")
                storage_dir = preprocessor_config.get(
                    "chat_history_dir", 
                    config.get("json_storage_path", os.path.join("db", "telegram", "chats"))
                )
            except Exception as e:
                self.logger.warning({
                    "action": "CONFIG_LOAD_FAILED",
                    "message": f"Could not load config, using default storage directory",
                    "data": {
                        "error": str(e),
                        "default_directory": os.path.join("db", "telegram", "chats")
                    },
                    "exception": e
                })
                storage_dir = os.path.join("db", "telegram", "chats")
        
        self.storage_dir = storage_dir
        self.serializer = serializer or ConversationSerializer(logger=self.logger)
        
        # Ensure storage directory exists
        os.makedirs(self.storage_dir, exist_ok=True)
        
        self.logger.info({
            "action": "FILE_MANAGER_INITIALIZED",
            "message": "Initialized FileManager with storage directory",
            "data": {
                "storage_directory": self.storage_dir
            }
        })
    
    def get_storage_path(self, conversation_id: str, processed: bool = False) -> str:
        """
        Determine the correct file path for a conversation based on its ID and status.
        
        Args:
            conversation_id: Unique identifier for the conversation.
            processed: Whether the conversation has been processed.
            
        Returns:
            str: Full path to the conversation file.
        """
        status = self.STATUS_PROCESSED if processed else self.STATUS_UNPROCESSED
        filename = f"{conversation_id}_{status}.json"
        return os.path.join(self.storage_dir, filename)
    
    def save_conversation(self, conversation: Dict[str, Any], force: bool = False) -> str:
        """
        Serialize and save a conversation as an unprocessed file.
        
        Args:
            conversation: Dictionary representing a Telegram conversation.
            force: If True, overwrites any existing file.
            
        Returns:
            str: Path to the saved file.
            
        Raises:
            ValueError: If the conversation is invalid or missing required fields.
            FileExistsError: If the file already exists and force is False.
        """
        # Extract conversation ID from metadata
        try:
            metadata = self.serializer.extract_metadata(conversation)
            conversation_id = metadata.get("conversation_id")
            
            if not conversation_id:
                raise ValueError("Conversation ID not found in metadata")
                
        except Exception as e:
            self.logger.error({
                "action": "CONVERSATION_ID_EXTRACTION_FAILED",
                "message": f"Failed to extract conversation ID",
                "data": {
                    "error": str(e)
                },
                "exception": e
            })
            raise ValueError(f"Invalid conversation structure: {str(e)}")
        
        # Get file path (always unprocessed when saving initially)
        file_path = self.get_storage_path(conversation_id, processed=False)
        
        # Check if file exists and handle force flag
        if os.path.exists(file_path) and not force:
            self.logger.warning({
                "action": "FILE_ALREADY_EXISTS",
                "message": f"File already exists",
                "data": {
                    "file_path": file_path,
                    "conversation_id": conversation_id,
                    "force": force
                }
            })
            raise FileExistsError(f"Conversation file already exists: {file_path}")
        
        # Write to temporary file first for atomic operation
        json_string = self.serializer.serialize_conversation(conversation)
        
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
            temp_file.write(json_string)
            temp_path = temp_file.name
        
        # Atomic move to ensure data integrity
        try:
            shutil.move(temp_path, file_path)
            self.logger.info({
                "action": "CONVERSATION_SAVED",
                "message": f"Saved conversation to file",
                "data": {
                    "conversation_id": conversation_id,
                    "file_path": file_path,
                    "processed": False
                }
            })
            return file_path
        except Exception as e:
            self.logger.error({
                "action": "SAVE_CONVERSATION_FAILED",
                "message": f"Failed to save conversation",
                "data": {
                    "conversation_id": conversation_id,
                    "file_path": file_path,
                    "error": str(e)
                },
                "exception": e
            })
            # Clean up temp file if move failed
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise IOError(f"Failed to save conversation: {str(e)}")
    
    def load_conversation(self, conversation_id: str, require_unprocessed: bool = False) -> Dict[str, Any]:
        """
        Load and deserialize a conversation by ID.
        
        Args:
            conversation_id: Unique identifier for the conversation.
            require_unprocessed: If True, only loads unprocessed conversations.
            
        Returns:
            Dict[str, Any]: Dictionary representation of the conversation.
            
        Raises:
            FileNotFoundError: If the conversation file is not found.
            ValueError: If the file contains invalid JSON or schema.
        """
        # First try to find the file with the specified status if required
        if require_unprocessed:
            file_path = self.get_storage_path(conversation_id, processed=False)
            if not os.path.exists(file_path):
                self.logger.error({
                    "action": "UNPROCESSED_FILE_NOT_FOUND",
                    "message": f"Unprocessed conversation file not found",
                    "data": {
                        "conversation_id": conversation_id,
                        "file_path": file_path
                    }
                })
                raise FileNotFoundError(f"Unprocessed conversation file not found: {file_path}")
        else:
            # Try unprocessed first, then processed
            unprocessed_path = self.get_storage_path(conversation_id, processed=False)
            processed_path = self.get_storage_path(conversation_id, processed=True)
            
            if os.path.exists(unprocessed_path):
                file_path = unprocessed_path
            elif os.path.exists(processed_path):
                file_path = processed_path
            else:
                self.logger.info({
                    "action": "CONVERSATION_FILE_NOT_FOUND",
                    "message": f"Conversation file not found for ID",
                    "data": {
                        "conversation_id": conversation_id,
                        "unprocessed_path": unprocessed_path,
                        "processed_path": processed_path
                    }
                })
                raise FileNotFoundError(f"Conversation file not found for ID: {conversation_id}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_string = f.read()
            
            conversation = self.serializer.deserialize_conversation(json_string)
            self.logger.info({
                "action": "CONVERSATION_LOADED",
                "message": f"Loaded conversation from file",
                "data": {
                    "conversation_id": conversation_id,
                    "file_path": file_path,
                    "processed": "processed" in file_path
                }
            })
            return conversation
            
        except Exception as e:
            self.logger.error({
                "action": "LOAD_CONVERSATION_FAILED",
                "message": f"Failed to load conversation",
                "data": {
                    "conversation_id": conversation_id,
                    "file_path": file_path,
                    "error": str(e)
                },
                "exception": e
            })
            raise ValueError(f"Failed to load conversation: {str(e)}")
    
    def mark_as_processed(self, conversation_id: str) -> str:
        """
        Rename a conversation file to indicate processed status.
        
        Args:
            conversation_id: Unique identifier for the conversation.
            
        Returns:
            str: Path to the renamed file.
            
        Raises:
            FileNotFoundError: If the unprocessed conversation file is not found.
            FileExistsError: If the processed file already exists.
        """
        unprocessed_path = self.get_storage_path(conversation_id, processed=False)
        processed_path = self.get_storage_path(conversation_id, processed=True)
        
        # Check if unprocessed file exists
        if not os.path.exists(unprocessed_path):
            self.logger.error({
                "action": "UNPROCESSED_FILE_NOT_FOUND",
                "message": f"Unprocessed conversation file not found",
                "data": {
                    "conversation_id": conversation_id,
                    "file_path": unprocessed_path
                }
            })
            raise FileNotFoundError(f"Unprocessed conversation file not found: {unprocessed_path}")
        
        # Check if processed file already exists
        if os.path.exists(processed_path):
            self.logger.warning({
                "action": "PROCESSED_FILE_EXISTS",
                "message": f"Processed file already exists",
                "data": {
                    "conversation_id": conversation_id,
                    "file_path": processed_path
                }
            })
            raise FileExistsError(f"Processed file already exists: {processed_path}")
        
        # Rename the file
        try:
            os.rename(unprocessed_path, processed_path)
            self.logger.info({
                "action": "CONVERSATION_MARKED_PROCESSED",
                "message": f"Marked conversation as processed",
                "data": {
                    "conversation_id": conversation_id,
                    "old_path": unprocessed_path,
                    "new_path": processed_path
                }
            })
            return processed_path
        except Exception as e:
            self.logger.error({
                "action": "MARK_PROCESSED_FAILED",
                "message": f"Failed to mark conversation as processed",
                "data": {
                    "conversation_id": conversation_id,
                    "old_path": unprocessed_path,
                    "new_path": processed_path,
                    "error": str(e)
                },
                "exception": e
            })
            raise IOError(f"Failed to mark conversation as processed: {str(e)}")
    
    def list_conversations(self, processed: Optional[bool] = None) -> List[str]:
        """
        List all conversation IDs, optionally filtering by processing status.
        
        Args:
            processed: If True, only list processed conversations.
                     If False, only list unprocessed conversations.
                     If None, list all conversations.
            
        Returns:
            List[str]: List of conversation IDs.
        """
        # Determine file pattern based on status
        if processed is True:
            pattern = f"*_{self.STATUS_PROCESSED}.json"
        elif processed is False:
            pattern = f"*_{self.STATUS_UNPROCESSED}.json"
        else:
            # Both statuses
            pattern = "*.json"
        
        # Get matching files and extract conversation IDs
        conversation_ids = []
        for filename in os.listdir(self.storage_dir):
            if fnmatch.fnmatch(filename, pattern):
                # Extract conversation ID from filename
                parts = filename.split('_')
                if len(parts) >= 2:
                    # Join all parts except the status suffix
                    conversation_id = '_'.join(parts[:-1])
                    conversation_ids.append(conversation_id)
        
        self.logger.debug({
            "action": "CONVERSATIONS_LISTED",
            "message": f"Listed conversation IDs with filter",
            "data": {
                "processed_filter": processed,
                "pattern": pattern,
                "count": len(conversation_ids)
            }
        })
        
        return conversation_ids
    
    def get_conversation_stats(self) -> Dict[str, int]:
        """
        Get statistics about stored conversations.
        
        Returns:
            Dict[str, int]: Dictionary with counts of processed, unprocessed, and total conversations.
        """
        processed_count = len(self.list_conversations(processed=True))
        unprocessed_count = len(self.list_conversations(processed=False))
        
        stats = {
            "processed_count": processed_count,
            "unprocessed_count": unprocessed_count,
            "total_count": processed_count + unprocessed_count
        }
        
        self.logger.info({
            "action": "CONVERSATION_STATS_RETRIEVED",
            "message": "Retrieved conversation statistics",
            "data": stats
        })
        
        return stats 