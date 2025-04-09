# Default Ingestion Pipeline

The Default Ingestion Pipeline is a unified solution for ingesting data from multiple sources into the ICI system. It provides a simplified way to manage both WhatsApp and Telegram data sources using a single pipeline.

## Overview

This pipeline combines the functionality of both WhatsApp and Telegram ingestors, providing:

- A unified interface for multiple data sources
- Consistent state tracking for each ingestor
- Shared embedder and vector store for all data
- Efficient resource management
- Centralized error handling and logging

## Architecture

The DefaultIngestionPipeline implements the `IngestionPipeline` interface and uses a component registry system to manage multiple ingestors and preprocessors:

```
┌───────────────────────────────────────────────────────┐
│               DefaultIngestionPipeline                │
├───────────────────────────────────────────────────────┤
│                                                       │
│  ┌───────────────┐        ┌────────────────┐          │
│  │ WhatsApp      │        │ Telegram       │          │
│  │ Ingestor      │        │ Ingestor       │          │
│  └───────┬───────┘        └────────┬───────┘          │
│          │                         │                  │
│  ┌───────┴───────┐        ┌───────┴───────┐           │
│  │ WhatsApp      │        │ Telegram      │           │
│  │ Preprocessor  │        │ Preprocessor  │           │
│  └───────┬───────┘        └───────┬───────┘           │
│          │                         │                  │
│          └─────────────┬───────────┘                  │
│                        │                              │
│              ┌─────────┴──────┐                       │
│              │    Embedder    │                       │
│              └─────────┬──────┘                       │
│                        │                              │
│              ┌─────────┴──────┐                       │
│              │  Vector Store  │                       │
│              └────────────────┘                       │
│                                                       │
└───────────────────────────────────────────────────────┘
```

## Key Components

1. **Ingestor Registry**: Stores and manages instances of different ingestors with their corresponding preprocessors. Each ingestor has a unique ID for state tracking.

2. **Shared Components**:
   - **Embedder**: A single embedder instance (SentenceTransformerEmbedder) for all documents
   - **Vector Store**: A single vector database (ChromaDB) for storing all processed documents
   - **State Manager**: Tracks the processing state for each ingestor separately

3. **Configuration**:
   - Loaded from the standard `config.yaml` file
   - Supports configuration for all components (ingestors, preprocessors, embedder, vector store)
   - Pipeline-specific settings like batch size and scheduling

## Usage

### Configuration

Add the following to your `config.yaml` file:

```yaml
pipelines:
  default:
    batch_size: 100
    schedule:
      interval_minutes: 15
    vector_store:
      collection_name: default_messages
```

### Code Example

```python
from ici.adapters.pipelines import DefaultIngestionPipeline

async def process_messages():
    # Create and initialize the pipeline
    pipeline = DefaultIngestionPipeline()
    await pipeline.initialize()
    
    # Run for a specific ingestor
    telegram_result = await pipeline.run_ingestion("@user/telegram_ingestor")
    whatsapp_result = await pipeline.run_ingestion("@user/whatsapp_ingestor")
    
    # Or run for all registered ingestors
    await pipeline.start()
    
    # Clean up resources
    await pipeline.close()
```

### Command Line Example

The provided example script can be used to run the pipeline:

```bash
# Run for all registered ingestors
python examples/default_pipeline_example.py

# Run for a specific ingestor
python examples/default_pipeline_example.py --ingestor-id @user/whatsapp_ingestor

# Force a full ingestion (ignore previous state)
python examples/default_pipeline_example.py --ingestor-id @user/telegram_ingestor --full

# Enable verbose logging
python examples/default_pipeline_example.py --verbose
```

## State Management

The pipeline tracks the state of each ingestor separately, allowing for:

- Full ingestion (when no previous state exists)
- Incremental ingestion (fetching only new data since last run)
- Independent reset of individual ingestors

The state includes:
- `last_timestamp`: Unix timestamp of the most recent processed message
- `additional_metadata`: Detailed statistics and processing information

## Error Handling

The pipeline includes comprehensive error handling:
- Component-level errors are caught and logged
- Each ingestor is processed independently to avoid cross-contamination
- Detailed logging provides insights into failures
- Health checking capabilities to verify component status

## Authentication

For WhatsApp, the pipeline handles authentication automatically:
- Checks authentication status before fetching data
- Provides authentication URL for QR code scanning if needed
- Waits for authentication with timeout

## Extension

The DefaultIngestionPipeline can be extended to support additional data sources:
1. Implement the ingestor interface for your data source
2. Implement the preprocessor for your data format
3. Add initialization code in the DefaultIngestionPipeline
4. Register your ingestor with a unique ID 