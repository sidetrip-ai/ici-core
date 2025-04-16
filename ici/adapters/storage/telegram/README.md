# Telegram Storage Module

This module implements the file-based storage system for Telegram conversations as described in the Enhanced Telegram Ingestor PRD.

## Features

- **JSON Schema Definition**: Comprehensive schema for Telegram conversations
- **Serialization/Deserialization**: Utilities to convert between objects and JSON
- **Filename-based Status Tracking**: Uses `_unprocessed.json` and `_processed.json` suffixes
- **File Management**: Atomic operations for file saving and status updates
- **Automated Backups**: Configurable backup creation and management
- **File Locking**: Prevents concurrent access issues with multiple processes
- **Parallel Processing**: Utilities for batch operations on conversation files
- **Import/Export**: Functionality for data migration and archiving

## Components

### Schema Definition (`schema.py`)

Defines the structure of Telegram conversation JSON files, including:

- Metadata section with conversation details
- Messages storage with comprehensive message properties
- Sample conversation structure for testing

### Serializer (`serializer.py`)

The `ConversationSerializer` class handles:

- Converting between Python objects and JSON strings
- Validating conversations against the schema
- Extracting metadata and messages from conversations
- Retrieving message dates for incremental fetching

### File Manager (`file_manager.py`)

The `FileManager` class provides:

- Filename-based status tracking with `_unprocessed` and `_processed` suffixes
- Atomic file operations to ensure data integrity
- Methods to save, load, and list conversations
- Functionality to mark conversations as processed

### Enhanced File Manager (`enhanced_file_manager.py`)

The `EnhancedFileManager` class extends the basic FileManager with:

- Automated backup creation based on configurable frequency
- File locking for concurrent access protection
- Parallel processing of multiple conversations
- Import/export functionality for data migration
- Recovery and maintenance operations

### Utilities (`utils.py`)

Provides additional functionality including:

- `FileSystemLock`: Thread-safe file locking mechanism
- `BackupManager`: Handles backup creation, listing, and restoration
- `atomic_write()`: Ensures data integrity during file operations
- `batch_process_files()`: Facilitates parallel file processing

## Usage Examples

### Basic File Management

```python
from ici.adapters.ingestors.telegram.storage import FileManager

file_manager = FileManager()
conversation = {
    "metadata": {
        "conversation_id": "12345",
        "name": "Example Chat",
        "chat_type": "private",
        "last_message_date": "2023-11-15T12:30:45Z",
        "last_update": "2023-11-15T12:30:45Z",
        # other metadata fields...
    },
    "messages": {
        # message objects...
    }
}

# Saves as 12345_unprocessed.json
file_path = file_manager.save_conversation(conversation)
```

### Enhanced Features with Locking and Backups

```python
from ici.adapters.ingestors.telegram.storage import EnhancedFileManager

# Creates a file manager with automated backups
enhanced_manager = EnhancedFileManager(
    backup_enabled=True,
    max_backups=5
)

# Save a conversation (creates backup if needed)
enhanced_manager.save_conversation(conversation)

# Process all unprocessed conversations
def process_function(conversation):
    # Do something with the conversation
    return "Processed"

results = enhanced_manager.process_all_unprocessed(process_function)

# Create a manual backup
backup_path = enhanced_manager.create_manual_backup(tag="pre-update")

# Export conversations to a single file
enhanced_manager.export_conversations_to_json("export.json")
```

### Safe Concurrent Access

```python
from ici.adapters.ingestors.telegram.storage.utils import FileSystemLock

# Acquire a lock on a file
with FileSystemLock.acquire("path/to/file.json", shared=False):
    # Write to the file
    # Other processes will wait until this completes
```

## Configuration

The storage directory is determined in the following order:

1. Explicit path provided to the constructor
2. `chat_history_dir` from preprocessor configuration
3. `json_storage_path` from ingestor configuration
4. Default: `db/telegram/chats/`

Additional configuration options:

- `backup_frequency`: Hours between automatic backups (from config or default: 24)
- `max_backups`: Maximum number of backup sets to keep (default: 5)
- `lock_timeout`: Maximum seconds to wait for file locks (default: 10) 