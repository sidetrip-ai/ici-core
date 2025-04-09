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


class TelegramPreprocessor(Preprocessor):
    """
    Preprocessor for Telegram messages.
    
    This preprocessor transforms raw Telegram messages into standardized documents
    by grouping them into time-based windows and formatting them as conversations.
    """
    
    def __init__(self, logger_name: str = "telegram_preprocessor"):
        """
        Initialize the TelegramPreprocessor.
        
        Args:
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
        
        # Chat history storage settings
        self._store_chat_history = True
        self._chat_history_dir = "db/telegram_chats"
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
                
                # Extract chat history storage settings
                if "store_chat_history" in preprocessor_config:
                    self._store_chat_history = bool(preprocessor_config.get("store_chat_history"))
                
                if "chat_history_dir" in preprocessor_config:
                    self._chat_history_dir = preprocessor_config.get("chat_history_dir")
                
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
                        "chat_history_dir": self._chat_history_dir
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
            
            # Group messages by time windows
            message_groups = self._group_messages_by_time(messages)
            
            self.logger.info({
                "action": "PREPROCESSOR_GROUPED",
                "message": f"Grouped messages into {len(message_groups)} time windows",
                "data": {"group_count": len(message_groups)}
            })
            
            # Process each group into standardized documents
            documents = []
            for group in message_groups:
                # Split large groups into chunks
                chunks = self._create_chunks(group)
                
                for chunk in chunks:
                    # Format conversation text
                    conversation_text = self._format_conversation(chunk)
                    
                    # Extract metadata
                    metadata = self._create_metadata(chunk)
                    
                    # Create standardized document with UUID-based ID
                    document = {
                        "id": str(uuid.uuid4()),
                        "text": conversation_text,
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
        Format a group of messages into a conversation text with rich context.
        
        Args:
            messages: List of messages to format
            
        Returns:
            Formatted conversation text with metadata and context
        """
        if not messages:
            return ""
        
        # Get chat metadata from the first message
        first_msg = messages[0]
        chat_name = first_msg.get("conversation_name", "Unknown Chat")
        chat_type = first_msg.get("chat_type", "private")
        is_group = first_msg.get("is_group", False)
        
        # Start with a metadata header
        formatted_lines = [
            f"(chatname: {chat_name} chattype: {chat_type} source: telegram messages: {len(messages)})"
        ]
        
        # Track active speaker
        current_sender = None
        
        # Format each message with sender and relationship context
        for i, message in enumerate(messages):
            # Get sender information
            sender_name = message.get("sender_name")
            if not sender_name:
                sender_name = message.get("conversation_username") or message.get("conversation_name") or "Unknown"
            
            # Get formatted date
            date_str = "Unknown date"
            if message.get("date"):
                try:
                    date_obj = datetime.fromisoformat(message.get("date"))
                    date_str = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    pass
            
            # Check if this is a reply
            is_reply = message.get("is_reply", False)
            replied_to = message.get("replied_to_message", {})
            
            # Add message prefix with sender and datetime
            if sender_name != current_sender or is_reply:
                # Add reply context if applicable
                if is_reply and replied_to:
                    replied_text = replied_to.get("text", "")
                    # Truncate long replied text
                    if len(replied_text) > 50:
                        replied_text = replied_text[:47] + "..."
                    replied_sender = replied_to.get("sender_name", "Someone")
                    
                    formatted_lines.append(f"{sender_name} [replying to {replied_sender}: {replied_text}] ({date_str}):")
                else:
                    formatted_lines.append(f"{sender_name} ({date_str}):")
                    
                current_sender = sender_name
            
            # Add message text with proper indentation
            message_text = message.get("text", "")
            if message_text is None:
                message_text = ""
            message_text = message_text.strip()
            
            if message_text:
                if current_sender == sender_name and not is_reply:
                    # Continue previous speaker's messages with indentation
                    formatted_lines.append(f"  {message_text}")
                else:
                    # First line after speaker change has no indentation
                    formatted_lines.append(f"{message_text}")
        
        # Join lines with newlines
        return "\n".join(formatted_lines)
    
    def _create_metadata(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create rich metadata for a group of messages.
        
        Args:
            messages: List of messages in a chunk
            
        Returns:
            Metadata dictionary
        """
        if not messages:
            return {}
        
        # Extract common data
        first_message = messages[0]
        last_message = messages[-1]
        
        # Get chat info
        conversation_id = first_message.get("conversation_id")
        conversation_name = first_message.get("conversation_name")
        is_group = first_message.get("is_group", False)
        chat_type = first_message.get("chat_type", "private")
        
        # Get timestamps
        try:
            start_date = datetime.fromisoformat(first_message.get("date", ""))
            end_date = datetime.fromisoformat(last_message.get("date", ""))
            timestamp_start = int(start_date.timestamp())
            timestamp_end = int(end_date.timestamp())
            date_start = start_date.isoformat()
            date_end = end_date.isoformat()
        except:
            # Fallback if dates are invalid
            now = datetime.now(timezone.utc)
            timestamp_start = timestamp_end = int(now.timestamp())
            date_start = date_end = now.isoformat()
        
        # Collect message IDs
        message_ids = [msg.get("id") for msg in messages]
        
        # Collect unique senders
        senders = set()
        for msg in messages:
            sender = msg.get("sender_name")
            if not sender:
                sender = msg.get("conversation_username") or msg.get("conversation_name")
            if sender:
                senders.add(sender)
        
        # Track message relationships
        reply_count = sum(1 for msg in messages if msg.get("is_reply", False))
        
        # Create metadata
        metadata = {
            "source": "telegram",
            "source_id": "telegram_ingestor",
            "chat_id": conversation_id,
            "chat_name": conversation_name,
            "is_group": is_group,
            "chat_type": chat_type,
            "timestamp_start": timestamp_start,
            "timestamp_end": timestamp_end,
            "date_start": date_start,
            "date_end": date_end,
            "message_ids": message_ids,
            "message_count": len(messages),
            "is_chunked": len(messages) < self._max_messages_per_chunk,
            "participants": list(senders),
            "reply_count": reply_count,
            "time_window_minutes": self._time_window_minutes
        }
        
        # Sanitize metadata to ensure it only contains types supported by ChromaDB
        return self._sanitize_metadata(metadata)
    
    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize metadata to ensure compatibility with vector stores.
        
        Converts lists and other complex types to string representations,
        as ChromaDB only supports str, int, float, and bool metadata values.
        
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