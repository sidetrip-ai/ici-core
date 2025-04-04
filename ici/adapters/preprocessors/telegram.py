"""
Telegram preprocessor implementation.

This module provides a Preprocessor implementation for Telegram data,
handling message grouping, chunking, and metadata extraction.
"""

import os
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import uuid
import asyncio
import json

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
                
                self.logger.info({
                    "action": "PREPROCESSOR_CONFIG_LOADED",
                    "message": "Loaded preprocessor configuration",
                    "data": {
                        "time_window_minutes": self._time_window_minutes,
                        "chunk_size": self._chunk_size,
                        "max_messages_per_chunk": self._max_messages_per_chunk,
                        "include_overlap": self._include_overlap
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
            raw_data: Raw data from TelegramIngestor, expected to be a dict with 'messages' list
            
        Returns:
            List[Dict[str, Any]]: List of standardized documents with 'text' and 'metadata'
            
        Raises:
            PreprocessorError: If preprocessing fails
        """
        if not self._is_initialized:
            raise PreprocessorError("Preprocessor not initialized. Call initialize() first.")
        
        try:
            # Extract messages from raw data
            if not isinstance(raw_data, dict) or "messages" not in raw_data:
                raise PreprocessorError("Invalid raw data format. Expected dict with 'messages' list.")
            
            messages = raw_data.get("messages", [])
            
            if not messages:
                self.logger.info({
                    "action": "PREPROCESSOR_NO_MESSAGES",
                    "message": "No messages to process"
                })
                return []
            
            # Process messages directly using the async process method
            return await self.process(messages)
            
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
        Format a group of messages into a conversation text.
        
        Args:
            messages: List of messages to format
            
        Returns:
            Formatted conversation text
        """
        if not messages:
            return ""
        
        formatted_lines = []
        current_sender = None
        
        for message in messages:
            # Get sender name (prefer username, fall back to conversation_name)
            sender = message.get("conversation_username") or message.get("conversation_name") or "Unknown"
            
            # Only add sender name when it changes
            if sender != current_sender:
                formatted_lines.append(f"{sender}: {message.get('text', '')}")
                current_sender = sender
            else:
                # Continue same speaker's message
                formatted_lines.append(f"  {message.get('text', '')}")
        
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
        
        # Get timestamps
        start_date = datetime.fromisoformat(first_message.get("date"))
        end_date = datetime.fromisoformat(last_message.get("date"))
        
        # Collect message IDs
        message_ids = [msg.get("id") for msg in messages]
        
        # Collect unique senders
        senders = set()
        for msg in messages:
            sender = msg.get("conversation_username") or msg.get("conversation_name")
            if sender:
                senders.add(sender)
        
        # Create metadata
        metadata = {
            "source": "telegram",
            "source_id": "telegram_ingestor",
            "chat_id": conversation_id,
            "chat_name": conversation_name,
            "timestamp_start": int(start_date.timestamp()),
            "timestamp_end": int(end_date.timestamp()),
            "date_start": start_date.isoformat(),
            "date_end": end_date.isoformat(),
            "message_ids": message_ids,
            "message_count": len(messages),
            "is_chunked": len(messages) < self._max_messages_per_chunk,
            "participants": list(senders)
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
                    "include_overlap": self._include_overlap
                }
            }
        }
        
        try:
            if not self._is_initialized:
                health_result["message"] = "Preprocessor not initialized"
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