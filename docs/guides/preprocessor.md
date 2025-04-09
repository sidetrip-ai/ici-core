# Preprocessor Component Guide

## Overview

A Preprocessor transforms raw data from ingestors into standardized documents suitable for embedding and storage in a vector database. It performs tasks such as message grouping, text normalization, metadata extraction, and format conversion.

## Interface

All preprocessors must implement the `Preprocessor` interface defined in `ici/core/interfaces/preprocessor.py`:

```python
class Preprocessor(ABC):
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the preprocessor with configuration parameters."""
        pass
        
    @abstractmethod
    async def preprocess(self, raw_data: Any) -> List[Dict[str, Any]]:
        """
        Transform raw data into standardized documents.
        
        Args:
            raw_data: Data from an ingestor, typically a dictionary with messages and conversations
            
        Returns:
            List[Dict[str, Any]]: List of standardized documents
        """
        pass
```

## Expected Input and Output

### Input Format

Preprocessors typically receive data from ingestors in this format:

```python
{
    "messages": [
        {
            "id": "unique_message_id",
            "text": "Message content",
            "date": "2023-06-15T12:34:56+00:00",
            "conversation_id": "chat_123",
            "conversation_name": "Chat Name",
            "sender_id": "user_456",
            "sender_name": "User Name",
            "timestamp": 1686835626,
            # Other message-specific fields
        },
        # More messages...
    ],
    "conversations": [
        {
            "id": "chat_123",
            "name": "Chat Name",
            "type": "direct",
            # Other conversation-specific fields
        },
        # More conversations...
    ]
}
```

### Output Format

Preprocessors should output a list of standardized documents:

```python
[
    {
        "id": "unique_document_id",  # Usually a generated UUID
        "text": "Formatted document text that combines multiple messages",
        "metadata": {
            "source": "platform_name",  # e.g., "telegram", "whatsapp"
            "conversation_id": "chat_123",
            "conversation_name": "Chat Name",
            "participants": ["User 1", "User 2"],
            "timestamp": 1686835626,
            "start_date": "2023-06-15T12:30:00+00:00",
            "end_date": "2023-06-15T12:45:00+00:00",
            # Other metadata useful for retrieval/filtering
        }
    },
    # More documents...
]
```

## Implementing a Custom Preprocessor

Here's a step-by-step guide to implementing a custom preprocessor:

### 1. Create a new class

Create a new file in `ici/adapters/preprocessors/` for your custom preprocessor:

```python
"""
CustomSource preprocessor implementation.
"""

import os
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from ici.core.interfaces.preprocessor import Preprocessor
from ici.core.exceptions import PreprocessorError
from ici.adapters.loggers import StructuredLogger
from ici.utils.config import get_component_config

class CustomSourcePreprocessor(Preprocessor):
    """
    Preprocessor for CustomSource data.
    
    This preprocessor transforms raw data from CustomSource into standardized documents
    by grouping messages, formatting text, and extracting metadata.
    """
    
    def __init__(self, logger_name: str = "custom_preprocessor"):
        """
        Initialize the CustomSource preprocessor.
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = StructuredLogger(name=logger_name)
        self._is_initialized = False
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        
        # Default configuration
        self._time_window_minutes = 15  # Group messages within this time window
        self._chunk_size = 512  # Target character count per document
        self._max_messages_per_chunk = 10  # Maximum messages per document
        self._include_overlap = True  # Include overlap between chunks
```

### 2. Implement the initialize method

Load your configuration from config.yaml:

```python
async def initialize(self) -> None:
    """
    Initialize the preprocessor with configuration parameters.
    
    Loads configuration from config.yaml and sets up processing parameters.
    
    Returns:
        None
        
    Raises:
        PreprocessorError: If initialization fails
    """
    try:
        self.logger.info({
            "action": "PREPROCESSOR_INIT_START",
            "message": "Initializing CustomSource preprocessor"
        })
        
        # Load preprocessor configuration
        try:
            preprocessor_config = get_component_config("preprocessors.custom_source", self._config_path)
            
            # Extract configuration with defaults
            if preprocessor_config:
                self._time_window_minutes = int(preprocessor_config.get("time_window_minutes", self._time_window_minutes))
                self._chunk_size = int(preprocessor_config.get("chunk_size", self._chunk_size))
                self._max_messages_per_chunk = int(preprocessor_config.get("max_messages_per_chunk", self._max_messages_per_chunk))
                self._include_overlap = bool(preprocessor_config.get("include_overlap", self._include_overlap))
            
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
                "action": "PREPROCESSOR_CONFIG_WARNING",
                "message": f"Failed to load configuration: {str(e)}. Using defaults.",
                "data": {"error": str(e)}
            })
        
        self._is_initialized = True
        
        self.logger.info({
            "action": "PREPROCESSOR_INIT_SUCCESS",
            "message": "CustomSource preprocessor initialized successfully"
        })
        
    except Exception as e:
        self.logger.error({
            "action": "PREPROCESSOR_INIT_ERROR",
            "message": f"Failed to initialize preprocessor: {str(e)}",
            "data": {"error": str(e), "error_type": type(e).__name__}
        })
        raise PreprocessorError(f"Preprocessor initialization failed: {str(e)}") from e
```

### 3. Implement the preprocess method

Implement the main preprocessing logic:

```python
async def preprocess(self, raw_data: Any) -> List[Dict[str, Any]]:
    """
    Transform raw data into standardized documents.
    
    Args:
        raw_data: Raw data from an ingestor, expected to be a dict with 'messages' and 'conversations'
        
    Returns:
        List[Dict[str, Any]]: List of standardized documents
        
    Raises:
        PreprocessorError: If preprocessing fails
    """
    if not self._is_initialized:
        raise PreprocessorError("Preprocessor not initialized. Call initialize() first.")
    
    try:
        # Validate input format
        if not isinstance(raw_data, dict):
            raise PreprocessorError(f"Expected dict, got {type(raw_data).__name__}")
        
        messages = raw_data.get("messages", [])
        conversations = raw_data.get("conversations", [])
        
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
        
        # Create a lookup for conversation metadata
        conversation_lookup = {conv["id"]: conv for conv in conversations}
        
        # Group messages by time windows and conversation
        message_groups = self._group_messages_by_time(messages)
        
        self.logger.info({
            "action": "PREPROCESSOR_GROUPED",
            "message": f"Grouped messages into {len(message_groups)} time windows",
            "data": {"group_count": len(message_groups)}
        })
        
        # Process each group into standardized documents
        documents = []
        for group in message_groups:
            # Split large groups into smaller chunks
            chunks = self._create_chunks(group)
            
            # Process each chunk into a document
            for chunk in chunks:
                # Format conversation text
                document_text = self._format_conversation(chunk)
                
                # Extract metadata
                metadata = self._create_metadata(chunk, conversation_lookup)
                
                # Create standardized document with UUID
                document = {
                    "id": str(uuid.uuid4()),
                    "text": document_text,
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
            "action": "PREPROCESSOR_ERROR",
            "message": f"Failed to preprocess data: {str(e)}",
            "data": {"error": str(e), "error_type": type(e).__name__}
        })
        raise PreprocessorError(f"Preprocessing failed: {str(e)}") from e
```

### 4. Implement helper methods

Implement helper methods for the preprocessing logic:

```python
def _group_messages_by_time(self, messages: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Group messages into time-based windows by conversation.
    
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
        key=lambda m: m.get("timestamp", 0)
    )
    
    # Group by conversation and time windows
    conversation_groups = {}
    
    for message in sorted_messages:
        # Extract message data
        conversation_id = message.get("conversation_id")
        message_timestamp = message.get("timestamp", 0)
        
        # Convert to datetime if needed
        if isinstance(message_timestamp, (int, float)):
            message_date = datetime.fromtimestamp(message_timestamp)
        else:
            # Skip messages without valid timestamps
            continue
        
        # Initialize conversation entry if needed
        if conversation_id not in conversation_groups:
            conversation_groups[conversation_id] = []
        
        # Check if message fits in current window or needs a new one
        current_groups = conversation_groups[conversation_id]
        
        if not current_groups:
            # First message for this conversation
            current_groups.append([message])
        else:
            # Get the last group and its end time
            last_group = current_groups[-1]
            last_message = last_group[-1]
            last_timestamp = last_message.get("timestamp", 0)
            
            if isinstance(last_timestamp, (int, float)):
                last_date = datetime.fromtimestamp(last_timestamp)
            else:
                # Use current message date if last message has invalid timestamp
                last_date = message_date
            
            # Check if within time window
            if (message_date - last_date) <= timedelta(minutes=self._time_window_minutes):
                # Add to current group
                last_group.append(message)
            else:
                # Start a new group
                current_groups.append([message])
    
    # Flatten the groups from all conversations
    all_groups = []
    for groups in conversation_groups.values():
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
        # Get sender name (prefer username, fall back to sender_name)
        sender = message.get("sender_name", "Unknown")
        message_text = message.get("text", "")
        
        if not message_text:
            continue
        
        # Only add sender name when it changes
        if sender != current_sender:
            formatted_lines.append(f"{sender}: {message_text}")
            current_sender = sender
        else:
            # Continue same speaker's message
            formatted_lines.append(f"  {message_text}")
    
    # Join lines with newlines
    return "\n".join(formatted_lines)

def _create_metadata(self, messages: List[Dict[str, Any]], conversation_lookup: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract metadata from a group of messages.
    
    Args:
        messages: List of messages in a chunk
        conversation_lookup: Dictionary mapping conversation IDs to conversation data
        
    Returns:
        Dictionary of metadata
    """
    if not messages:
        return {}
    
    # Get conversation ID from first message
    conversation_id = messages[0].get("conversation_id")
    
    # Get conversation data
    conversation = conversation_lookup.get(conversation_id, {})
    conversation_name = conversation.get("name") or messages[0].get("conversation_name", "Unknown Chat")
    
    # Get timestamps
    timestamps = [msg.get("timestamp", 0) for msg in messages if msg.get("timestamp")]
    start_timestamp = min(timestamps) if timestamps else 0
    end_timestamp = max(timestamps) if timestamps else 0
    
    # Extract participant names
    participants = set()
    for message in messages:
        sender = message.get("sender_name")
        if sender:
            participants.add(sender)
    
    return {
        "source": "custom_source",  # Replace with your actual source name
        "conversation_id": conversation_id,
        "conversation_name": conversation_name,
        "conversation_type": conversation.get("type", "unknown"),
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "message_count": len(messages),
        "participants": list(participants)
    }
```

## Configuration Setup

In your `config.yaml` file, add a section for your preprocessor:

```yaml
preprocessors:
  custom_source:
    time_window_minutes: 15
    chunk_size: 512
    max_messages_per_chunk: 10
    include_overlap: true
    # Other configuration options specific to your preprocessor
```

## Preprocessor Pipeline Integration

Your preprocessor will be used by the ingestion pipeline:

```python
# In DefaultIngestionPipeline._initialize_components:
custom_preprocessor = CustomSourcePreprocessor()
await custom_preprocessor.initialize()

# Register with an ingestor
self.register_ingestor(
    ingestor_id="@user/custom_ingestor",
    ingestor=custom_ingestor,
    preprocessor=custom_preprocessor
)
```

## Best Practices

1. **Handle Different Formats**: Be flexible in handling different input formats from various ingestors.

2. **Meaningful Grouping**: Group messages in ways that preserve conversation context and flow.

3. **Document Size**: Balance document size for optimal embedding - too short lacks context, too long dilutes relevance.

4. **Rich Metadata**: Include comprehensive metadata to enable effective filtering and retrieval.

5. **Text Normalization**: Clean and normalize text for better embedding quality.

6. **Error Handling**: Gracefully handle malformed or incomplete data.

7. **Time-based Processing**: Use timestamps consistently for grouping messages.

8. **Performance Optimization**: Process data efficiently, especially for large datasets.

9. **Overlapping Documents**: Consider including overlap between documents to maintain context.

10. **Configurable Parameters**: Make chunking and grouping parameters configurable.

## Example Preprocessors

Explore existing preprocessors for reference:
- `ici/adapters/preprocessors/telegram.py` - For Telegram data
- `ici/adapters/preprocessors/whatsapp.py` - For WhatsApp data
