# Intelligent Consciousness Interface (ICI) Core

A modular framework for creating a personal AI assistant that is context-aware, style-aware, personality-aware, and security-aware. The system processes data through an Ingestion Pipeline and responds to queries via a Query Pipeline, leveraging vector databases for efficient retrieval.

## Features

- Modular architecture with well-defined interfaces
- Separation of concerns between ingestion and query pipelines
- Extensible design supporting multiple data sources and AI models
- Structured logging for better debugging and monitoring
- Security-first approach with input validation

## Quick Start

### Installation

The simplest way to install ICI Core is using pip:

```bash
# Create a virtual environment (recommended)
python -m venv ici-env
source ici-env/bin/activate  # Linux/macOS
# OR
ici-env\Scripts\activate     # Windows

# Install from the repository
pip install -e .
```

For development:

```bash
# Install development dependencies
pip install -e ".[dev]"
```

For specific components:

```bash
# For embeddings support
pip install -e ".[embeddings]"

# For vector store support
pip install -e ".[vector-stores]"

# For all components
pip install -e ".[dev,embeddings,vector-stores]"
```

### Basic Usage

Here's how to use the structured logger:

```python
from ici.adapters.loggers import StructuredLogger

# Initialize logger
logger = StructuredLogger(
    name="my_component", 
    level="INFO",
    log_file="logs/app.log"
)

# Log events with structured data
logger.info({
    "action": "APP_START",
    "message": "Application started successfully",
    "data": {
        "version": "0.1.0",
        "environment": "development"
    }
})
```

## Project Structure

```
ici-core/
├── ici/                      # Main package
│   ├── core/                 # Core domain logic
│   │   ├── interfaces/       # Interfaces defining the architecture
│   │   └── exceptions/       # Exception definitions
│   └── adapters/             # Implementations of interfaces
│       └── loggers/          # Logger implementations
├── examples/                 # Example scripts
├── tests/                    # Tests
├── requirements.txt          # Project dependencies
├── setup.py                  # Package installation script
└── README.md                 # Project documentation
```

## Development

To contribute to this project:

1. Clone the repository
2. Install development dependencies: `pip install -e ".[dev]"`
3. Run the tests: `pytest`
4. Format code: `black ici tests examples`

## License

[MIT License](LICENSE)

## Telegram Ingestor

The ICI framework includes a Telegram ingestor that can extract direct messages from your Telegram account using the MTProto API. This allows you to analyze your personal message history.

### Setup

To use the Telegram ingestor, you need to:

1. **Create a Telegram API application**:
   - Go to https://my.telegram.org/apps
   - Log in with your phone number
   - Create a new application to get your API ID and API hash

2. **Install the required dependencies**:
   ```bash
   pip install -e ".[telegram]"
   ```

3. **Configure the ingestor**:

   Create a `config.yaml` file with your Telegram credentials:
   ```yaml
   telegram:
     api_id: "YOUR_API_ID"
     api_hash: "YOUR_API_HASH"
     phone_number: "+12345678901"  # Include country code
     # Use either session_file or session_string
     session_file: "telegram_session"  # Option 1: Path to session file
     # session_string: "1BQANOTEuMTA4LjU..."  # Option 2: Session string 
     request_delay: 0.5  # Delay between requests to avoid rate limiting
   ```

4. **Authentication Options**:
   - **Session File**: Traditional method that stores session data in a local file
   - **Session String**: Portable string-based authentication that can be securely stored and transferred between environments without file access

5. **Usage example**:
   ```python
   import asyncio
   from ici.adapters.ingestors.telegram import TelegramIngestor
   from datetime import datetime, timedelta
   
   async def main():
       # Initialize using config.yaml
       ingestor = TelegramIngestor()
       await ingestor.initialize()  # Loads config from config.yaml
       
       # Check if connected successfully
       health = ingestor.healthcheck()
       if health["healthy"]:
           # Fetch all direct message conversations
           data = ingestor.fetch_full_data()
           
           # Or fetch messages from the last 7 days
           since_date = datetime.now() - timedelta(days=7)
           recent_data = ingestor.fetch_new_data(since=since_date)
           
           # Or fetch messages within a date range
           start_date = datetime.now() - timedelta(days=30)
           end_date = datetime.now() - timedelta(days=15)
           range_data = ingestor.fetch_data_in_range(start=start_date, end=end_date)
           
           print(f"Retrieved {len(recent_data['messages'])} messages from {len(recent_data['conversations'])} conversations")
   
   # Run the async function
   asyncio.run(main())
   ```

### Generating a Session String

You can generate a session string from an existing session file:

```python
from telethon.sessions import StringSession
from telethon.sync import TelegramClient

with TelegramClient("your_session_file", api_id, api_hash) as client:
    print(StringSession.save(client.session))
```

### Security Notes

- The API credentials give access to your Telegram account, so keep them secure
- Both session files and session strings store your authentication token - protect them like passwords
- Session strings are useful for containerized environments where persistent file storage may not be available
- All data is processed locally on your machine; no data is sent to any third-party servers

### Structure of Retrieved Data

The ingestor returns data in the following format:

```json
{
  "conversations": [
    {
      "id": "123456789",
      "name": "John Doe",
      "username": "johndoe",
      "type": "direct",
      "unread_count": 0,
      "last_message_date": "2023-03-18T12:00:00"
    }
  ],
  "messages": [
    {
      "id": "1001",
      "conversation_id": "123456789",
      "conversation_name": "John Doe",
      "conversation_username": "johndoe",
      "date": "2023-03-18T11:30:00",
      "text": "Hello, this is a message",
      "outgoing": false,
      "media_type": null,
      "reply_to_msg_id": null,
      "source": "telegram"
    }
  ]
}
```

For a complete example, see `examples/telegram_ingestor_example.py`.

## ICI Core

Intelligent Collective Intelligence (ICI) Core library provides the foundation for ICI data ingestion and processing pipelines.

## Overview

ICI Core provides:

- Base interfaces for data ingestion pipelines
- Storage adapters for saving processed data
- Utilities for consistent logging, error handling, and configuration

## Configuration

ICI Core uses a configuration file to set up services, storage, and pipeline parameters. By default, it looks for a file specified by the `ICI_CONFIG_PATH` environment variable.

Example `config.yaml`:

```yaml
storage:
  type: local
  path: ./data

telegram:
  api_id: YOUR_API_ID
  api_hash: YOUR_API_HASH
  phone: YOUR_PHONE_NUMBER
  session_file: ./telegram_session.session
  group_usernames:
    - some_group_name
    - another_group
```

## Basic Usage

### Creating an Ingestion Pipeline

```python
from ici.adapters.pipelines.telegram import TelegramIngestionPipeline
from ici.adapters.loggers import StructuredLogger

# Create a logger
logger = StructuredLogger(name="telegram_pipeline")

# Initialize the pipeline
pipeline = TelegramIngestionPipeline(logger_name="telegram_pipeline")
await pipeline.initialize()

# Register an ingestor
pipeline.register_ingestor(
    ingestor_id="telegram_ingestor", 
    ingestor_config={}
)

# Run the pipeline once
pipeline.start()
```

## Examples

See the `examples` directory for complete working examples:

- `examples/scheduled_telegram_pipeline_example.py` - Example of a Telegram ingestion pipeline that can be run once or scheduled

## Development

### Setup

1. Clone the repository
```bash
git clone https://github.com/yourusername/ici-core.git
cd ici-core
```

2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install development dependencies
```bash
pip install -e ".[dev]"
```

### Testing

Run tests with pytest:
```bash
pytest tests/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
