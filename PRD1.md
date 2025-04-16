# Product Requirements Document: Enhanced Telegram Ingestor

## Executive Summary
This document outlines the requirements for enhancing the Telegram Ingestor component of the ICI Core system. The enhancements include implementing a dual-storage mechanism (SQL database and JSON cache), selective conversation filtering, and a decoupled processing pipeline architecture.

## Background
The current Telegram Ingestor fetches conversation data directly into memory and returns it as dictionaries without persistent storage or processing status tracking. This approach has several limitations:
- No persistence between runs
- Repeated fetching of the same data
- No way to track processed vs. unprocessed messages
- Tight coupling between data fetching and processing

## Objectives
1. Implement a persistent storage system for Telegram conversation data
2. Create a mechanism to track processing status of messages
3. Implement selective conversation filtering for initial fetches
4. Decouple the ingestor from the processing pipeline
5. Ensure efficient incremental data fetching

## User Stories
- As a system operator, I want the Telegram Ingestor to only fetch personal chats, bot chats, and private groups on initial fetch so that the system processes the most relevant data first.
- As a system operator, I want the ingestor to store raw Telegram data in a JSON cache so that I can recover the original data if needed.
- As a system operator, I want all Telegram data stored in an SQL database so that it can be efficiently queried by the preprocessor.
- As a system operator, I want the ingestor to fetch only new messages on subsequent runs so that it minimizes API usage and improves performance.
- As a preprocessor, I want to query only unprocessed messages so that I don't reprocess the same data multiple times.

## Functional Requirements

### 1. Storage System
1.1. Implement SQL database storage for Telegram conversations and messages
1.2. Implement JSON cache storage for raw Telegram message data
1.3. Store processing status flags in the database
1.4. Enable recovery from JSON cache if database is missing or corrupted

### 2. Conversation Filtering
2.1. Initial fetch mode: Only fetch personal chats, bot chats, and private groups
2.2. Secondary fetch mode: Fetch all available conversations
2.3. Make fetch mode configurable in `config.yaml`

### 3. Incremental Fetching
3.1. Track the latest message timestamp per conversation
3.2. Only fetch messages newer than the latest stored message
3.3. Provide mechanism to force a full refresh if needed

### 4. Processing Pipeline
4.1. Store processing status for each message
4.2. Provide method to query unprocessed messages
4.3. Provide method to mark messages as processed
4.4. Enable preprocessing and processing stages to operate independently

## Technical Specifications

### Database Schema
```sql
CREATE TABLE IF NOT EXISTS telegram_conversations (
    id TEXT PRIMARY KEY,
    name TEXT,
    username TEXT,
    is_group BOOLEAN,
    chat_type TEXT,
    last_message_date TIMESTAMP,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS telegram_messages (
    id TEXT,
    conversation_id TEXT,
    sender_id TEXT,
    text TEXT,
    date TIMESTAMP,
    is_outgoing BOOLEAN,
    reply_to_id TEXT,
    processed BOOLEAN DEFAULT FALSE,
    raw_data_key TEXT,  -- Reference to the JSON cache
    metadata TEXT,
    PRIMARY KEY (id, conversation_id),
    FOREIGN KEY (conversation_id) REFERENCES telegram_conversations(id)
);

CREATE TABLE IF NOT EXISTS telegram_sync_status (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_sync TIMESTAMP,
    json_last_updated TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_processed ON telegram_messages(processed);
CREATE INDEX IF NOT EXISTS idx_messages_date ON telegram_messages(date);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON telegram_messages(conversation_id);
```

### JSON Cache Format
```json
{
  "last_update": "ISO-timestamp",
  "conversations": {
    "chat_id_1": {
      "metadata": {...},
      "raw_messages": {
        "message_id_1": {...},
        "message_id_2": {...}
      }
    },
    "chat_id_2": {...}
  }
}
```

### Configuration Updates
```yaml
ingestors:
  telegram:
    # Existing config...
    db_path: "db/telegram/telegram.db"
    json_cache_path: "db/telegram/telegram_cache.json"
    fetch_mode: "initial"  # "initial" or "all"
    sqlite:
      enable: true
      connection_timeout: 30
    backup_frequency: 24  # hours between full JSON backups
```

### Conversation Type Detection
- Personal chats: `not is_group and chat_type == "private"`
- Bot chats: `username.endswith("bot")`
- Private groups: `is_group and not is_channel and chat_type != "channel"`

## Implementation Plan

### Phase 1: Storage Infrastructure
1. Implement SQL database schema and connection methods
2. Implement JSON cache serialization and deserialization
3. Implement database utility methods (init, connect, query)

### Phase 2: Data Fetching Enhancements
1. Implement conversation filtering based on fetch mode
2. Implement incremental message fetching
3. Implement raw message serialization

### Phase 3: Storage Operations
1. Implement methods to store conversations and messages
2. Implement methods to update processing status
3. Implement database-to-JSON sync methods
4. Implement JSON-to-database recovery methods

### Phase 4: Interface Integration
1. Update existing interface methods to use new storage system
2. Implement new methods for preprocessor integration
3. Add configuration validation and error handling

## Testing Strategy

### Unit Tests
1. Test database schema creation and connection
2. Test JSON serialization and deserialization
3. Test conversation filtering logic
4. Test incremental fetching logic

### Integration Tests
1. Test full data fetch and storage workflow
2. Test recovery from JSON cache
3. Test preprocessor integration
4. Test performance with large datasets

### System Tests
1. Test end-to-end flow with real Telegram API
2. Test error handling and recovery
3. Test with various configuration settings

## Acceptance Criteria
1. The ingestor successfully stores all Telegram data in both SQL and JSON formats
2. Initial fetch mode correctly filters for personal chats, bot chats, and private groups
3. Subsequent fetches only retrieve new messages
4. The system can recover from database deletion using the JSON cache
5. The preprocessor can query unprocessed messages and mark them as processed
6. Performance metrics meet expectations for large datasets

## Timelines and Dependencies

### Dependencies
1. Telethon library for Telegram API access
2. SQLite for database storage
3. Existing ICI Core interfaces and configurations

### Timeline
1. Phase 1 (Storage Infrastructure): 1 week
2. Phase 2 (Data Fetching Enhancements): 1 week
3. Phase 3 (Storage Operations): 1 week
4. Phase 4 (Interface Integration): 1 week
5. Testing and Bug Fixes: 1 week

Total estimated timeline: 5 weeks 