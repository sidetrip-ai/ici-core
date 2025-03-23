# Examples

This directory contains example scripts demonstrating the usage of the ICI framework components.

## Vector Store Query Tools

This directory contains example scripts for querying the ChromaDB vector store where Telegram messages are stored.

### Basic Query Script

The `query_vectorstore_example.py` script provides a simple interface for querying the vector store:

```bash
# Basic query
python query_vectorstore_example.py "your search query"

# Specify number of results
python query_vectorstore_example.py "your search query" --top_k 10

# Filter by conversation
python query_vectorstore_example.py "your search query" --conversation_id "123456789"
```

### Advanced Query Tool

The `advanced_vector_query.py` script offers more advanced features:

```bash
# Basic search
python advanced_vector_query.py "your search query"

# List all documents
python advanced_vector_query.py --list_all --top_k 20

# Filter by conversation and date range
python advanced_vector_query.py "your search query" --conversation_id "123456789" --date_from "2025-01-01" --date_to "2025-03-20"

# Get conversation context around a specific message
python advanced_vector_query.py --message_id "message_uuid" --context_window 5

# Export results to JSON
python advanced_vector_query.py "your search query" --format json --export results.json

# Export results to CSV
python advanced_vector_query.py "your search query" --export results.csv

# Show full text in results
python advanced_vector_query.py "your search query" --full_text
```

## Telegram Ingestion Pipeline

The examples also include scripts for running the Telegram ingestion pipeline:

### Single Run Pipeline

The `async_telegram_pipeline_example.py` script demonstrates a single run of the Telegram ingestion pipeline:

```bash
# Run the pipeline once
python async_telegram_pipeline_example.py
```

### Scheduled Pipeline

The `scheduled_telegram_pipeline_example.py` script demonstrates scheduled ingestion with the Telegram pipeline:

```bash
# Register the ingestor (first-time use) and start scheduled ingestion
python scheduled_telegram_pipeline_example.py --register

# Start scheduled ingestion (if already registered)
python scheduled_telegram_pipeline_example.py

# Just run once (don't schedule)
python scheduled_telegram_pipeline_example.py --run-once
```

The scheduled pipeline will run at the interval specified in `config.yaml` (under `pipelines.telegram.schedule.interval_minutes`).

## Usage Notes

- These scripts use the configuration from `config.yaml` in the project root.
- Vector store queries require that data has been ingested using one of the pipeline examples.
- For date filtering, use ISO format dates (YYYY-MM-DD).
- The scheduled pipeline can be stopped with Ctrl+C, which will gracefully shut down the scheduler.

## Examples

**Search for messages about a specific topic:**
```bash
python advanced_vector_query.py "cryptocurrency market updates"
```

**Find all messages from a specific conversation mentioning a topic:**
```bash
python advanced_vector_query.py "login code" --conversation_id "777000"
```

**Export all messages from the last month:**
```bash
python advanced_vector_query.py --list_all --date_from "2025-02-20" --export recent_messages.csv
```

**Get the conversation context around a specific message:**
```bash
python advanced_vector_query.py --message_id "d290f1ee-6c54-4b01-90e6-d701748f0851" --context_window 3
``` 