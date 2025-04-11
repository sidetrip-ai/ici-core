"""
WhatsApp preprocessor implementation.
"""

import os
import re
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set

import time
from ici.core.interfaces.preprocessor import Preprocessor
from ici.adapters.loggers import StructuredLogger
from ici.core.exceptions import PreprocessorError
from ici.utils.config import get_component_config, load_config
from ici.utils.metadata_utils import sanitize_metadata_for_vector_store


class WhatsAppPreprocessor(Preprocessor):
    """
    Preprocessor for WhatsApp messages.
    
    This preprocessor transforms raw WhatsApp data into standardized documents
    with appropriate context windows.
    """
    
    def __init__(self, ingestor=None, logger_name: str = "whatsapp_preprocessor"):
        """
        Initialize the WhatsApp preprocessor.
        
        Args:
            ingestor: Optional WhatsApp ingestor to get user information from
            logger_name: Name for the logger instance
        """
        self.logger = StructuredLogger(name=logger_name)
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        
        # Chunking parameters with defaults
        self._time_window_minutes = 15
        self._chunk_size = 512
        self._max_messages_per_chunk = 10
        self._include_overlap = True
        
        # User identification
        self._my_user_id = None
        self._ingestor = ingestor
        
        # Chat history storage
        self._store_chat_history = True
        self._chat_history_dir = None
        
        self._is_initialized = False
        self._lock = asyncio.Lock()  # For thread safety
    
    async def initialize(self) -> None:
        """
        Initialize the preprocessor with configuration from config.yaml.
        
        Returns:
            None
            
        Raises:
            PreprocessorError: If initialization fails
        """
        try:
            self.logger.info({
                "action": "PREPROCESSOR_INIT_START",
                "message": "Initializing WhatsApp preprocessor"
            })
            
            # Load configuration parameters if available
            try:
                preprocessor_config = get_component_config("preprocessors.whatsapp", self._config_path)
                
                # Extract chunking parameters with defaults
                self._time_window_minutes = int(preprocessor_config.get("time_window_minutes", 15))
                self._chunk_size = int(preprocessor_config.get("chunk_size", 512))
                self._max_messages_per_chunk = int(preprocessor_config.get("max_messages_per_chunk", 10))
                self._include_overlap = bool(preprocessor_config.get("include_overlap", True))
                
                # Extract user identification - prioritize ingestor if available
                if self._ingestor:
                    try:
                        ingestor_user_id = self._ingestor.get_current_user_id()
                        print("--------------------------------")
                        print("ingestor_user_id")
                        print(ingestor_user_id)
                        print("--------------------------------")
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
                    self._chat_history_dir = preprocessor_config.get("chat_history_dir", os.path.join("db", "whatsapp", "chats"))

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
                "message": "WhatsApp preprocessor initialized successfully"
            })
            
        except Exception as e:
            self.logger.error({
                "action": "PREPROCESSOR_INIT_ERROR",
                "message": f"Failed to initialize WhatsApp preprocessor: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise PreprocessorError(f"Preprocessor initialization failed: {str(e)}") from e
    
    async def preprocess(self, raw_data: Any) -> List[Dict[str, Any]]:
        """
        Transform raw WhatsApp data into standardized documents with context windows.
        
        Args:
            raw_data: Raw data from the WhatsApp ingestor
                Expected to be a dict with 'conversations' mapping chat_ids to message lists
                
        Returns:
            List[Dict[str, Any]]: List of standardized documents with 'text' and 'metadata'
            
        Raises:
            PreprocessorError: If preprocessing fails
        """
        try:
            if not isinstance(raw_data, dict):
                raise PreprocessorError(f"Expected dict, got {type(raw_data).__name__}")
            
            conversations = raw_data.get("conversations", {})
            if not conversations:
                self.logger.info({
                    "action": "NO_MESSAGES",
                    "message": "No messages to preprocess"
                })
                return []
            
            # Save complete export
            with open("db/whatsapp/chat_export.json", "w", encoding="utf-8") as f:
                json.dump(raw_data, f, indent=2, ensure_ascii=False)
            
            # Process each chat
            documents = []
            total_messages = 0
            
            for chat_id, messages in conversations.items():
                # Save/update individual chat history if enabled
                if self._store_chat_history:
                    await self._update_chat_history(chat_id, messages)
                
                # Get chat info
                chat_name = self._extract_chat_name(chat_id, messages)
                is_group = self._is_group_chat(chat_id, messages)
                chat_type = "group" if is_group else "private"
                
                # Filter valid messages and sort by timestamp
                valid_messages = [m for m in messages if self._is_valid_message(m)]
                if not valid_messages:
                    continue
                    
                sorted_messages = sorted(valid_messages, key=lambda m: m.get("timestamp", 0))
                total_messages += len(sorted_messages)
                
                # Process each message with context
                chat_documents = self._process_messages_with_context(
                    sorted_messages, 
                    chat_id, 
                    chat_name, 
                    is_group, 
                    chat_type
                )
                documents.extend(chat_documents)
            
            self.logger.info({
                "action": "PREPROCESSING_COMPLETE",
                "message": f"Processed {total_messages} messages into {len(documents)} documents",
                "data": {
                    "message_count": total_messages,
                    "document_count": len(documents),
                    "chat_count": len(conversations)
                }
            })
            
            return documents
            
        except Exception as e:
            error_message = f"Failed to preprocess WhatsApp messages: {str(e)}"
            self.logger.error({
                "action": "PREPROCESSING_ERROR",
                "message": error_message,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise PreprocessorError(error_message) from e
    
    def _is_reply(self, message: Dict[str, Any]) -> bool:
        """
        Check if a message is a reply to another message.
        
        Args:
            message: Message to check
            
        Returns:
            bool: True if it's a reply, False otherwise
        """
        return bool(
            message.get("hasQuotedMsg", False) or 
            message.get("quotedMsgId") or 
            message.get("quoted_msg_id") or
            message.get("reply_to_id")
        )

    def _extract_reply_info(self, message: Dict[str, Any], all_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract information about the message being replied to.
        
        Args:
            message: Message to extract reply info from
            all_messages: All messages in the chat for reference lookup
            
        Returns:
            Dict[str, Any]: Reply information or None if not a reply
        """
        if not self._is_reply(message):
            return None
        
        # Get the ID of the message being replied to
        quoted_msg_id = (
            message.get("quotedMsgId") or 
            message.get("quoted_msg_id") or 
            message.get("reply_to_id")
        )
        
        if not quoted_msg_id:
            return None
        
        # Look for the quoted message across all messages
        for msg in all_messages:
            if msg.get("id") == quoted_msg_id:
                return {
                    "id": quoted_msg_id,
                    "sender_name": self._extract_author(msg),
                    "timestamp": self._extract_timestamp(msg),
                    "text": (msg.get("text", "") or msg.get("body", ""))[:100] + 
                           ("..." if len(msg.get("text", "") or msg.get("body", "")) > 100 else "")
                }
        
        # Fallback for missing message data
        return {
            "id": quoted_msg_id,
            "sender_name": message.get("quotedParticipant", "Unknown"),
            "text": message.get("quotedMsg", "Incomplete message data..."),
            "is_partial": True
        }

    def _process_messages_with_context(
        self, 
        sorted_messages: List[Dict[str, Any]],
        chat_id: str,
        chat_name: str,
        is_group: bool,
        chat_type: str
    ) -> List[Dict[str, Any]]:
        """
        Process messages with context windows to create documents.
        Each message becomes a separate document with neighboring message IDs in metadata.
        
        Args:
            sorted_messages: List of messages sorted by timestamp
            chat_id: The ID of the chat
            chat_name: The name of the chat
            is_group: Whether the chat is a group chat
            chat_type: 'group' or 'private'
            
        Returns:
            List[Dict[str, Any]]: List of documents
        """
        documents = []
        
        for i, current_message in enumerate(sorted_messages):
            # Clearly separate the messages into primary, previous, and next
            primary_message = current_message
            
            # Get previous messages (up to 5)
            start_idx = max(0, i - 5)
            previous_messages = sorted_messages[start_idx:i]
            
            # Get next messages (up to 5)
            end_idx = min(len(sorted_messages), i + 6)  # +6 because end index is exclusive
            next_messages = sorted_messages[i+1:end_idx]
            
            # Format raw message text
            message_text = self._format_conversation([primary_message])
            
            # Extract main message details
            message_id = primary_message.get("id", "")
            main_author = self._extract_author(primary_message)
            main_timestamp = self._extract_timestamp(primary_message)
            main_datetime = self._format_datetime(main_timestamp)
            
            # Extract IDs from previous and next messages
            previous_message_ids = [msg.get("id", "") for msg in previous_messages]
            next_message_ids = [msg.get("id", "") for msg in next_messages]
            
            # Extract reply information
            is_reply = self._is_reply(primary_message)
            reply_to_id = None
            reply_data = None
            
            if is_reply:
                # Get the ID of the message being replied to
                reply_to_id = (
                    primary_message.get("quotedMsgId") or 
                    primary_message.get("quoted_msg_id") or 
                    primary_message.get("reply_to_id")
                )
                
                # Get detailed information about the replied message
                reply_data = self._extract_reply_info(primary_message, sorted_messages)
                
                # Log for debugging
                self.logger.debug({
                    "action": "REPLY_INFO_EXTRACTED",
                    "message": f"Extracted reply information for message {message_id}",
                    "data": {
                        "message_id": message_id,
                        "reply_to_id": reply_to_id,
                        "reply_data": reply_data
                    }
                })
            
            # Create metadata
            metadata = {
                "source": "whatsapp",
                "chat_id": chat_id,
                "conversation_id": chat_id,  # Add for consistency
                "chat_name": chat_name,
                "is_group": is_group,
                "chat_type": chat_type,
                "author": main_author,
                "sender_name": main_author,
                "timestamp": main_timestamp,
                "date": main_datetime,
                "message_id": message_id,
                "previous_message_ids": previous_message_ids,
                "next_message_ids": next_message_ids,
                "neighboring_message_ids": previous_message_ids + next_message_ids,
                "is_reply": is_reply,
                "reply_to_id": reply_to_id,
                "reply_data": reply_data
            }
            
            # Sanitize metadata for vector store compatibility
            sanitized_metadata = sanitize_metadata_for_vector_store(metadata)
            
            # Create document with sanitized metadata
            document = {
                "id": message_id,
                "text": message_text,
                "metadata": sanitized_metadata
            }
            
            documents.append(document)
        
        return documents
    
    def _is_valid_message(self, message: Dict[str, Any]) -> bool:
        """
        Check if a message is valid for processing.
        
        Args:
            message: Message to check
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Skip non-text messages or empty messages
        if message.get("type") != "chat" and (not message.get("body") or message.get("body").strip() == ""):
            return False
            
        return True
    
    def _extract_chat_name(self, chat_id: str, messages: List[Dict[str, Any]]) -> str:
        """
        Extract chat name from messages context.
        
        Args:
            chat_id: The chat ID
            messages: List of messages
            
        Returns:
            str: Chat name
        """
        # Try to get from messages
        for message in messages:
            if "chatName" in message:
                return message["chatName"]
        
        # If not found, use chat ID as fallback
        return f"Chat {chat_id}"
    
    def _is_group_chat(self, chat_id: str, messages: List[Dict[str, Any]]) -> bool:
        """
        Determine if this is a group chat.
        
        Args:
            chat_id: The chat ID
            messages: List of messages
            
        Returns:
            bool: True if group chat, False otherwise
        """
        # Try to get from messages first
        for message in messages:
            if "isGroup" in message:
                return message["isGroup"]
        
        # WhatsApp group chat IDs typically end with @g.us
        # While private chats end with @c.us
        if "@g.us" in chat_id:
            return True
        if "@c.us" in chat_id:
            return False
        
        # If we can't determine from chat_id or message data
        # Check if there are multiple different authors in the chat
        authors = set()
        for message in messages:
            author = self._extract_author(message)
            if author != "Me" and author != "Unknown":
                authors.add(author)
        
        # If more than one distinct author (besides "Me"), likely a group
        return len(authors) > 1
    
    def _extract_author(self, message: Dict[str, Any]) -> str:
        """
        Extract author name from message.
        
        Args:
            message: Message data
            
        Returns:
            str: Author name
        """
        if message.get("fromMe"):
            return "Me"
        return message.get("author", message.get("sender_name", message.get("notifyName", "Unknown")))
    
    def _extract_timestamp(self, message: Dict[str, Any]) -> int:
        """
        Extract timestamp from message.
        
        Args:
            message: Message data
            
        Returns:
            int: Timestamp in milliseconds
        """
        return message.get("timestamp", 0)
    
    def _format_datetime(self, timestamp: int) -> str:
        """
        Format timestamp as readable datetime string.
        
        Args:
            timestamp: Timestamp in milliseconds
            
        Returns:
            str: Formatted datetime
        """
        if timestamp:
            dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        return "Unknown time"
    
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
                    merged_messages.sort(key=lambda m: m.get("timestamp", 0))
                    
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
    
    def _get_safe_filename(self, chat_id: str) -> str:
        """
        Convert chat_id to a safe filename.
        
        Args:
            chat_id: Chat ID
            
        Returns:
            str: Safe filename
        """
        # Replace characters that are problematic in filenames
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', chat_id)
        return safe_name
    
    def _extract_participant_names(self, messages: List[Dict[str, Any]]) -> List[str]:
        """
        Extract unique participant names from messages.
        
        Args:
            messages: List of messages
            
        Returns:
            List[str]: List of unique participant names
        """
        participants = set()
        
        for message in messages:
            sender_name = self._extract_author(message)
            if sender_name and sender_name != "Unknown" and sender_name != "System":
                participants.add(sender_name)
        
        return list(participants)
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Perform a health check of the preprocessor.
        
        Returns:
            Dict[str, Any]: Health check results
        """
        is_healthy = True
        message = "WhatsApp preprocessor is healthy"
        details = {
            "chunk_size": self._chunk_size,
            "include_overlap": self._include_overlap,
            "max_messages_per_chunk": self._max_messages_per_chunk,
            "time_window_minutes": self._time_window_minutes,
            "store_chat_history": self._store_chat_history
        }
        
        # Check if chat history directory exists if storage is enabled
        if self._store_chat_history:
            if not os.path.exists(self._chat_history_dir):
                is_healthy = False
                message = f"Chat history directory '{self._chat_history_dir}' does not exist"
            
            details["chat_history_dir"] = self._chat_history_dir
            details["chat_history_dir_exists"] = os.path.exists(self._chat_history_dir)
        
        return {
            "healthy": is_healthy,
            "message": message,
            "details": details
        }

    def _format_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format a message as raw text without additional formatting.
        
        Args:
            messages: List of WhatsApp message dictionaries. We'll only use the current message.
            
        Returns:
            str: Raw message text
        """
        if not messages:
            return ""
        
        # Just return the raw text of the message
        message = messages[0]  # Use the first message as the primary one
        
        # Get the basic text
        text = message.get("text", "") or message.get("body", "")
        
        # Add media information if present
        if message.get("has_media", False):
            media_type = message.get("media_type", "unknown")
            media_caption = message.get("media_caption", "")
            
            if media_caption:
                text += f" {media_caption}"
            
            text += f" [{media_type.capitalize()} attachment]"
        
        return text 