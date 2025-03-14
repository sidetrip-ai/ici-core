# Technical Specifications for the Intelligent Consciousness Interface (ICI)

## 1. Overview
The **Intelligent Consciousness Interface (ICI)** is a modular, extensible framework designed to create a personal AI assistant that is **context-aware**, **style-aware**, **personality-aware**, and **security-aware**. It ingests data from diverse sources (e.g., Telegram, Twitter, YouTube), processes it into a searchable format, and responds to user queries by leveraging a vector database for efficient retrieval and a language model for response generation. The system is architecturally divided into two primary pipelines: the **Ingestion Pipeline** for data processing and storage, and the **Query Pipeline** for handling user interactions.

---

## 2. Architecture
The ICI framework consists of two distinct pipelines, each with well-defined responsibilities, ensuring separation of concerns and independent scalability:

### 2.1 Ingestion Pipeline
- **Purpose**: Continuously ingests raw data from external sources, processes it into a standardized format, generates vector embeddings, and stores it in a vector database for efficient retrieval.
- **Components**:
  - **IngestionPipeline**: Coordinates the ingestion workflow and manages scheduling.
  - **Ingestor**: Fetches raw data from a specific source (e.g., Telegram messages, Twitter posts).
  - **Preprocessor**: Transforms raw data into a consistent, structured format.
  - **Embedder**: Converts text into vector embeddings for semantic representation.
  - **VectorStore**: Persists processed data and embeddings for later use.
  - **ingestor_state**: Database table for tracking ingestion progress and state.

### 2.2 Query Pipeline
- **Purpose**: Processes user queries by validating input, retrieving relevant data, constructing prompts, and generating tailored responses.
- **Components**:
  - **Orchestrator**: Coordinates the query workflow, integrating all components.
  - **Validator**: Enforces security and validation rules on user input.
  - **Embedder**: Embeds the query for retrieval (shared with the Ingestion Pipeline).
  - **VectorStore**: Retrieves relevant documents based on query embeddings (shared with the Ingestion Pipeline).
  - **PromptBuilder**: Constructs prompts for the language model using retrieved data.
  - **Generator**: Produces the final response using a language model.

- **Shared Components**:
  - **Logger**: Provides structured logging across all components for debugging and monitoring.

---

## 3. Component Specifications
Each component is implemented as an abstract base class (ABC) in Python, ensuring a consistent interface, modularity, and type safety through type hints. Below are detailed specifications for each component, including their purpose, interface, finer details, and design choice thesis.

### 3.1 Ingestor
- **Purpose**: Fetches raw data from a specific external source (e.g., Telegram, Twitter, YouTube) for processing.
- **Interface**:
  ```python
  from abc import ABC, abstractmethod
  from typing import Any, Optional
  from datetime import datetime

  class Ingestor(ABC):
      @abstractmethod
      def fetch_full_data(self) -> Any:
          """Fetches all available data for initial ingestion."""
          pass

      @abstractmethod
      def fetch_new_data(self, since: Optional[datetime] = None) -> Any:
          """Fetches new data since the given timestamp."""
          pass

      @abstractmethod
      def fetch_data_in_range(self, start: datetime, end: datetime) -> Any:
          """Fetches data within a specified date range."""
          pass
  ```
- **Details**:
  - Each `Ingestor` is designed for a specific data source, handling authentication and API-specific logic.
  - Returns raw data in a source-native format (e.g., JSON, XML) for the `Preprocessor` to handle.
  - The `since` parameter in `fetch_new_data` enables incremental ingestion, fetching only data newer than the specified timestamp.
  - State (e.g., last fetch timestamp) is managed externally in the `ingestor_state` table to keep the `Ingestor` stateless and focused on data retrieval.
  - Error handling includes specific exception types (e.g., `IngestorError`) with detailed messages for different failure scenarios.
- **Design Choice Thesis**:  
  The `Ingestor` is kept source-specific in implementation but abstract in its interface to allow seamless integration of new data sources. By externalizing state management, it remains lightweight and reusable across different ingestion schedules or pipelines. This design ensures scalability—new sources can be added by subclassing `Ingestor` without altering the core ingestion logic—while supporting continuous, incremental data updates.

### 3.2 Preprocessor
- **Purpose**: Transforms raw, source-specific data into a standardized format suitable for embedding and storage.
- **Interface**:
  ```python
  from abc import ABC, abstractmethod
  from typing import Any, List, Dict

  class Preprocessor(ABC):
      @abstractmethod
      def preprocess(self, raw_data: Any) -> List[Dict[str, Any]]:
          """Transforms raw data into a list of standardized documents."""
          pass
  ```
- **Details**:
  - Paired with a specific `Ingestor` to handle its unique data structure.
  - Output format:
    - `'text'`: `str` - The primary content to be embedded (e.g., tweet text, message body).
    - `'metadata'`: `Dict[str, Any]` - Contextual data (e.g., `{'source': 'Twitter', 'timestamp': 1698777600, 'user_id': '123'}`).
  - Handles data cleaning (e.g., removing URLs, normalizing text) as needed for the source.
  - Ensures consistent document format for downstream processing, regardless of source.
- **Design Choice Thesis**:  
  The `Preprocessor` normalizes diverse data into a unified structure, decoupling source-specific logic from downstream processes. This separation allows the `Embedder` and `VectorStore` to operate uniformly, regardless of the data's origin. By pairing each `Preprocessor` with an `Ingestor`, the system remains modular and extensible, enabling tailored preprocessing for new sources without affecting existing workflows.

### 3.3 Embedder
- **Purpose**: Generates vector embeddings from text data for both ingestion and querying, ensuring consistent semantic representation.
- **Interface**:
  ```python
  from abc import ABC, abstractmethod
  from typing import List

  class Embedder(ABC):
      @abstractmethod
      def embed(self, text: str) -> List[float]:
          """Generates a vector embedding from the input text."""
          pass
  ```
- **Details**:
  - Shared between the Ingestion and Query Pipelines to ensure identical embedding logic.
  - Output is a fixed-length list of floats (e.g., 384 dimensions for a model like `all-MiniLM-L6-v2`).
  - Supports batch processing internally for efficiency when embedding multiple texts.
  - Maintains consistency across pipelines to ensure accurate similarity matching.
- **Design Choice Thesis**:  
  A shared `Embedder` ensures that data stored in the `VectorStore` aligns with query embeddings, enabling accurate similarity searches. Centralizing embedding logic simplifies updates (e.g., switching to a new model) and maintains consistency across the system. This design choice enhances retrieval precision and reduces redundancy, critical for a context-aware assistant.

### 3.4 VectorStore
- **Purpose**: Stores processed documents with embeddings and retrieves relevant data based on vector similarity.
- **Interface**:
  ```python
  from abc import ABC, abstractmethod
  from typing import List, Dict, Any

  class VectorStore(ABC):
      @abstractmethod
      def store_documents(self, documents: List[Dict[str, Any]]) -> None:
          """Stores documents with their vectors, text, and metadata."""
          pass

      @abstractmethod
      def search(self, query_vector: List[float], num_results: int, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
          """Retrieves the most similar documents based on the query vector."""
          pass
  ```
- **Details**:
  - Input to `store_documents`: List of dictionaries with:
    - `'vector'`: `List[float]` - Embedding vector.
    - `'text'`: `str` - Original text content.
    - `'metadata'`: `Dict[str, Any]` - Contextual data (e.g., source, timestamp).
  - `search` supports advanced metadata filtering with comparison operators:
    - Equality: `{'source': 'Twitter'}`
    - Greater than/less than: `{'timestamp': {'gte': 1698777600}}`
    - Array containment: `{'tags': {'in': ['important', 'urgent']}}`
    - Logical combinations: `{'$and': [{'source': 'Twitter'}, {'timestamp': {'gte': 1698777600}}]}`
  - Implementations can use in-memory (e.g., FAISS) or external (e.g., Pinecone) storage.
  - Throws specific `VectorStoreError` exceptions with detailed messages for search and storage failures.
- **Design Choice Thesis**:  
  The `VectorStore` abstracts the underlying storage technology, allowing flexibility in scaling from local to distributed systems. Metadata filtering enhances context-awareness by enabling retrieval tailored to specific criteria (e.g., time or source). This design supports efficient, scalable searches, crucial for real-time query handling in a growing dataset.

### 3.5 Validator
- **Purpose**: Ensures user input adheres to security and compliance rules before processing.
- **Interface**:
  ```python
  from abc import ABC, abstractmethod
  from typing import Dict, Any, List

  class Validator(ABC):
      @abstractmethod
      def validate(self, input: str, context: Dict[str, Any], rules: List[Dict[str, Any]]) -> bool:
          """Validates the input based on provided rules and context."""
          pass
  ```
- **Details**:
  - Rules are dynamically supplied as structured dictionaries for maximum flexibility:
    - Keyword filtering: `{'type': 'keyword', 'forbidden': ['delete', 'drop']}`
    - Time restrictions: `{'type': 'time', 'allowed_hours': [8, 18]}`
    - User permissions: `{'type': 'permission', 'required_level': 'admin'}`
    - Content length: `{'type': 'length', 'max': 1000, 'min': 5}`
    - Pattern matching: `{'type': 'regex', 'pattern': '^[a-zA-Z0-9\\s]+$'}`
  - `context` provides runtime data (e.g., `{'user_id': '123', 'timestamp': 1698777600}`) for rule evaluation.
  - Returns `True` if input passes all rules, `False` otherwise.
  - Can provide detailed validation failure reasons through optional parameter.
- **Design Choice Thesis**:  
  A dynamic, rule-based `Validator` allows the system to adapt to varying security needs without hardcoding logic. Passing rules at runtime supports diverse use cases (e.g., user permissions, time restrictions), enhancing security and flexibility. This design ensures the assistant remains compliant and safe, protecting both users and the system.

### 3.6 PromptBuilder
- **Purpose**: Constructs prompts for the language model by integrating user input with retrieved documents.
- **Interface**:
  ```python
  from abc import ABC, abstractmethod
  from typing import List, Dict, Any

  class PromptBuilder(ABC):
      @abstractmethod
      def build_prompt(self, input: str, documents: List[Dict[str, Any]]) -> str:
          """Constructs a prompt from the input and retrieved documents."""
          pass
  ```
- **Details**:
  - Default behavior: Combines document texts into a context section (e.g., "Context: doc1\n doc2\n\nQuestion: input").
  - Handles edge cases through specific fallback mechanisms:
    - No documents: "Answer based on general knowledge: input"
    - Empty or invalid input: Returns standardized error prompt
    - Excessive content: Implements truncation strategies to fit model context windows
  - Supports customizable templates via configuration, with variable substitution.
  - Can prioritize documents based on relevance scores from the vector search.
  - Implements robust fallback logic for various scenarios:
    - When no relevant documents are found: Uses a configurable fallback template
    - When context is too large: Applies intelligent truncation strategies
    - When input is malformed: Returns a standardized error prompt
  - Provides template customization through YAML configuration:
    ```yaml
    prompt_builder:
      template: "Context:\n{context}\n\nQuestion: {question}"
      fallback_template: "Answer based on general knowledge: {question}"
      error_template: "Unable to process: {error}"
    ```
- **Design Choice Thesis**:  
  Decoupling prompt construction from generation allows for flexible prompt strategies (e.g., few-shot, instruction-based) tailored to different models or use cases. This modularity ensures the assistant can adapt to evolving language model requirements, optimizing response quality and relevance. The addition of robust fallback mechanisms ensures graceful handling of edge cases, maintaining a consistent user experience even when ideal conditions are not met.

### 3.7 Generator
- **Purpose**: Produces the final response using a language model based on the constructed prompt.
- **Interface**:
  ```python
  from abc import ABC, abstractmethod

  class Generator(ABC):
      @abstractmethod
      def generate(self, prompt: str) -> str:
          """Generates an output based on the prompt."""
          pass
  ```
- **Details**:
  - Supports multiple language models through provider-specific implementations:
    - OpenAI models (e.g., GPT-4, GPT-3.5)
    - xAI's Grok
    - Anthropic's Claude
    - Local models (e.g., Llama 2, Mistral)
  - Model parameters are configured externally via YAML with comprehensive options:
    - `temperature`: Controls randomness (0.0-2.0)
    - `max_tokens`: Limits response length
    - `top_p`: Controls diversity via nucleus sampling
    - `frequency_penalty`: Reduces word repetition
    - `presence_penalty`: Reduces topic repetition
  - Handles API-specific logic (e.g., retries, rate limiting, authentication) within concrete implementations.
  - Implements robust error handling with exponential backoff for temporary failures.
- **Design Choice Thesis**:  
  Abstracting the language model behind the `Generator` interface enables seamless integration of different models or providers. This design supports future enhancements (e.g., custom fine-tuned models) and ensures the system remains agnostic to model-specific details, enhancing adaptability and longevity.

### 3.8 Orchestrator
- **Purpose**: Manages the query pipeline, coordinating components from validation to response generation.
- **Interface**:
  ```python
  from abc import ABC, abstractmethod
  from typing import Dict, Any, List

  class Orchestrator(ABC):
      @abstractmethod
      def process_query(self, input: str, user_id: str) -> str:
          """Manages query processing from validation to generation."""
          pass
  ```
- **Details**:
  - Workflow:
    1. Retrieves validation rules dynamically based on `user_id` from a runtime source (database, config file)
    2. Builds context for validation based on `user_id` and runtime data
    3. Validates input with `validator.validate(input, context, rules)`
    4. If validation fails, returns appropriate error message
    5. Generates query embedding with `embedder.embed(input)`
    6. Retrieves relevant documents with `vector_store.search(query_vector, num_results, filters={'user_id': user_id})`
    7. Constructs prompt with `prompt_builder.build_prompt(input, documents)`
    8. Generates response with `generator.generate(prompt)`
    9. Returns final output or error message
  - Dynamic Rule and Context Management:
    - Rules are fetched at runtime using methods like `get_rules(user_id)`
    - Context is retrieved dynamically, customized to the specific user
    - Filters for vector search include user-specific parameters 
  - Handles errors at each step with appropriate recovery strategies:
    - Validation failure: "Access denied: [reason]"
    - Embedding failure: "Cannot process query at this time"
    - Search failure: Falls back to general knowledge response
    - Generation failure: "Failed to generate response: [reason]"
  - Implements retry mechanisms with exponential backoff for critical operations
  - Logs each step via the `Logger` for traceability and debugging
  - Supports custom error messages through configuration
- **Design Choice Thesis**:  
  The `Orchestrator` centralizes query handling and rule/context management, ensuring a consistent workflow while delegating tasks to specialized components. By dynamically retrieving rules and context at runtime rather than accepting them as parameters, the system gains improved security, modularity, and real-time adaptability to user-specific data and policies. This design maintains the ability for components to be swapped or upgraded independently and enhances reliability by managing errors gracefully, critical for user-facing interactions.

### 3.9 IngestionPipeline
- **Purpose**: Manages the ingestion process, including scheduling, state tracking, and component coordination.
- **Interface**:
  ```python
  from abc import ABC, abstractmethod

  class IngestionPipeline(ABC):
      @abstractmethod
      def run_ingestion(self, ingestor_id: str) -> None:
          """Executes the ingestion process for a specific ingestor."""
          pass

      @abstractmethod
      def start(self) -> None:
          """Starts the continuous ingestion loop or scheduler."""
          pass
  ```
- **Details**:
  - Coordinates `Ingestor`, `Preprocessor`, `Embedder`, and `VectorStore` in a sequential workflow:
    1. Retrieves ingestor state from the database (including `last_timestamp`)
    2. Calls appropriate ingestor method based on state
    3. Preprocesses raw data into standardized format
    4. Generates embeddings for each document
    5. Stores documents with vectors and metadata
    6. Updates ingestor state with the latest timestamp
  - Uses a configurable scheduler with various strategies:
    - Fixed interval: Run every N seconds
    - Cron-style: Run at specific times
    - Event-based: Run in response to triggers
  - Implements fault-tolerance through transaction-like processing:
    - Updates state only after successful completion
    - Includes retry logic for temporary failures
    - Logs detailed error information for failed ingestions
  - Can be run as a background process or separate service.
- **Design Choice Thesis**:  
  Encapsulating ingestion logic in a dedicated `IngestionPipeline` ensures that data updates run independently of query handling. This separation supports continuous ingestion without impacting performance, while the scheduler provides flexibility for different data source needs, enhancing scalability and autonomy.

### 3.10 Logger
- **Purpose**: Provides structured logging across all components for monitoring and debugging.
- **Interface**:
  ```python
  from abc import ABC, abstractmethod
  from typing import Any

  class Logger(ABC):
      @abstractmethod
      def debug(self, message: str, *args: Any) -> None:
          pass

      @abstractmethod
      def info(self, message: str, *args: Any) -> None:
          pass

      @abstractmethod
      def warning(self, message: str, *args: Any) -> None:
          pass

      @abstractmethod
      def error(self, message: str, *args: Any) -> None:
          pass

      @abstractmethod
      def critical(self, message: str, *args: Any) -> None:
          pass
  ```
- **Details**:
  - Supports multiple severity levels (debug, info, warning, error, critical).
  - Implementations can log to multiple destinations simultaneously:
    - Console output with colored formatting
    - Rotating file logs with size limits
    - External services (e.g., ELK stack, CloudWatch)
  - Structured log format includes:
    - Timestamp with millisecond precision
    - Log level
    - Component name
    - Message with formatted arguments
    - Optional context data (e.g., user ID, request ID)
  - Used consistently across pipelines for comprehensive event tracking.
  - Configurable verbosity through log level thresholds.
- **Design Choice Thesis**:  
  A centralized `Logger` ensures uniform logging practices, critical for debugging, auditing, and monitoring a complex system. Abstracting the logging mechanism allows flexibility in output destinations (e.g., local files, cloud services), supporting operational needs without altering component code.

---

## 4. Database Schema
A SQLite database persists state information for ingestion tracking.

- **Table**: `ingestor_state`
  ```sql
  CREATE TABLE ingestor_state (
      ingestor_id TEXT PRIMARY KEY,
      last_timestamp INTEGER,
      additional_metadata TEXT
  );
  ```
- **Fields**:
  - `ingestor_id`: Unique identifier (e.g., "@alice/twitter_ingestor").
  - `last_timestamp`: Epoch timestamp (e.g., 1698777600) of the most recent processed data.
  - `additional_metadata`: Optional text field (e.g., JSON string) storing extensible state information such as:
    - Pagination tokens or cursors for resuming API requests
    - Rate limiting information
    - API-specific context (e.g., tweet IDs, message IDs)
    - Error counts and backoff parameters
    - Statistics on processed items
- **Indices**:
  - Primary key on `ingestor_id` ensures uniqueness
- **Usage**:
  - Queried before ingestion to determine starting point
  - Updated after successful ingestion to record progress
  - Managed by the `IngestionPipeline` component
  - Critical for enabling incremental ingestion and resumability
- **Design Choice Thesis**:  
  SQLite provides a lightweight, file-based solution for state persistence, ideal for simplicity and portability. The `ingestor_state` table ensures resumable ingestion after interruptions, maintaining data integrity with minimal overhead. The extensible `additional_metadata` field enables storage of source-specific state without schema changes, supporting future requirements while keeping the core schema simple. This design allows future scalability (e.g., to a distributed database) if needed.

---

## 5. Ingestor ID Management
- **Format**: User-defined as `@username/ingestor-name` (e.g., "@alice/twitter_ingestor").
- **Components**:
  - `@username`: Identifies the user or organization responsible for the ingestor
  - `/`: Separator for readability
  - `ingestor-name`: Descriptive name of the ingestor's purpose or data source
- **Uniqueness**: Enforced by the `ingestor_id` primary key in `ingestor_state`.
- **Validation**: Implemented at the application level with regex pattern `^@[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$`
- **Future Consideration**: Implement a registration script or service to assign and reserve IDs, preventing duplicates (not in current scope).
- **Design Choice Thesis**:  
  The `@username/ingestor-name` format offers user-friendly, structured naming while minimizing collisions via database constraints. This approach balances flexibility with system integrity, deferring centralized ID management to future iterations for simplicity in the initial design.

---

## 6. Configuration
The system is configured via a YAML file, specifying components and their settings.

- **Example Configuration**:
  ```yaml
  database:
    path: "state.db"

  logger:
    type: ConsoleLogger
    config:
      level: "INFO"
      format: "{timestamp} [{level}] {component}: {message}"
      console_colors: true

  ingestion_pipeline:
    type: DefaultIngestionPipeline
    config:
      interval: 300  # seconds between ingestion cycles
      max_retries: 3
      retry_delay: 60  # seconds

  ingestors:
    - type: TwitterIngestor
      config:
        api_key: "xxx"
        api_secret: "yyy"
        max_items_per_request: 100
      ingestor_id: "@alice/twitter_ingestor"
    
    - type: TelegramIngestor
      config:
        api_id: 12345
        api_hash: "zzz"
        chat_ids: [111, 222, 333]
      ingestor_id: "@alice/telegram_ingestor"

  embedder:
    type: SentenceTransformerEmbedder
    config:
      model_name: "all-MiniLM-L6-v2"
      device: "cuda" # or "cpu"
      batch_size: 32

  vector_store:
    type: FAISSVectorStore
    config:
      index_path: "index.faiss"
      dimension: 384
      index_type: "IVFFlat"
      metric: "cosine"

  validator:
    type: RuleBasedValidator
    config:
      default_rules:
        - type: "length"
          max: 1000
        - type: "keyword"
          forbidden: ["drop", "delete", "remove"]

  prompt_builder:
    type: DefaultPromptBuilder
    config:
      template: "Context:\n{context}\n\nQuestion: {question}"
      max_context_length: 4000
      fallback_template: "Answer based on general knowledge: {question}"
      error_template: "Unable to process: {error}"

  generator:
    type: OpenAIGenerator
    config:
      model: "gpt-4"
      api_key: "aaa"
      temperature: 0.7
      max_tokens: 500
      frequency_penalty: 0.5
      presence_penalty: 0.5
      timeout: 30

  orchestrator:
    type: DefaultOrchestrator
    config:
      log_level: "INFO"
      num_results: 5
      rules_source: "database"  # Where to fetch validation rules from
      context_filters:
        user_id: true  # Include user_id in filters
        timestamp_range: true  # Support time-based filtering
      error_messages:
        validation_failed: "Access denied: {reason}"
        generation_failed: "Unable to generate response at this time."
      retry:
        max_attempts: 3
        backoff_factor: 2.0  # Exponential backoff multiplier
  ```
- **File Locations**:
  - Default: `config.yaml` in the application root
  - Override with environment variable: `ICI_CONFIG_PATH`
  - Support for environment-specific configs: `config.{env}.yaml`
- **Variable Substitution**:
  - Environment variables: `${ENV_VAR}`
  - Secrets from external sources: `!secret SECRET_NAME`
- **Rules and Context Configuration**:
  - Rules can be stored in database or config files and referenced by `rules_source`
  - Context filters determine what metadata is used when retrieving documents
  - User-specific settings can be applied through the `user_id` parameter
- **Design Choice Thesis**:  
  A YAML-based configuration provides a readable, editable interface for customizing the system without code changes. This approach supports rapid experimentation (e.g., swapping models) and serves as self-documentation, enhancing usability and maintainability. The comprehensive configuration schema ensures all components can be fully customized, while sensible defaults reduce the burden on users for common scenarios. The addition of dynamic rule and context management enables real-time adaptability to user-specific requirements and security policies.

---

## 7. Error Handling
- **Component-Level**: Each component raises specific exceptions (e.g., `IngestorError`, `VectorStoreError`) with detailed messages.
  ```python
  class IngestorError(Exception):
      """Base exception for all ingestor-related errors."""
      pass

  class APIAuthenticationError(IngestorError):
      """Raised when API authentication fails."""
      pass

  class APIRateLimitError(IngestorError):
      """Raised when API rate limits are exceeded."""
      pass
      
  class ValidationError(Exception):
      """Raised when input validation fails."""
      pass
      
  class VectorStoreError(Exception):
      """Base exception for all vector store related errors."""
      pass
      
  class EmbeddingError(Exception):
      """Raised when embedding generation fails."""
      pass
      
  class PromptBuilderError(Exception):
      """Raised when prompt construction fails."""
      pass
      
  class GenerationError(Exception):
      """Raised when text generation fails."""
      pass
  ```
- **Pipeline-Level**: The `IngestionPipeline` and `Orchestrator` catch exceptions, log them via the `Logger`, and handle them appropriately (e.g., retrying ingestion, returning "Query failed" to the user).
- **Retry Strategies**:
  - Exponential backoff for transient errors (e.g., network issues, rate limits)
    ```python
    def retry_with_backoff(func, max_attempts=3, backoff_factor=2.0):
        """Retry a function with exponential backoff."""
        attempt = 0
        while attempt < max_attempts:
            try:
                return func()
            except (APIRateLimitError, ConnectionError) as e:
                attempt += 1
                if attempt == max_attempts:
                    raise
                wait_time = backoff_factor ** attempt
                logger.warning(f"Attempt {attempt} failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
    ```
  - Circuit breaking for persistent failures to prevent cascading issues
  - Fallback mechanisms for critical components
- **User-Facing Errors**:
  - Sanitized error messages that avoid exposing system details
  - Customizable through configuration
  - Contextual hints for recoverable errors (e.g., "Try again later")
- **Logging**: All errors are logged with:
  - Exception type and message
  - Component and operation that failed
  - Context data (e.g., input parameters)
  - Stack trace for debugging (in development/testing environments)
- **Error Recovery**:
  - Transient failures (e.g., network issues): Automatic retries with exponential backoff
  - Validation failures: Clear error messages with specific reasons
  - Resource exhaustion: Graceful degradation with fallback options
  - Critical failures: Detailed logging and administrator notifications
- **Design Choice Thesis**:  
  Structured error handling prevents system crashes and ensures graceful degradation. Logging all errors aids in diagnostics, while user-friendly responses maintain trust and usability, balancing reliability with transparency. The typed exception hierarchy enables precise error handling, allowing components to fail in predictable ways that can be appropriately managed by orchestration layers. Implementing retry mechanisms with exponential backoff ensures resilience against transient failures, particularly when interacting with external services.

---

## 8. Data Flow

### 8.1 Ingestion Data Flow
1. **Retrieve State**: `IngestionPipeline` queries `ingestor_state` for `last_timestamp` by `ingestor_id`.
2. **Fetch Data**: `raw_data = ingestor.fetch_new_data(since=last_timestamp)`.
3. **Preprocess**: `processed_data = preprocessor.preprocess(raw_data)`.
4. **Embed**: For each `doc` in `processed_data`, `doc['vector'] = embedder.embed(doc['text'])`.
5. **Store**: `vector_store.store_documents(processed_data)`.
6. **Update State**: Update `ingestor_state` with the latest timestamp from `processed_data`.
- **Error Handling**:
  - Fetch failure: Log error, retry with backoff, reuse last state
  - Preprocessing failure: Log error, skip batch, continue with next batch
  - Embedding failure: Log error, retry or skip individual documents
  - Storage failure: Log error, retry before updating state
- **Design Choice Thesis**:  
  This flow ensures efficient, incremental ingestion by leveraging state tracking, avoiding redundant processing. The sequential design guarantees data consistency and supports continuous updates, critical for real-time applications. Each step is isolated to contain failures, preventing partial data processing and maintaining system integrity through robust error handling.

### 8.2 Query Data Flow
1. **Retrieve Rules**: `rules = orchestrator.get_rules(user_id)` - Fetch validation rules based on user ID.
2. **Build Context**: `context = orchestrator.build_context(user_id)` - Build validation context with user-specific data.
3. **Validate**: `if not validator.validate(input, context, rules): return "Access denied."`.
4. **Embed**: `query_vector = embedder.embed(input)`.
5. **Retrieve**: `documents = vector_store.search(query_vector, num_results=5, filters={'user_id': user_id})`.
6. **Build Prompt**: `prompt = prompt_builder.build_prompt(input, documents)`.
7. **Generate**: `output = generator.generate(prompt)`.
8. **Return**: Return `output`.
- **Performance Considerations**:
  - Dynamic rule retrieval enables real-time policy enforcement
  - User-specific context improves validation accuracy
  - Validation is performed first to fail fast and save resources
  - Embedding reuses the same models as ingestion for consistency
  - Metadata filters can dramatically improve search relevance
  - Prompt construction optimizes context window usage
  - Generation can be configured for speed vs. quality tradeoffs
- **Design Choice Thesis**:  
  The query flow prioritizes security (validation first) and relevance (vector-based retrieval), ensuring fast, accurate responses. Modularity in each step allows for customization, optimizing the assistant's performance for diverse queries. The step-by-step processing approach maximizes performance by applying filters early and ensuring each component receives well-formed inputs, reducing errors in subsequent stages. Dynamic rule and context retrieval enhances security and personalization by adapting to each user's specific requirements and permissions.

---

## 9. Pipeline Interaction and Dependencies
- **Component Reuse**:
  - The `Embedder` and `VectorStore` components are reused between both pipelines, ensuring consistent embedding and retrieval logic.
  - The `Logger` is used by all components across both pipelines for unified logging.
- **Pipeline Independence**:
  - Each pipeline can operate independently, with the `IngestionPipeline` running on a schedule and the `Orchestrator` responding to user queries on demand.
  - This separation allows each pipeline to scale according to its own requirements.
- **State Management**:
  - The `ingestor_state` table is the critical linkage between ingestion runs, enabling incremental processing.
  - State is only updated after successful completion of an ingestion cycle to ensure data integrity.
- **Sequence Flows**:
  - The `IngestionPipeline` operates in a loop or according to a schedule, with each cycle following the sequence: retrieve state → fetch data → preprocess → embed → store → update state.
  - The `Orchestrator` follows a conditional sequence for each query: validate → embed → retrieve → build prompt → generate → return.
- **Error Propagation**:
  - Errors in the `IngestionPipeline` are contained within the pipeline, with appropriate logging and retry mechanisms.
  - Errors in the `Orchestrator` are translated into user-friendly messages while preserving detailed logging for debugging.
- **Design Choice Thesis**:  
  This clear separation of responsibilities with shared components where appropriate enables independent development, testing, and scaling of each pipeline while maintaining consistency in critical areas like embedding and storage. The well-defined sequence flows and error boundaries ensure reliable operation and clear debugging paths.

---

## 10. High-Level Design Choice Thesis
The ICI framework's architecture is guided by these principles:
- **Modularity**: Components are single-purpose and interchangeable, enabling independent upgrades (e.g., swapping `Generator` models).
  - **Evidence**: Each component has a focused interface with a single responsibility
  - **Benefit**: New implementations can be developed and deployed without affecting the entire system
- **Separation of Concerns**: Distinct ingestion and query pipelines prevent interference, allowing independent optimization and scaling.
  - **Evidence**: Pipelines operate independently with shared components where appropriate
  - **Benefit**: Each pipeline can be scaled and optimized based on its specific load characteristics
- **Scalability**: Vector-based storage and incremental ingestion support growing datasets and real-time updates.
  - **Evidence**: State tracking enables efficient incremental updates
  - **Benefit**: System can handle increasing data volumes without performance degradation
- **Flexibility**: Abstract interfaces and YAML configuration allow customization without code changes, adapting to user needs.
  - **Evidence**: All components are configured via YAML with sensible defaults
  - **Benefit**: Behavior can be modified without programming knowledge
- **Reliability**: State persistence, error handling, and logging ensure robust operation and recovery from failures.
  - **Evidence**: Comprehensive error handling and logging throughout the system
  - **Benefit**: System can recover from failures and maintain data integrity

This design creates a robust, adaptable framework capable of evolving with technological advancements and user requirements, delivering a personalized, secure, and efficient AI assistant experience. The explicit design choice thesis for each component provides clear rationales for architectural decisions, ensuring that implementations adhere to the guiding principles while allowing reasonable customization for specific use cases.
