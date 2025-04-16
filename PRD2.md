# Product Requirements Document: Enhanced Telegram Ingestor

## Overview
The Enhanced Telegram Ingestor is a critical component of the ICI Core system responsible for retrieving message data from Telegram. This enhancement addresses critical limitations in the current implementation by decoupling the data ingestion from preprocessing and implementing a persistent JSON-based storage system with processing status tracking.

The current Telegram Ingestor fetches conversation data directly into memory and returns it as dictionaries without persistent storage or processing status tracking, resulting in:
- No persistence between runs
- Repeated fetching of the same data
- No way to track processed vs. unprocessed messages
- Tight coupling between data fetching and processing

This enhancement will significantly improve system efficiency, enable parallel processing, and provide better data management for Telegram conversations.

## Core Features

### 1. JSON-based Storage System
**What**: A file-based storage system that persists Telegram conversation data as JSON files, one per conversation.

**Why**: Provides persistence between runs, enables recovery of original data, and decouples the ingestor from preprocessing.

**How**: 
- Each conversation gets its own JSON file with comprehensive metadata and full message content
- Files are organized using a simple naming convention that indicates processing status
- JSON format includes all necessary fields for both the ingestor and preprocessor

### 2. Processing Status Tracking
**What**: A mechanism to track which conversations have been processed using a filename-based convention.

**Why**: Prevents reprocessing of the same data, allows parallel operation of ingestor and preprocessor, and provides visibility into processing status.

**How**:
- Files use a naming convention: `conversation_id_unprocessed.json` or `conversation_id_processed.json`
- Preprocessor only processes files with `_unprocessed` in the filename
- After processing, preprocessor renames the file to use the `_processed` suffix
- This approach eliminates the need to parse file contents to determine processing status

### 3. Selective Conversation Filtering
**What**: Capability to selectively fetch conversations based on type (personal chats, bot chats, private groups).

**Why**: Allows processing of the most relevant data first, optimizes initial setup time, and provides control over which data is ingested.

**How**:
- Initial fetch mode only retrieves personal chats, bot chats, and private groups
- Secondary fetch mode retrieves all available conversations
- Mode is configurable in the system configuration

### 4. Incremental Data Fetching
**What**: Ability to fetch only new messages for conversations that have already been downloaded.

**Why**: Minimizes API usage, improves performance, and reduces redundant data processing.

**How**:
- Track the timestamp of the latest message in each conversation
- Only fetch messages newer than the latest stored message
- Provide a mechanism to force a full refresh if needed

## User Experience

### User Personas
1. **System Operator**: Technical user who configures and maintains the ICI Core system
2. **Preprocessor Component**: Downstream system component that processes ingested Telegram data

### Key User Flows

#### System Operator Flow
1. Configure the Enhanced Telegram Ingestor in config.yaml
2. Run the ingestor orchestrator to fetch initial conversation data
3. Run the preprocessor orchestrator in parallel to process the fetched data
4. Monitor processing status and system performance
5. Configure additional fetch parameters as needed for ongoing operation

#### Preprocessor Component Flow
1. Identify unprocessed conversation files (with `_unprocessed` suffix)
2. Read and process the conversation data
3. Rename the file to use the `_processed` suffix
4. Store processed data in the vector database

### UI/UX Considerations
- Command-line interface for orchestrator management
- Clear logging of ingestor and preprocessor operations
- Simple configuration interface in YAML format
- File-based architecture for easy debugging and manual intervention if needed

## Technical Architecture

### System Components

#### 1. Ingestor Orchestrator
- Manages the process of fetching and storing Telegram data
- Runs independently of the preprocessing pipeline
- Configurable for different fetch modes and schedules

#### 2. Preprocessor Orchestrator
- Monitors the JSON storage directory for unprocessed files
- Processes conversation data and updates processing status
- Runs independently of the ingestor orchestrator

#### 3. JSON Storage Layer
- File-based storage for Telegram conversation data
- Implements read/write operations for conversation files
- Handles file organization and management

### Data Models

#### JSON File Format
```json
{
  "metadata": {
    "conversation_id": "chat_id_1",
    "name": "Chat Name",
    "username": "username",
    "is_group": false,
    "chat_type": "private",
    "last_message_date": "ISO-timestamp",
    "last_update": "ISO-timestamp",
    "participants": [
      {
        "id": "user123",
        "username": "username1",
        "first_name": "First",
        "last_name": "Last"
      }
    ]
  },
  "messages": {
    "message_id_1": {
      "sender_id": "user123",
      "sender_name": "First Last",
      "text": "Message content",
      "date": "ISO-timestamp",
      "is_outgoing": false,
      "reply_to_id": null,
      "media_type": null,
      "media_path": null,
      "entities": [],
      "reactions": [],
      "forwarded_from": null,
      "raw_data": {...}
    },
    "message_id_2": {...}
  }
}
```

#### Configuration Model
```yaml
ingestors:
  telegram:
    # Existing config...
    json_storage_path: "db/telegram/chats/"
    fetch_mode: "initial"  # "initial" or "all"
    backup_frequency: 24  # hours between backups
    max_history_limit: 5000  # maximum messages per conversation
```

### Conversation Type Detection
- Personal chats: `not is_group and chat_type == "private"`
- Bot chats: `username.endswith("bot")`
- Private groups: `is_group and not is_channel and chat_type != "channel"`

## Development Roadmap

### Phase 1: Storage Infrastructure
1. Create JSON file format definition
2. Implement JSON serialization and deserialization
3. Implement file system operations (save, load, list)
4. Implement filename-based status tracking
5. Implement backup mechanism for JSON files

### Phase 2: Ingestor Enhancements
1. Implement conversation filtering based on fetch mode
   - Personal chat detection
   - Bot chat detection
   - Private group detection
2. Implement incremental message fetching
   - Track latest message timestamp per conversation
   - Fetch only newer messages for existing conversations
   - Handle message edits and deletions
3. Implement raw message serialization
   - Capture all relevant Telegram message fields
   - Handle media attachments
   - Support message entities (formatting, links, etc.)

### Phase 3: Processing Status Management
1. Implement filename-based status tracking (`_unprocessed` and `_processed` suffixes)
2. Develop utility functions to identify unprocessed files
3. Create methods to update processing status (file renaming)
4. Add recovery mechanisms for interrupted processing

### Phase 4: Orchestrator Implementation
1. Create separate Ingestor Orchestrator
   - Schedule-based operation
   - Configurable fetch modes
   - Robust error handling
2. Create separate Preprocessor Orchestrator
   - File system monitoring for unprocessed files
   - Processing status updates
   - Integration with existing preprocessor components

### Phase 5: Interface and Testing
1. Update existing interfaces for new storage system
2. Implement comprehensive unit tests
   - JSON serialization/deserialization tests
   - Conversation filtering tests
   - Incremental fetching tests
3. Develop integration tests
   - End-to-end data flow tests
   - Performance testing with large datasets
   - Error recovery testing

## Logical Dependency Chain

### Foundation Components (Build First)
1. JSON data model and serialization utilities
   - Define comprehensive JSON schema
   - Implement serialization/deserialization
   - Create file system operations
   
2. Conversation type detection
   - Implement logic for identifying chat types
   - Create utility methods for filtering conversations

### Core Functionality (Build Second)
1. Ingestor with JSON storage
   - Fetch conversations from Telegram
   - Store as JSON files with `_unprocessed` suffix
   - Implement incremental fetching for existing files

2. Processing status management
   - Add methods to find unprocessed files
   - Create utilities to update processing status (rename files)

### Orchestration Layer (Build Third)
1. Ingestor Orchestrator
   - Schedule-based operation
   - Configuration-driven behavior
   
2. Preprocessor Orchestrator
   - File monitoring
   - Processing workflow

### Advanced Features (Build Last)
1. Recovery mechanisms
   - Handling interrupted processing
   - Managing corrupted files
   
2. Performance optimizations
   - Parallel processing capabilities
   - Efficient file handling for large datasets

## Risks and Mitigations

### Technical Challenges
1. **Risk**: Telegram API rate limits could slow down data fetching
   **Mitigation**: Implement intelligent rate limiting and backoff strategies

2. **Risk**: Large conversations could cause performance issues
   **Mitigation**: Implement chunking for large conversations and optimize file operations

3. **Risk**: Parallel processing could lead to race conditions
   **Mitigation**: Implement proper file locking and transaction-based updates

### Implementation Risks
1. **Risk**: JSON format might not capture all necessary preprocessor data
   **Mitigation**: Work closely with preprocessor team to verify data requirements and enhance the format as needed

2. **Risk**: File-based approach might have scalability limitations
   **Mitigation**: Design for eventual migration to a more scalable storage solution if needed

### Resource Constraints
1. **Risk**: Development timeline may be tight for all features
   **Mitigation**: Implement core features first and follow with enhancements; define clear MVP

## Appendix

### Telethon API Considerations
- Message history limit is 100 messages per request
- Media downloads require separate API calls
- Rate limiting allows approximately 30 requests per second

### Testing Requirements
- Test with varied conversation types and sizes
- Verify correct handling of edited and deleted messages
- Ensure proper handling of media attachments
- Validate incremental fetching with timestamp-based filtering 