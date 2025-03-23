# Feature: Dynamic Ingestion Pipeline

## Overview

This document outlines the technical specification for transforming the existing TelegramIngestionPipeline into a dynamic, configuration-driven DefaultIngestionPipeline capable of managing multiple data sources simultaneously.

## Motivation

The current implementation uses a source-specific ingestion pipeline (TelegramIngestionPipeline), which limits extensibility and requires new pipeline implementations for each data source. By creating a generic DefaultIngestionPipeline, we can:

1. Support multiple data sources through configuration
2. Reuse shared components across ingestors
3. Add new data sources without code changes
4. Simplify system architecture and maintenance
5. Enable independent scheduling and state management per ingestor

This aligns with the technical specifications and functional requirements for a modular, extensible system.

## Architecture Design

### Current vs. Target Architecture

**Current Architecture**:
```
┌───────────────────────┐
│TelegramIngestionPipeline│
├───────────────────────┤
│- TelegramIngestor     │
│- TelegramPreprocessor │
│- Embedder             │
│- VectorStore          │
└───────────────────────┘
```

**Target Architecture**:
```
┌────────────────────────┐
│DefaultIngestionPipeline │
├────────────────────────┤
│- Component Registry    │
│- Scheduler             │
│- State Manager         │
│                        │
│  ┌─────────────────┐   │
│  │Shared Components│   │
│  │- Embedder       │   │
│  │- VectorStore    │   │
│  └─────────────────┘   │
│                        │
│  ┌─────────────────┐   │
│  │Ingestor Registry│   │
│  │┌───────────────┐│   │
│  ││@user/telegram ││   │
│  │└───────────────┘│   │
│  │┌───────────────┐│   │
│  ││@user/twitter  ││   │
│  │└───────────────┘│   │
│  └─────────────────┘   │
└────────────────────────┘
```

### Component Registry System

The DefaultIngestionPipeline will implement a component registry system with these key features:

1. **Dynamic Component Loading**: Load and instantiate components based on their type names in configuration
2. **Ingestor Registry**: Map ingestor IDs to their corresponding ingestor/preprocessor pairs
3. **Shared Component Management**: Load shared components (embedder, vector store, state manager) once and reuse across all ingestors
4. **Validation**: Ensure all components implement the required interfaces

## Configuration Structure

The new configuration structure supports multiple ingestors with their preprocessors:

```yaml
# Shared components
embedder:
  type: SentenceTransformerEmbedder
  config:
    model_name: "all-MiniLM-L6-v2"
    device: "cuda"

vector_store:
  type: FAISSVectorStore
  config:
    index_path: "index.faiss"

state_manager:
  type: SQLiteStateManager
  config:
    db_path: "state.db"

# Multiple ingestor definitions
ingestors:
  - id: "@alice/telegram_ingestor"
    ingestor:
      type: TelegramIngestor
      config:
        api_id: 12345
        api_hash: "zzz"
        session_string: "session_string"
        phone_number: "+911234567890"
    preprocessor:
      type: TelegramPreprocessor
      config:
        clean_urls: true
        
  - id: "@alice/twitter_ingestor"
    ingestor:
      type: TwitterIngestor
      config:
        api_key: "xxx"
        api_secret: "yyy"
    preprocessor:
      type: TwitterPreprocessor
      config:
        include_retweets: false

ingestion_pipeline:
  type: DefaultIngestionPipeline
  config:
    interval: 300  # seconds
    max_retries: 3
    schedule: true  # Enable scheduling
```

### Configuration Elements

- **Shared Components**: Common components used across all ingestors
- **Ingestor Array**: List of ingestor definitions, each with:
  - `id`: Unique identifier in the format `@username/ingestor-name`
  - `ingestor`: Ingestor component configuration
  - `preprocessor`: Preprocessor component configuration
- **Pipeline Configuration**: Settings for the DefaultIngestionPipeline itself

## Ingestor ID Management

### Format and Validation

Ingestor IDs follow the format `@username/ingestor-name`:

- `@username`: Identifies the user or organization responsible for the ingestor
- `/`: Separator for readability
- `ingestor-name`: Descriptive name of the ingestor's purpose or data source

Validation is performed using a regular expression:
```python
def _validate_ingestor_id(self, ingestor_id: str) -> bool:
    """Validate ingestor_id format."""
    if not ingestor_id:
        return False
    
    # Pattern: @username/ingestor-name
    pattern = r'^@[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, ingestor_id))
```

### Registry Implementation

The ingestor registry maps ingestor IDs to their component instances:

```python
# Structure of ingestor_registry
{
    "@alice/telegram_ingestor": {
        "ingestor": <TelegramIngestor instance>,
        "preprocessor": <TelegramPreprocessor instance>
    },
    "@alice/twitter_ingestor": {
        "ingestor": <TwitterIngestor instance>,
        "preprocessor": <TwitterPreprocessor instance>
    }
}
```

## Initialization Flow

The DefaultIngestionPipeline follows this initialization sequence:

1. **Configuration Loading**:
   - Load configuration from YAML file
   - Process any environment variable substitutions

2. **Shared Component Initialization**:
   - Initialize embedder
   - Initialize vector store
   - Initialize state manager

3. **Ingestor Registry Population**:
   - For each ingestor definition:
     - Validate ingestor ID format
     - Load ingestor component
     - Load preprocessor component
     - Store pair in registry with ingestor ID as key

4. **Scheduler Setup** (if enabled):
   - Configure scheduler with interval from config
   - Add jobs for each registered ingestor

5. **Error Handling**:
   - Log initialization errors
   - Continue with successfully initialized ingestors

```python
async def initialize(self):
    # Load shared components first
    self.embedder = await self._load_component(self.config['embedder'], Embedder)
    self.vector_store = await self._load_component(self.config['vector_store'], VectorStore)
    self.state_manager = await self._load_component(self.config['state_manager'], StateManager)
    
    # Process all ingestor definitions
    for ingestor_config in self.config.get('ingestors', []):
        ingestor_id = ingestor_config.get('id')
        
        # Validate ingestor_id format
        if not self._validate_ingestor_id(ingestor_id):
            self.logger.error(f"Invalid ingestor_id format: {ingestor_id}")
            continue
            
        try:
            # Load ingestor and preprocessor
            ingestor = await self._load_component(ingestor_config['ingestor'], Ingestor)
            preprocessor = await self._load_component(ingestor_config['preprocessor'], Preprocessor)
            
            # Register the pair
            self.ingestor_registry[ingestor_id] = {
                "ingestor": ingestor,
                "preprocessor": preprocessor
            }
            
            self.logger.info(f"Registered ingestor: {ingestor_id}")
        except Exception as e:
            self.logger.error(f"Failed to initialize ingestor {ingestor_id}: {str(e)}")
```

## Component Loading

The pipeline will implement a generic component loading system:

```python
async def _load_component(self, component_config, base_class):
    """Load and initialize a component from configuration."""
    component_type = component_config.get('type')
    config = component_config.get('config', {})
    
    if not component_type:
        raise ValueError(f"Missing type for {base_class.__name__} component")
    
    try:
        # Import the class using importlib
        module_path, class_name = self._get_class_path(component_type)
        module = importlib.import_module(module_path)
        component_class = getattr(module, class_name)
        
        # Verify it's a subclass of the expected base class
        if not issubclass(component_class, base_class):
            raise TypeError(f"{component_type} is not a valid {base_class.__name__}")
        
        # Instantiate the component
        component = component_class()
        
        # Configure it if it has a configure method
        if hasattr(component, "configure"):
            await component.configure(config)
            
        # Initialize it if it has an initialize method
        if hasattr(component, "initialize"):
            await component.initialize()
            
        return component
        
    except (ImportError, AttributeError) as e:
        raise ValueError(f"Failed to load component {component_type}: {str(e)}")
```

## Running Ingestion

When `run_ingestion(ingestor_id)` is called, the pipeline:

1. Looks up the components for the specified ingestor_id
2. Retrieves the last processed timestamp from the state manager
3. Uses the appropriate ingestor method based on state
4. Preprocesses the raw data
5. Generates embeddings for each document
6. Stores the documents in the vector store
7. Updates the ingestor state with the latest timestamp

```python
async def run_ingestion(self, ingestor_id: str) -> None:
    # Validate ingestor_id exists
    if ingestor_id not in self.ingestor_registry:
        raise ValueError(f"Unknown ingestor_id: {ingestor_id}")
    
    # Retrieve components
    components = self.ingestor_registry[ingestor_id]
    ingestor = components["ingestor"]
    preprocessor = components["preprocessor"]
    
    try:
        # Get last timestamp for this ingestor
        last_timestamp = await self.state_manager.get_last_timestamp(ingestor_id)
        
        # Fetch data based on last timestamp
        if last_timestamp is None:
            self.logger.info(f"Running full ingestion for {ingestor_id}")
            raw_data = await ingestor.fetch_full_data()
        else:
            self.logger.info(f"Running incremental ingestion for {ingestor_id} since {last_timestamp}")
            raw_data = await ingestor.fetch_new_data(since=last_timestamp)
        
        # Process data
        processed_data = await preprocessor.preprocess(raw_data)
        
        # Skip if no data
        if not processed_data:
            self.logger.info(f"No new data for {ingestor_id}")
            return
        
        # Generate embeddings
        for doc in processed_data:
            doc['vector'] = await self.embedder.embed(doc['text'])
        
        # Store in vector database
        await self.vector_store.store_documents(processed_data)
        
        # Update latest timestamp
        latest_timestamp = self._get_latest_timestamp(processed_data)
        if latest_timestamp:
            await self.state_manager.update_last_timestamp(ingestor_id, latest_timestamp)
            
        self.logger.info(f"Successfully ingested {len(processed_data)} documents for {ingestor_id}")
        
    except Exception as e:
        self.logger.error(f"Error during ingestion for {ingestor_id}: {str(e)}")
        # Implement retry logic here
```

## State Management

The state manager tracks progress for each ingestor separately:

```python
async def get_last_timestamp(self, ingestor_id: str) -> Optional[int]:
    """Get the last processed timestamp for the given ingestor."""
    # Query the database for the last timestamp
    query = "SELECT last_timestamp FROM ingestor_state WHERE ingestor_id = ?"
    result = await self.db.execute_query(query, (ingestor_id,))
    
    if result and result[0]:
        return result[0][0]
    return None

async def update_last_timestamp(self, ingestor_id: str, timestamp: int) -> None:
    """Update the last processed timestamp for the given ingestor."""
    # Insert or update the timestamp in the database
    query = """
    INSERT INTO ingestor_state (ingestor_id, last_timestamp) 
    VALUES (?, ?) 
    ON CONFLICT (ingestor_id) 
    DO UPDATE SET last_timestamp = ?
    """
    await self.db.execute_query(query, (ingestor_id, timestamp, timestamp))
```

## Scheduling

The DefaultIngestionPipeline will implement flexible scheduling:

```python
async def start(self) -> None:
    """Start the ingestion pipeline."""
    # Check if scheduling is enabled
    if self.config.get('schedule', True):
        interval = self.config.get('interval', 300)  # Default: 5 minutes
        
        # Initialize scheduler
        self.scheduler = AsyncIOScheduler()
        
        # Schedule each registered ingestor
        for ingestor_id in self.ingestor_registry.keys():
            self.scheduler.add_job(
                self.run_ingestion, 
                'interval', 
                seconds=interval,
                args=[ingestor_id]
            )
            
        self.scheduler.start()
        self.logger.info(f"Scheduled {len(self.ingestor_registry)} ingestors with interval: {interval}s")
    else:
        self.logger.info("Scheduling disabled, pipeline will run on-demand only")
        
    # Optionally run initial ingestion for all ingestors
    if self.config.get('run_on_start', False):
        for ingestor_id in self.ingestor_registry.keys():
            await self.run_ingestion(ingestor_id)
```

## Error Handling and Retries

The pipeline implements robust error handling:

1. **Component-level failures**: Log errors, continue with working components
2. **Ingestion failures**: Implement retry with exponential backoff
3. **Transaction safety**: Update state only after successful ingestion

```python
async def _run_with_retry(self, func, *args, **kwargs):
    """Run a function with retry logic."""
    max_retries = self.config.get('max_retries', 3)
    backoff_factor = self.config.get('backoff_factor', 2.0)
    
    attempt = 0
    while attempt < max_retries:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            attempt += 1
            if attempt >= max_retries:
                raise  # Re-raise after max retries
                
            wait_time = backoff_factor ** attempt
            self.logger.warning(f"Attempt {attempt} failed, retrying in {wait_time}s: {str(e)}")
            await asyncio.sleep(wait_time)
```

## Implementation Guidelines

### Migration Path

To migrate from TelegramIngestionPipeline to DefaultIngestionPipeline:

1. Implement the DefaultIngestionPipeline class with the component registry system
2. Convert the TelegramIngestor to be compatible with the new system
3. Create a TelegramPreprocessor class to handle Telegram-specific preprocessing
4. Update the configuration file structure
5. Test with the existing Telegram ingestion to ensure compatibility
6. Gradually add new ingestors as needed

### Key Design Principles

1. **Loose Coupling**: Each component operates independently
2. **Single Responsibility**: Each class has a focused purpose
3. **Interface-Based Design**: Components interact through well-defined interfaces
4. **Configuration-Driven**: Behavior defined through external configuration
5. **Fault Tolerance**: Problems in one ingestor don't affect others

### Testing Strategy

1. **Unit Tests**: Test each component in isolation
2. **Integration Tests**: Test the complete ingestion flow
3. **Configuration Tests**: Verify correct loading of different configuration formats
4. **Error Handling Tests**: Verify system resilience under failure conditions

## Benefits

This new architecture provides several advantages:

1. **Modularity**: Each ingestor/preprocessor pair is encapsulated and independent
2. **Scalability**: Easy to add new data sources without changing core pipeline code
3. **Resource Efficiency**: Shared components reduce memory footprint
4. **Maintainability**: Configuration-driven approach simplifies system evolution
5. **Fault Tolerance**: Problems with one ingestor don't affect others
6. **Flexibility**: Support for different schedules and configurations per ingestor

## Future Considerations

1. **Ingestor-Specific Scheduling**: Allow different intervals for different ingestors
2. **Priority-Based Ingestion**: Implement priority levels for time-sensitive sources
3. **Health Monitoring**: Add ingestor-specific health checks and statistics
4. **Parallel Ingestion**: Process multiple ingestors concurrently for efficiency
5. **Ingestor Registration API**: Provide an API for dynamic ingestor registration

## Conclusion

The transformation from TelegramIngestionPipeline to DefaultIngestionPipeline represents a significant architectural improvement, enabling a truly modular and extensible ingestion system that can grow with the platform's needs. By centralizing the ingestion logic while supporting diverse data sources, this approach aligns with the core design principles of the ICI system.

## AI Knowledge Snapshot

<ai:knowledge_representation>
SYSTEM_ARCHITECTURE{
  component:DefaultIngestionPipeline{
    responsibility:[manage_multiple_ingestors, coordinate_ingestion_flow, schedule_operations, handle_errors];
    key_attributes:[ingestor_registry, shared_components, scheduler, state_manager];
    initialization_flow:[load_config→init_shared_components→populate_registry→setup_scheduler];
    methods:[
      async_initialize(){load_components; register_ingestors; setup_scheduling},
      async_run_ingestion(ingestor_id){fetch_components; get_state; fetch_data; process; embed; store; update_state},
      async_start(){configure_scheduler; schedule_jobs; optional_immediate_run},
      _load_component(){dynamic_import; type_validation; instantiation; configuration},
      _validate_ingestor_id(){pattern_matching:"^@[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$"}
    ];
  }
  
  config_structure{
    shared_components:[embedder, vector_store, state_manager];
    ingestors:array_of{
      id:"@username/ingestor-name";
      ingestor:{type, config};
      preprocessor:{type, config};
    };
    ingestion_pipeline:{
      type:"DefaultIngestionPipeline";
      config:{interval, max_retries, schedule};
    }
  }
  
  component_relationships{
    Orchestrator->DefaultIngestionPipeline:initializes_and_starts;
    DefaultIngestionPipeline->Ingestor:dynamically_loads_per_config;
    DefaultIngestionPipeline->Preprocessor:pairs_with_ingestor;
    DefaultIngestionPipeline->StateManager:tracks_ingestion_progress;
    DefaultIngestionPipeline->Embedder:shared_across_ingestors;
    DefaultIngestionPipeline->VectorStore:shared_across_ingestors;
  }
  
  data_flow{
    ingestor->raw_data;
    raw_data->preprocessor->processed_data;
    processed_data->embedder->embedded_documents;
    embedded_documents->vector_store->stored_data;
    timestamp->state_manager->updated_state;
  }
  
  key_implementations{
    ingestor_registry:dict{ingestor_id->{"ingestor":instance, "preprocessor":instance}};
    state_management:db_operations{get_last_timestamp(ingestor_id), update_last_timestamp(ingestor_id, timestamp)};
    error_handling:exponential_backoff_retry{max_retries, backoff_factor};
    component_loading:dynamic_import{module_import, class_retrieval, interface_validation};
  }
  
  migration_strategy{
    from:TelegramIngestionPipeline{specific_to_telegram};
    to:DefaultIngestionPipeline{configurable_multi_source};
    steps:[implement_registry, adapt_telegram_components, configure_yaml, test_compatibility];
  }
}
</ai:knowledge_representation> 