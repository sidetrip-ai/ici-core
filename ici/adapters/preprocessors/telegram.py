"""
Telegram preprocessor implementation.

This module provides a Preprocessor implementation for Telegram data,
handling message grouping, chunking, and metadata extraction.
"""

import os
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
import uuid
import asyncio
import json
import re

from ici.core.interfaces.preprocessor import Preprocessor
from ici.core.exceptions import PreprocessorError
from ici.adapters.loggers import StructuredLogger
from ici.utils.config import get_component_config
from ici.utils.metadata_utils import sanitize_metadata_for_vector_store


class TelegramPreprocessor(Preprocessor):
    """
    Preprocessor for Telegram messages.
    
    This preprocessor transforms raw Telegram messages into standardized documents
    by grouping them into time-based windows and formatting them as conversations.
    """
    
    def __init__(self, ingestor=None, logger_name: str = "telegram_preprocessor"):
        """
        Initialize the TelegramPreprocessor.
        
        Args:
            ingestor: Optional Telegram ingestor to get user information from
            logger_name: Name for the logger instance
        """
        self.logger = StructuredLogger(name=logger_name)
        self._is_initialized = False
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        
        # Default configuration
        self._time_window_minutes = 15
        self._chunk_size = 512
        self._max_messages_per_chunk = 10
        self._include_overlap = True
        
        # User identification
        self._my_user_id = None  # The user's Telegram ID for identifying "Me" messages
        self._ingestor = ingestor
        
        # Chat history storage settings
        self._store_chat_history = True
        self._chat_history_dir = None
        self._lock = asyncio.Lock()  # For thread safety
    
    async def initialize(self) -> None:
        """
        Initialize the preprocessor with configuration parameters.
        
        Loads configuration from config.yaml and sets chunking parameters.
        
        Returns:
            None
            
        Raises:
            PreprocessorError: If initialization fails
        """
        try:
            self.logger.info({
                "action": "PREPROCESSOR_INIT_START",
                "message": "Initializing Telegram preprocessor"
            })
            
            # Load preprocessor configuration
            try:
                preprocessor_config = get_component_config("preprocessors.telegram", self._config_path)
                
                # Extract chunking parameters with defaults
                self._time_window_minutes = int(preprocessor_config.get("time_window_minutes", 15))
                self._chunk_size = int(preprocessor_config.get("chunk_size", 512))
                self._max_messages_per_chunk = int(preprocessor_config.get("max_messages_per_chunk", 10))
                self._include_overlap = bool(preprocessor_config.get("include_overlap", True))
                
                # Extract user identification - prioritize ingestor if available
                if self._ingestor:
                    try:
                        ingestor_user_id = self._ingestor.get_current_user_id()
                        if ingestor_user_id:
                            self._my_user_id = ingestor_user_id
                            self.logger.info({
                                "action": "PREPROCESSOR_USER_ID_FROM_INGESTOR",
                                "message": "User ID obtained from ingestor",
                                "data": {"my_user_id": self._my_user_id}
                            })
                    except Exception as e:
                        self.logger.warning({
                            "action": "PREPROCESSOR_USER_ID_INGESTOR_ERROR",
                            "message": f"Error getting user ID from ingestor: {str(e)}",
                            "data": {"error": str(e)}
                        })
                
                # As a fallback, try to get from config (deprecated)
                if not self._my_user_id:
                    self._my_user_id = preprocessor_config.get("my_user_id", None)
                    if self._my_user_id:
                        self.logger.info({
                            "action": "PREPROCESSOR_USER_ID_FROM_CONFIG",
                            "message": "User ID set from config (deprecated)",
                            "data": {"my_user_id": self._my_user_id}
                        })
                
                # Extract chat history storage settings
                if "store_chat_history" in preprocessor_config:
                    self._store_chat_history = bool(preprocessor_config.get("store_chat_history"))
                
                if "chat_history_dir" in preprocessor_config:
                    self._chat_history_dir = preprocessor_config.get("chat_history_dir", os.path.join("db", "telegram", "chats"))
                
                # Create chat history directory if storage is enabled
                if self._store_chat_history:
                    os.makedirs(self._chat_history_dir, exist_ok=True)
                
                self.logger.info({
                    "action": "PREPROCESSOR_CONFIG_LOADED",
                    "message": "Loaded preprocessor configuration",
                    "data": {
                        "time_window_minutes": self._time_window_minutes,
                        "chunk_size": self._chunk_size,
                        "max_messages_per_chunk": self._max_messages_per_chunk,
                        "include_overlap": self._include_overlap,
                        "store_chat_history": self._store_chat_history,
                        "chat_history_dir": self._chat_history_dir,
                        "my_user_id": self._my_user_id
                    }
                })
                
            except Exception as e:
                # Use defaults if configuration loading fails
                self.logger.warning({
                    "action": "PREPROCESSOR_CONFIG_ERROR",
                    "message": f"Failed to load configuration: {str(e)}. Using defaults.",
                    "data": {"error": str(e)}
                })
            
            self._is_initialized = True
            
            self.logger.info({
                "action": "PREPROCESSOR_INIT_SUCCESS",
                "message": "Telegram preprocessor initialized successfully"
            })
            
        except Exception as e:
            self.logger.error({
                "action": "PREPROCESSOR_INIT_ERROR",
                "message": f"Failed to initialize Telegram preprocessor: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise PreprocessorError(f"Preprocessor initialization failed: {str(e)}") from e
    
    async def process(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a batch of Telegram messages into standardized documents.
        
        This method allows direct processing of message batches in async pipelines.
        Each message will be processed into a separate document with its context.
        
        Args:
            messages: List of raw Telegram message dictionaries
            
        Returns:
            List[Dict[str, Any]]: List of standardized documents with 'text' and 'metadata'
            
        Raises:
            PreprocessorError: If preprocessing fails
        """
        if not self._is_initialized:
            raise PreprocessorError("Preprocessor not initialized. Call initialize() first.")
        
        try:
            if not messages:
                self.logger.info({
                    "action": "PREPROCESSOR_NO_MESSAGES",
                    "message": "No messages to process"
                })
                return []
            
            self.logger.info({
                "action": "PREPROCESSOR_PROCESS_START",
                "message": f"Processing {len(messages)} messages",
                "data": {"message_count": len(messages)}
            })
            
            # Group messages by conversation
            conversation_messages = {}
            for message in messages:
                conv_id = message.get("conversation_id")
                if conv_id not in conversation_messages:
                    conversation_messages[conv_id] = []
                conversation_messages[conv_id].append(message)
            
            # Sort messages in each conversation by timestamp
            for conv_id in conversation_messages:
                conversation_messages[conv_id].sort(
                    key=lambda m: m.get("timestamp", 0) 
                    if isinstance(m.get("timestamp"), (int, float)) 
                    else 0
                )
            
            self.logger.info({
                "action": "PREPROCESSOR_GROUPED",
                "message": f"Grouped messages into {len(conversation_messages)} conversations",
                "data": {"conversation_count": len(conversation_messages)}
            })
            
            # Process each message with its context
            documents = []
            for conv_id, conv_messages in conversation_messages.items():
                for i, current_message in enumerate(conv_messages):
                    # Clearly separate the messages into primary, previous, and next
                    primary_message = current_message
                    
                    # Get previous messages (up to 5)
                    start_idx = max(0, i - 5)
                    previous_messages = conv_messages[start_idx:i]
                    
                    # Get next messages (up to 5)
                    end_idx = min(len(conv_messages), i + 6)  # +6 because end index is exclusive
                    next_messages = conv_messages[i+1:end_idx]
                    
                    # Format the message text (only using the primary message)
                    message_text = self._format_conversation([primary_message])
                    
                    # Create metadata with context
                    # Pass all three components separately to make the structure clearer
                    metadata = self._create_metadata_with_context(
                        primary_message=primary_message,
                        previous_messages=previous_messages,
                        next_messages=next_messages
                    )
                    
                    # Create document
                    document = {
                        "id": str(primary_message.get("id", "")),
                        "text": message_text,
                        "metadata": metadata
                    }
                    
                    documents.append(document)
            
            self.logger.info({
                "action": "PREPROCESSOR_PROCESS_COMPLETE",
                "message": f"Created {len(documents)} standardized documents",
                "data": {"document_count": len(documents)}
            })
            
            return documents
            
        except Exception as e:
            self.logger.error({
                "action": "PREPROCESSOR_PROCESS_ERROR",
                "message": f"Failed to process Telegram messages: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise PreprocessorError(f"Message processing failed: {str(e)}") from e
    
    async def preprocess(self, raw_data: Any) -> List[Dict[str, Any]]:
        """
        Transform raw Telegram data into standardized documents.
        
        Implements time-based chunking and conversation formatting for Telegram messages.
        
        Args:
            raw_data: Raw data from TelegramIngestor, can be either:
                     - Legacy format: dict with 'messages' list
                     - New format: dict with 'conversations' dict mapping chat_ids to message lists
            
        Returns:
            List[Dict[str, Any]]: List of standardized documents with 'text' and 'metadata'
            
        Raises:
            PreprocessorError: If preprocessing fails
        """
        if not self._is_initialized:
            raise PreprocessorError("Preprocessor not initialized. Call initialize() first.")
        
        try:
            if not isinstance(raw_data, dict):
                raise PreprocessorError("Invalid raw data format. Expected dictionary.")
            
            # Handle both legacy and new data structures
            all_messages = []
            
            # Check for new format (conversations organized by chat_id)
            if "conversations" in raw_data and isinstance(raw_data["conversations"], dict):
                self.logger.info({
                    "action": "PREPROCESSOR_USING_NEW_FORMAT",
                    "message": "Using new data format with conversations by chat_id"
                })
                
                # Store chat histories if enabled
                if self._store_chat_history:
                    for chat_id, messages in raw_data["conversations"].items():
                        if messages:
                            await self._update_chat_history(chat_id, messages)
                            self.logger.info({
                                "action": "CHAT_HISTORY_STORED",
                                "message": f"Stored chat history for {chat_id}",
                                "data": {"chat_id": chat_id, "message_count": len(messages)}
                            })
                
                # Flatten messages from all conversations
                for chat_id, messages in raw_data["conversations"].items():
                    # Ensure messages have conversation metadata
                    for msg in messages:
                        # Add conversation details if available
                        if "conversation_details" in raw_data and chat_id in raw_data["conversation_details"]:
                            conv_details = raw_data["conversation_details"][chat_id]
                            if "is_group" not in msg and "is_group" in conv_details:
                                msg["is_group"] = conv_details["is_group"]
                            if "chat_type" not in msg and "chat_type" in conv_details:
                                msg["chat_type"] = conv_details["chat_type"]
                    
                    all_messages.extend(messages)
                
            # Check for legacy format (flat messages list)
            elif "messages" in raw_data and isinstance(raw_data["messages"], list):
                self.logger.info({
                    "action": "PREPROCESSOR_USING_LEGACY_FORMAT",
                    "message": "Using legacy data format with flat messages list"
                })
                all_messages = raw_data.get("messages", [])
                
                # Store chat histories for legacy format if enabled
                if self._store_chat_history and all_messages:
                    # Group by chat_id if available
                    chat_messages = {}
                    for msg in all_messages:
                        chat_id = msg.get("chatId") or msg.get("chat_id") or "default"
                        if chat_id not in chat_messages:
                            chat_messages[chat_id] = []
                        chat_messages[chat_id].append(msg)
                    
                    # Store each chat group
                    for chat_id, messages in chat_messages.items():
                        if messages:
                            await self._update_chat_history(chat_id, messages)
                            self.logger.info({
                                "action": "CHAT_HISTORY_STORED",
                                "message": f"Stored chat history for {chat_id}",
                                "data": {"chat_id": chat_id, "message_count": len(messages)}
                            })
            
            else:
                raise PreprocessorError("Invalid data structure. Expected 'conversations' dict or 'messages' list.")
            
            if not all_messages:
                self.logger.info({
                    "action": "PREPROCESSOR_NO_MESSAGES",
                    "message": "No messages to process"
                })
                return []
            
            # Process all messages with the existing pipeline
            return await self.process(all_messages)
            
        except Exception as e:
            self.logger.error({
                "action": "PREPROCESSOR_ERROR",
                "message": f"Failed to preprocess Telegram data: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise PreprocessorError(f"Preprocessing failed: {str(e)}") from e
    
    def _run_sync_process(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Helper method to run process synchronously inside an existing event loop.
        
        Args:
            messages: List of raw Telegram message dictionaries
            
        Returns:
            List[Dict[str, Any]]: Processed documents
        """
        future = asyncio.ensure_future(self.process(messages))
        
        # Wait for completion using the current event loop
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(future)
    
    def _group_messages_by_time(self, messages: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Group messages into time-based windows.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List of message groups, where each group is a list of messages
        """
        if not messages:
            return []
        
        # Sort messages by date
        sorted_messages = sorted(
            messages, 
            key=lambda m: datetime.fromisoformat(m.get("date"))
        )
        
        # Group by conversation and time windows
        conversation_groups = {}
        
        for message in sorted_messages:
            # Extract message data
            conversation_id = message.get("conversation_id")
            message_date = datetime.fromisoformat(message.get("date"))
            
            # Initialize conversation entry if needed
            if conversation_id not in conversation_groups:
                conversation_groups[conversation_id] = []
            
            # Check if message fits in the current window or needs a new one
            current_groups = conversation_groups[conversation_id]
            
            if not current_groups:
                # First message for this conversation
                current_groups.append([message])
            else:
                # Get the last group and its end time
                last_group = current_groups[-1]
                last_message = last_group[-1]
                last_date = datetime.fromisoformat(last_message.get("date"))
                
                # Check if within time window
                if (message_date - last_date) <= timedelta(minutes=self._time_window_minutes):
                    # Add to current group
                    last_group.append(message)
                else:
                    # Start a new group
                    current_groups.append([message])
        
        # Flatten the groups from all conversations
        all_groups = []
        for conversation_id, groups in conversation_groups.items():
            all_groups.extend(groups)
        
        return all_groups
    
    def _create_chunks(self, message_group: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Split large message groups into smaller chunks.
        
        Args:
            message_group: List of messages in a time-based group
            
        Returns:
            List of message chunks
        """
        if not message_group:
            return []
        
        # If group size is small enough, return as is
        if len(message_group) <= self._max_messages_per_chunk:
            return [message_group]
        
        # Split into smaller chunks
        chunks = []
        for i in range(0, len(message_group), self._max_messages_per_chunk):
            # Create chunk with overlap
            if i > 0 and self._include_overlap:
                # Add one overlapping message from previous chunk
                chunk = [message_group[i-1]] + message_group[i:i+self._max_messages_per_chunk]
            else:
                chunk = message_group[i:i+self._max_messages_per_chunk]
            
            chunks.append(chunk)
        
        return chunks
    
    def _format_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format a message as raw text without additional formatting.
        
        Args:
            messages: List of Telegram message dictionaries. We'll only use the current message.
            
        Returns:
            str: Raw message text
        """
        if not messages:
            return ""
        
        # Just return the raw text of the message
        message = messages[0]  # Use the first message as the primary one
        
        # Get the basic text
        text = message.get("text", "")
        
        # Add media descriptions if present
        if message.get("media_type"):
            media_type = message.get("media_type")
            
            if media_type == "sticker":
                emoji = message.get("sticker_emoji", "")
                text += f" [Sticker{': ' + emoji if emoji else ''}]"
                
            elif media_type in ["photo", "video", "document", "audio", "voice"]:
                # Add file name if available
                file_name = message.get("file_name", "")
                if file_name:
                    text += f" [File: {file_name}]"
                else:
                    text += f" [{media_type.capitalize()}]"
            
            # Add caption if present
            if message.get("caption"):
                text += f" Caption: {message.get('caption')}"
        
        return text
    
    def _create_metadata_with_context(
        self, 
        primary_message: Dict[str, Any],
        previous_messages: List[Dict[str, Any]],
        next_messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create rich metadata for a message with clearly separated context.
        
        Args:
            primary_message: The main message being processed
            previous_messages: List of messages that came before
            next_messages: List of messages that came after
            
        Returns:
            Metadata dictionary
        """
        if not primary_message:
            return {}
        
        # Extract message data
        message_id = primary_message.get("id")
        
        # Get chat info
        conversation_id = primary_message.get("conversation_id")
        conversation_name = primary_message.get("conversation_name")
        is_group = primary_message.get("is_group", False)
        chat_type = primary_message.get("chat_type", "private")
        
        # Get message timestamp
        try:
            message_date = datetime.fromisoformat(primary_message.get("date", ""))
            timestamp = int(message_date.timestamp())
            date = message_date.isoformat()
        except:
            # Fallback if date is invalid
            now = datetime.now(timezone.utc)
            timestamp = int(now.timestamp())
            date = now.isoformat()
        
        # Get sender info
        sender_id = primary_message.get("sender_id", primary_message.get("from_id"))
        sender_name = primary_message.get("sender_name", "Unknown")
        
        # Determine if the message is from the user
        is_me = self._my_user_id and str(sender_id) == str(self._my_user_id)
        
        # Extract IDs from previous and next messages
        previous_message_ids = [msg.get("id") for msg in previous_messages]
        next_message_ids = [msg.get("id") for msg in next_messages]
        
        # Get reply information
        reply_to_id = primary_message.get("reply_to_id")
        reply_to_info = None
        
        if reply_to_id:
            # Look for the message being replied to in previous and next messages
            for msg in previous_messages + next_messages:
                if msg.get("id") == reply_to_id:
                    reply_to_info = {
                        "id": msg.get("id"),
                        "sender_name": msg.get("sender_name"),
                        "text": msg.get("text", "")[:100] + ("..." if len(msg.get("text", "")) > 100 else "")
                    }
                    break
        
        # Create metadata
        metadata = {
            "id": message_id,
            "source": "telegram",
            "source_id": "telegram_ingestor",
            "chat_id": conversation_id,
            "conversation_id": conversation_id,  # Add for consistency with formats
            "chat_name": conversation_name,
            "is_group": is_group,
            "chat_type": chat_type,
            "timestamp": timestamp,
            "date": date,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "is_me": is_me,
            "previous_message_ids": previous_message_ids,
            "next_message_ids": next_message_ids,
            "neighboring_message_ids": previous_message_ids + next_message_ids,
            "reply_to_id": reply_to_id,
            "reply_to": reply_to_info
        }
        
        # Sanitize metadata to ensure it only contains types supported by ChromaDB
        return sanitize_metadata_for_vector_store(metadata)
    
    def _get_safe_filename(self, chat_id: str) -> str:
        """
        Convert chat_id to a safe filename.
        
        Args:
            chat_id: Chat ID
            
        Returns:
            str: Safe filename
        """
        # Replace characters that are problematic in filenames
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', str(chat_id))
        return safe_name
    
    async def _update_chat_history(self, chat_id: str, new_messages: List[Dict[str, Any]]) -> None:
        """
        Update chat history file for a specific chat_id.
        
        Args:
            chat_id: The chat ID
            new_messages: New messages to add to history
            
        Returns:
            None
        """
        try:
            safe_chat_id = self._get_safe_filename(chat_id)
            chat_file_path = os.path.join(self._chat_history_dir, f"{safe_chat_id}.json")
            
            # Initialize with new messages
            chat_history = {
                "chat_id": chat_id,
                "messages": new_messages,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            # Use lock for thread safety when reading/writing files
            async with self._lock:
                # Check if file already exists
                if os.path.exists(chat_file_path):
                    # Load existing chat history
                    with open(chat_file_path, 'r', encoding='utf-8') as f:
                        existing_history = json.load(f)
                        
                    # Create dictionary of existing message IDs for quick lookup
                    existing_message_ids = {msg.get("id", f"unknown_{i}"): i 
                                          for i, msg in enumerate(existing_history.get("messages", []))}
                    
                    # Merge new messages that don't already exist
                    merged_messages = existing_history.get("messages", [])
                    new_count = 0
                    
                    for msg in new_messages:
                        msg_id = msg.get("id", "")
                        if not msg_id or msg_id not in existing_message_ids:
                            merged_messages.append(msg)
                            new_count += 1
                    
                    # Sort by timestamp
                    merged_messages.sort(key=lambda m: m.get("timestamp", 0) or 0)
                    
                    # Update chat history
                    chat_history["messages"] = merged_messages
                    chat_history["message_count"] = len(merged_messages)
                    chat_history["last_updated"] = datetime.now(timezone.utc).isoformat()
                    
                    self.logger.info({
                        "action": "CHAT_HISTORY_UPDATED",
                        "message": f"Updated chat history for {chat_id}: added {new_count} new messages",
                        "data": {
                            "chat_id": chat_id,
                            "new_messages": new_count,
                            "total_messages": len(merged_messages)
                        }
                    })
                else:
                    # Creating new chat history file
                    chat_history["message_count"] = len(new_messages)
                    
                    self.logger.info({
                        "action": "CHAT_HISTORY_CREATED",
                        "message": f"Created new chat history for {chat_id} with {len(new_messages)} messages",
                        "data": {
                            "chat_id": chat_id,
                            "message_count": len(new_messages)
                        }
                    })
                
                # Write updated chat history
                with open(chat_file_path, 'w', encoding='utf-8') as f:
                    json.dump(chat_history, f, indent=2, ensure_ascii=False)
            
        except Exception as e:
            self.logger.error({
                "action": "CHAT_HISTORY_UPDATE_ERROR",
                "message": f"Failed to update chat history for {chat_id}: {str(e)}",
                "data": {
                    "chat_id": chat_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            })
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Check if the preprocessor is properly configured and functioning.
        
        Returns:
            Dict[str, Any]: Health status information
            
        Raises:
            PreprocessorError: If the health check encounters an error
        """
        health_result = {
            "healthy": False,
            "message": "Telegram preprocessor health check failed",
            "details": {
                "initialized": self._is_initialized,
                "config": {
                    "time_window_minutes": self._time_window_minutes,
                    "chunk_size": self._chunk_size,
                    "max_messages_per_chunk": self._max_messages_per_chunk,
                    "include_overlap": self._include_overlap,
                    "store_chat_history": self._store_chat_history,
                    "chat_history_dir": self._chat_history_dir
                }
            }
        }
        
        try:
            if not self._is_initialized:
                health_result["message"] = "Preprocessor not initialized"
                return health_result
                
            # Check chat history directory if storage is enabled
            if self._store_chat_history:
                chat_dir_exists = os.path.exists(self._chat_history_dir)
                chat_dir_writable = os.access(self._chat_history_dir, os.W_OK) if chat_dir_exists else False
                
                health_result["details"]["chat_history"] = {
                    "directory_exists": chat_dir_exists,
                    "directory_writable": chat_dir_writable
                }
                
                if not chat_dir_exists:
                    health_result["healthy"] = False
                    health_result["message"] = f"Chat history directory '{self._chat_history_dir}' does not exist"
                    return health_result
                    
                if not chat_dir_writable:
                    health_result["healthy"] = False
                    health_result["message"] = f"Chat history directory '{self._chat_history_dir}' is not writable"
                    return health_result
            
            # Test with a minimal message
            test_messages = [
                {
                    "id": "test_msg_1",
                    "conversation_id": "test_conv_1",
                    "text": "Hello, this is a test message",
                    "date": datetime.now().isoformat(),
                    "from_id": "user123",
                    "from_name": "Test User"
                }
            ]
            
            # Test the process method directly - using await instead of asyncio.run()
            try:
                test_result = await self.process(test_messages)
                
                if test_result and len(test_result) > 0:
                    health_result["healthy"] = True
                    health_result["message"] = "Preprocessor is healthy"
                    health_result["details"]["test_success"] = True
                    health_result["details"]["test_results"] = {
                        "documents_created": len(test_result)
                    }
            except Exception as e:
                health_result["message"] = f"Health check test failed: {str(e)}"
                health_result["details"]["error"] = str(e)
                health_result["details"]["error_type"] = type(e).__name__
            
            return health_result
            
        except Exception as e:
            self.logger.error({
                "action": "PREPROCESSOR_HEALTHCHECK_ERROR",
                "message": f"Health check failed: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            health_result["details"]["error"] = str(e)
            health_result["details"]["error_type"] = type(e).__name__
            
            return health_result 