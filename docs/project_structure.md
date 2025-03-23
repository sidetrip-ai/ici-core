# ICI-Core Project Structure

## Overview

This document outlines the agreed-upon directory structure for the ICI-Core project. The structure follows a Clean Architecture approach with source-specific organization for ingestors and preprocessors.

## Directory Structure Principles

1. **Source-Specific Organization**: Ingestors and preprocessors for each data source are grouped together in source-specific directories.
2. **Interface Separation**: All interfaces are defined in individual files within a dedicated interfaces directory.
3. **Logical Component Grouping**: Components are grouped based on their functionality and domain relationship.
4. **Clear Layer Separation**: The codebase is organized to maintain clear boundaries between architectural layers.

## Directory Tree

```
ici-core/
│
├── ici/
│   ├── __init__.py
│   │
│   ├── core/                      # Core domain logic
│   │   ├── __init__.py
│   │   ├── entities/
│   │   │   ├── __init__.py
│   │   │   ├── document.py
│   │   │   └── state.py
│   │   ├── interfaces/            # Each interface in its own file
│   │   │   ├── __init__.py
│   │   │   ├── ingestor.py
│   │   │   ├── preprocessor.py
│   │   │   ├── embedder.py
│   │   │   ├── vector_store.py
│   │   │   ├── validator.py
│   │   │   ├── prompt_builder.py
│   │   │   ├── generator.py
│   │   │   ├── logger.py
│   │   │   ├── orchestrator.py
│   │   │   └── pipeline.py
│   │   └── exceptions/
│   │       ├── __init__.py
│   │       ├── ingestion.py
│   │       ├── processing.py
│   │       └── query.py
│   │
│   ├── adapters/                  # Adapters (implementations)
│   │   ├── __init__.py
│   │   ├── data_sources/          # Source-specific adapters
│   │   │   ├── __init__.py
│   │   │   ├── telegram/          # All Telegram-specific components
│   │   │   │   ├── __init__.py
│   │   │   │   ├── ingestor.py
│   │   │   │   ├── preprocessor.py
│   │   │   │   └── models.py
│   │   │   ├── twitter/           # All Twitter-specific components
│   │   │   │   ├── __init__.py
│   │   │   │   ├── ingestor.py
│   │   │   │   ├── preprocessor.py
│   │   │   │   └── models.py
│   │   │   └── youtube/           # All YouTube-specific components
│   │   │       ├── __init__.py
│   │   │       ├── ingestor.py
│   │   │       ├── preprocessor.py
│   │   │       └── models.py
│   │   ├── embedders/
│   │   │   ├── __init__.py
│   │   │   ├── sentence_transformer.py
│   │   │   └── openai.py
│   │   ├── vector_stores/
│   │   │   ├── __init__.py
│   │   │   ├── faiss.py
│   │   │   └── pinecone.py
│   │   ├── validators/
│   │   │   ├── __init__.py
│   │   │   └── rule_based.py
│   │   ├── prompt_builders/
│   │   │   ├── __init__.py
│   │   │   └── default.py
│   │   ├── generators/
│   │   │   ├── __init__.py
│   │   │   ├── openai.py
│   │   │   ├── anthropic.py
│   │   │   └── local.py
│   │   └── loggers/
│   │       ├── __init__.py
│   │       ├── console.py
│   │       └── file.py
│   │
│   ├── services/                  # Service layer
│   │   ├── __init__.py
│   │   ├── ingestion_pipeline.py
│   │   └── orchestrator.py
│   │
│   ├── infrastructure/            # External dependencies and IO
│   │   ├── __init__.py
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   └── loader.py
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   └── operations.py
│   │   └── external/              # External API clients
│   │       ├── __init__.py
│   │       ├── telegram_api.py
│   │       ├── twitter_api.py
│   │       └── youtube_api.py
│   │
│   └── utils/                     # Utilities
│       ├── __init__.py
│       ├── retry.py
│       └── validation.py
│
├── tests/                         # Test directory
│   ├── __init__.py
│   ├── unit/                      # Unit tests
│   │   ├── core/
│   │   ├── adapters/
│   │   └── services/
│   └── integration/               # Integration tests
│       ├── ingestion/
│       └── query/
│
├── config/                        # Configuration files
│   ├── config.yaml                # Default configuration
│   ├── config.dev.yaml            # Development-specific configuration
│   └── config.prod.yaml           # Production-specific configuration
│
├── scripts/                       # Utility scripts
│   ├── run_ingestion.py
│   └── initialize_db.py
│
├── main.py                        # Entry point
└── README.md
```

## Component Placement Guidelines

### Where to place new components

| Component Type | Directory Location | Example |
|----------------|-------------------|---------|
| New data source | `ici/adapters/data_sources/{source_name}/` | `ici/adapters/data_sources/slack/` |
| New embedder | `ici/adapters/embedders/` | `ici/adapters/embedders/huggingface.py` |
| New vector store | `ici/adapters/vector_stores/` | `ici/adapters/vector_stores/qdrant.py` |
| New utility | `ici/utils/` | `ici/utils/string_processing.py` |
| Core interface | `ici/core/interfaces/` | `ici/core/interfaces/storage.py` |
| External API client | `ici/infrastructure/external/` | `ici/infrastructure/external/slack_api.py` |

### Naming Conventions

* **Interfaces**: Should be named descriptively without prefixes/suffixes (`ingestor.py`, not `i_ingestor.py` or `ingestor_interface.py`)
* **Implementations**: Should be named after their specific implementation (`openai.py`, `anthropic.py`, etc.)
* **Source-specific components**: Should be consistently named across sources (`ingestor.py`, `preprocessor.py`, `models.py`)

## Adding New Components

When adding a new component:

1. Identify the appropriate layer for your component (core, adapter, service, infrastructure)
2. Determine if it belongs to an existing source or represents a new source
3. Follow the established directory structure and naming conventions
4. Create necessary test files in the corresponding test directory

### Example: Adding a new data source (Slack)

1. Create a new directory structure:
   ```
   ici/adapters/data_sources/slack/
   ├── __init__.py
   ├── ingestor.py
   ├── preprocessor.py
   └── models.py
   ```

2. Add corresponding test files:
   ```
   tests/unit/adapters/data_sources/slack/
   ├── test_ingestor.py
   └── test_preprocessor.py
   ```

## Maintaining the Structure

* Run linting tools to ensure adherence to the structure
* Review PRs for structural compliance
* Update this document when structural changes are agreed upon
* Refactor existing code if it doesn't follow the current guidelines

## Questions and Exceptions

For questions about where a specific component should be placed or to propose exceptions to these guidelines, please open a discussion in the project issue tracker or team communication channels. 