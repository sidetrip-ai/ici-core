"""
WhatsApp preprocessor implementation.
"""

import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from ici.core.interfaces.preprocessor import Preprocessor
from ici.adapters.loggers import StructuredLogger
from ici.core.exceptions import PreprocessorError
from ici.utils.config import get_component_config, load_config


class WhatsAppPreprocessor(Preprocessor):
    """
    Preprocesses raw WhatsApp message data into a standardized document format.
    
    This preprocessor transforms raw WhatsApp messages into a format suitable
    for embedding and storage in the vector database.
    """
    
    def __init__(self, logger_name: str = "whatsapp_preprocessor"):
        """
        Initialize the WhatsApp preprocessor.
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = StructuredLogger(name=logger_name)
        self._config = None
        self._chunk_size = 512
        self._include_overlap = True
        self._max_messages_per_chunk = 10
        self._time_window_minutes = 15
        self._config_path = None
    
    async def initialize(self) -> None:
        """
        Initialize the preprocessor with configuration from config.yaml.
        
        Returns:
            None
            
        Raises:
            PreprocessorError: If initialization fails
        """
        try:
            # Load config from file
            self._config_path = self._config_path or "config.yaml"
            whatsapp_config = get_component_config("preprocessors.whatsapp", self._config_path)
            
            if whatsapp_config:
                # Apply configuration settings
                if "chunk_size" in whatsapp_config:
                    self._chunk_size = int(whatsapp_config["chunk_size"])
                
                if "include_overlap" in whatsapp_config:
                    self._include_overlap = bool(whatsapp_config["include_overlap"])
                
                if "max_messages_per_chunk" in whatsapp_config:
                    self._max_messages_per_chunk = int(whatsapp_config["max_messages_per_chunk"])
                
                if "time_window_minutes" in whatsapp_config:
                    self._time_window_minutes = int(whatsapp_config["time_window_minutes"])
            
            self.logger.info({
                "action": "PREPROCESSOR_INITIALIZED",
                "message": "WhatsApp preprocessor initialized successfully",
                "data": {
                    "chunk_size": self._chunk_size,
                    "include_overlap": self._include_overlap,
                    "max_messages_per_chunk": self._max_messages_per_chunk,
                    "time_window_minutes": self._time_window_minutes
                }
            })
            
        except Exception as e:
            error_message = f"Failed to initialize WhatsApp preprocessor: {str(e)}"
            self.logger.error({
                "action": "INITIALIZATION_ERROR",
                "message": error_message,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise PreprocessorError(error_message) from e
    
    async def preprocess(self, raw_data: Any) -> List[Dict[str, Any]]:
        """
        Transform raw WhatsApp data into standardized documents.
        
        Args:
            raw_data: Raw data from the WhatsApp ingestor
                Expected to be a dict with 'messages' and 'conversations' lists
                
        Returns:
            List[Dict[str, Any]]: List of standardized documents with 'text' and 'metadata'
            
        Raises:
            PreprocessorError: If preprocessing fails
        """
        try:
            if not isinstance(raw_data, dict):
                raise PreprocessorError(f"Expected dict, got {type(raw_data).__name__}")
            
            messages = raw_data.get("messages", [])
            conversations = raw_data.get("conversations", [])
            
            if not messages:
                self.logger.info({
                    "action": "NO_MESSAGES",
                    "message": "No messages to preprocess"
                })
                return []
            
            # Create a lookup for conversation metadata
            conversation_lookup = {conv["id"]: conv for conv in conversations}
            
            # Sort messages by timestamp
            sorted_messages = sorted(
                messages,
                key=lambda m: m.get("timestamp", 0)
            )
            
            # Group messages into conversation chunks
            conversation_chunks = self._group_messages_into_chunks(sorted_messages, conversation_lookup)
            
            # Convert conversation chunks to standardized documents
            documents = self._chunks_to_documents(conversation_chunks)
            
            self.logger.info({
                "action": "PREPROCESSING_COMPLETE",
                "message": f"Processed {len(messages)} messages into {len(documents)} documents",
                "data": {
                    "message_count": len(messages),
                    "document_count": len(documents)
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
    
    def _group_messages_into_chunks(
        self, 
        messages: List[Dict[str, Any]], 
        conversation_lookup: Dict[str, Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """
        Group messages into conversation chunks based on time windows and maximum messages.
        
        Args:
            messages: List of messages sorted by timestamp
            conversation_lookup: Dictionary mapping conversation IDs to conversation data
            
        Returns:
            List[List[Dict[str, Any]]]: List of message chunks
        """
        conversation_chunks = []
        current_chunk = []
        current_chat_id = None
        chunk_start_time = None
        
        for message in messages:
            # Skip non-text messages
            if message.get("type") != "chat" and (not message.get("body") or message.get("body").strip() == ""):
                continue
            
            chat_id = message.get("chatId")
            timestamp = message.get("timestamp", 0)
            
            if timestamp:
                message_time = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
            else:
                message_time = datetime.now(tz=timezone.utc)
            
            # Start a new chunk if:
            # 1. This is the first message
            # 2. The chat ID changes
            # 3. The chunk has reached max messages
            # 4. The time window has been exceeded
            start_new_chunk = (
                not current_chunk or
                chat_id != current_chat_id or
                len(current_chunk) >= self._max_messages_per_chunk or
                (chunk_start_time and (message_time - chunk_start_time) > timedelta(minutes=self._time_window_minutes))
            )
            
            if start_new_chunk and current_chunk:
                conversation_chunks.append(current_chunk)
                current_chunk = []
            
            # Set the parameters for the new chunk if starting fresh
            if not current_chunk:
                current_chat_id = chat_id
                chunk_start_time = message_time
            
            # Add message to the current chunk
            current_chunk.append(message)
        
        # Add the last chunk if not empty
        if current_chunk:
            conversation_chunks.append(current_chunk)
        
        return conversation_chunks
    
    def _chunks_to_documents(self, chunks: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Convert message chunks to standardized documents.
        
        Args:
            chunks: List of message chunks
            
        Returns:
            List[Dict[str, Any]]: List of standardized documents
        """
        documents = []
        
        for chunk in chunks:
            if not chunk:
                continue
            
            # Get message metadata from the first message in the chunk
            first_message = chunk[0]
            chat_id = first_message.get("chatId", "")
            chat_name = first_message.get("chat_name", "")
            
            # Format the chunk of messages into a conversation text
            chunk_text = self._format_messages_as_text(chunk)
            
            # Get timestamp from first and last message for the timeframe
            first_timestamp = first_message.get("timestamp", 0)
            last_timestamp = chunk[-1].get("timestamp", 0)
            
            # Create document metadata
            metadata = {
                "source": "whatsapp",
                "conversation_id": chat_id,
                "conversation_name": chat_name,
                "start_timestamp": first_timestamp,
                "end_timestamp": last_timestamp,
                "message_count": len(chunk),
                "participants": ", ".join(self._extract_participant_names(chunk))
            }
            
            # Create the document
            document = {
                "text": chunk_text,
                "metadata": metadata
            }
            
            documents.append(document)
        
        return documents
    
    def _format_messages_as_text(self, messages: List[Dict[str, Any]]) -> str:
        """
        Format a list of messages as a conversation text.
        
        Args:
            messages: List of message objects
            
        Returns:
            str: Formatted conversation text
        """
        formatted_lines = []
        
        for message in messages:
            # Skip non-text messages
            if message.get("type") != "chat" and (not message.get("body") or message.get("body").strip() == ""):
                continue
            
            # Format timestamp
            timestamp = message.get("timestamp", 0)
            if timestamp:
                time_str = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            else:
                time_str = "[Unknown time]"
            
            # Get sender info
            sender = "Me" if message.get("fromMe") else message.get("sender_name", "Unknown")
            
            # Format message text
            body = message.get("body", "").strip()
            
            # Add to formatted lines
            formatted_lines.append(f"[{time_str}] {sender}: {body}")
        
        return "\n".join(formatted_lines)
    
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
            sender_name = message.get("author", "").strip()
            if sender_name and sender_name != "System":
                participants.add(sender_name)
        
        return list(participants)
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Perform a health check of the preprocessor.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        return {
            "status": "healthy",
            "config": {
                "chunk_size": self._chunk_size,
                "include_overlap": self._include_overlap,
                "max_messages_per_chunk": self._max_messages_per_chunk,
                "time_window_minutes": self._time_window_minutes
            }
        } 