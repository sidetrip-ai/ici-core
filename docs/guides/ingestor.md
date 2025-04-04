# Ingestor Component Guide

## Overview

An Ingestor is responsible for fetching data from external sources such as messaging platforms, APIs, or data services. It handles authentication, data retrieval, and returning the data in a standardized format that can be processed by other components in the pipeline.

## Interface

All ingestors must implement the `Ingestor` interface defined in `ici/core/interfaces/ingestor.py`:

```python
class Ingestor(ABC):
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the ingestor with configuration parameters."""
        pass
        
    @abstractmethod
    async def fetch_full_data(self) -> Dict[str, Any]:
        """Fetch all available data from the source."""
        pass
        
    @abstractmethod
    async def fetch_new_data(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """Fetch new data since the specified time."""
        pass
        
    @abstractmethod
    async def fetch_data_in_range(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """Fetch data within a specific date range."""
        pass
```

## Expected Return Format

All fetch methods should return data in a consistent format:

```python
{
    "messages": [
        {
            "id": "unique_message_id",
            "text": "Message content",
            "date": "2023-06-15T12:34:56+00:00",  # ISO 8601 format
            "conversation_id": "chat_123",
            "conversation_name": "Chat Name",
            "sender_id": "user_456",
            "sender_name": "User Name",
            "timestamp": 1686835626,  # Unix timestamp (seconds)
            # Other message-specific fields
        },
        # More messages...
    ],
    "conversations": [
        {
            "id": "chat_123",
            "name": "Chat Name",
            "type": "direct",  # or "group", "channel", etc.
            # Other conversation-specific fields
        },
        # More conversations...
    ]
}
```

## Implementing a Custom Ingestor

Here's a step-by-step guide to implementing a custom ingestor:

### 1. Create a new class

Create a new file in `ici/adapters/ingestors/` for your custom ingestor:

```python
"""
MyService ingestor implementation.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from ici.core.interfaces.ingestor import Ingestor
from ici.adapters.loggers import StructuredLogger
from ici.utils.config import get_component_config
from ici.core.exceptions import ConfigurationError, DataFetchError
from ici.utils.datetime_utils import ensure_tz_aware

class MyServiceIngestor(Ingestor):
    """
    Ingestor implementation for MyService data source.
    
    Required config parameters:
    - api_key: API key for accessing MyService
    - base_url: API base URL
    """
    
    def __init__(self, logger_name: str = "myservice_ingestor"):
        """Initialize the MyService ingestor."""
        self.logger = StructuredLogger(name=logger_name)
        self._is_initialized = False
        self._config_path = None
        self._api_key = None
        self._base_url = None
```

### 2. Implement the initialize method

Load your configuration from config.yaml:

```python
async def initialize(self) -> None:
    """
    Initialize the MyService ingestor.
    
    Loads configuration from config.yaml and sets up any
    necessary connections or client instances.
    
    Raises:
        ConfigurationError: If required configuration is missing
    """
    try:
        # Set default config path if not specified
        self._config_path = self._config_path or "config.yaml"
        
        # Load config from file
        config = get_component_config("ingestors.myservice", self._config_path)
        
        if not config:
            raise ConfigurationError("No configuration found for MyService ingestor")
        
        # Extract required configuration
        self._api_key = config.get("api_key")
        self._base_url = config.get("base_url")
        
        if not self._api_key:
            raise ConfigurationError("API key is required for MyService ingestor")
        
        if not self._base_url:
            raise ConfigurationError("Base URL is required for MyService ingestor")
        
        # Initialize any API clients or connections
        # e.g., self._client = MyServiceClient(self._api_key, self._base_url)
        
        self._is_initialized = True
        
        self.logger.info({
            "action": "INGESTOR_INITIALIZED",
            "message": "MyService ingestor initialized successfully"
        })
        
    except Exception as e:
        self.logger.error({
            "action": "INITIALIZATION_ERROR",
            "message": f"Failed to initialize MyService ingestor: {str(e)}",
            "data": {"error": str(e), "error_type": type(e).__name__}
        })
        raise ConfigurationError(f"Failed to initialize MyService ingestor: {str(e)}") from e
```

### 3. Implement the fetch methods

Implement each of the required fetch methods:

```python
async def fetch_full_data(self) -> Dict[str, Any]:
    """
    Fetch all available data from MyService.
    
    Returns:
        Dict[str, Any]: Dictionary with messages and conversations
        
    Raises:
        DataFetchError: If data fetching fails
    """
    if not self._is_initialized:
        raise ConfigurationError("Ingestor not initialized. Call initialize() first.")
        
    try:
        self.logger.info({
            "action": "FETCH_FULL_DATA_START",
            "message": "Fetching all available data from MyService"
        })
        
        # Implement your data fetching logic here
        # Example:
        # raw_messages = await self._client.get_all_messages()
        # raw_conversations = await self._client.get_all_conversations()
        
        # Convert to standardized format
        messages = []
        conversations = []
        
        # Process and transform raw_messages and raw_conversations
        # Add to messages and conversations lists
        
        result = {
            "messages": messages,
            "conversations": conversations
        }
        
        self.logger.info({
            "action": "FETCH_FULL_DATA_COMPLETE",
            "message": f"Fetched {len(messages)} messages from {len(conversations)} conversations"
        })
        
        return result
        
    except Exception as e:
        self.logger.error({
            "action": "FETCH_FULL_DATA_ERROR",
            "message": f"Failed to fetch data from MyService: {str(e)}",
            "data": {"error": str(e), "error_type": type(e).__name__}
        })
        raise DataFetchError(f"Failed to fetch data from MyService: {str(e)}") from e

async def fetch_new_data(self, since: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Fetch new data from MyService since the given timestamp.
    
    Args:
        since: Timestamp to fetch data from. If None, defaults to 24 hours ago.
        
    Returns:
        Dict[str, Any]: Dictionary with new messages and conversations
        
    Raises:
        DataFetchError: If data fetching fails
    """
    if not self._is_initialized:
        raise ConfigurationError("Ingestor not initialized. Call initialize() first.")
    
    # Default to last 24 hours if no timestamp provided
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(days=1)
    
    # Ensure timestamp is timezone aware
    since = ensure_tz_aware(since)
    
    try:
        self.logger.info({
            "action": "FETCH_NEW_DATA_START",
            "message": f"Fetching new data since {since.isoformat()}",
            "data": {"since": since.isoformat()}
        })
        
        # Implement incremental data fetching logic
        # Example:
        # raw_messages = await self._client.get_messages_since(since)
        # raw_conversations = await self._client.get_updated_conversations_since(since)
        
        # Process and transform data to standardized format
        # ...
        
        # Return standardized data
        return {
            "messages": [],  # Populated with actual messages
            "conversations": []  # Populated with actual conversations
        }
        
    except Exception as e:
        self.logger.error({
            "action": "FETCH_NEW_DATA_ERROR",
            "message": f"Failed to fetch new data from MyService: {str(e)}",
            "data": {"error": str(e), "timestamp": since.isoformat()}
        })
        raise DataFetchError(f"Failed to fetch new data: {str(e)}") from e

async def fetch_data_in_range(self, start: datetime, end: datetime) -> Dict[str, Any]:
    """
    Fetch data from MyService within a specific date range.
    
    Args:
        start: Start of the date range
        end: End of the date range
        
    Returns:
        Dict[str, Any]: Dictionary with messages and conversations in the range
        
    Raises:
        DataFetchError: If data fetching fails
    """
    # Implementation similar to fetch_new_data but with start and end parameters
    # ...
```

## Configuration Setup

In your `config.yaml` file, add a section for your ingestor:

```yaml
ingestors:
  myservice:
    api_key: "your_api_key_here"
    base_url: "https://api.myservice.com/v1"
    request_timeout: 30
    max_retries: 3
    # Other configuration options specific to your ingestor
```

## Handle Authentication

If your data source requires authentication:

1. Implement authentication methods:
```python
async def check_authentication(self) -> Dict[str, Any]:
    """
    Check if the ingestor is authenticated with the data source.
    
    Returns:
        Dict[str, Any]: Authentication status and details
    """
    # Check authentication status
    # Example:
    # is_authenticated = await self._client.test_auth()
    
    return {
        "authenticated": True,  # Replace with actual check
        "expires_at": None,  # Optional expiration timestamp
        "user_id": "user_123"  # Optional authenticated user info
    }

async def get_authentication_url(self) -> str:
    """
    Get URL for authentication if not already authenticated.
    
    Returns:
        str: Authentication URL for the user to visit
    """
    # Generate or return authentication URL
    # Example:
    # auth_url = await self._client.get_auth_url()
    
    return "https://myservice.com/auth?token=xyz"

async def wait_for_authentication(self, timeout_seconds: int = 300) -> bool:
    """
    Wait for authentication to complete.
    
    Args:
        timeout_seconds: Maximum time to wait in seconds
        
    Returns:
        bool: True if authenticated, False if timed out
    """
    # Poll for authentication status
    # Example:
    # start_time = time.time()
    # while time.time() - start_time < timeout_seconds:
    #     if await self._client.is_authenticated():
    #         return True
    #     await asyncio.sleep(5)
    # return False
    
    return True  # Replace with actual implementation
```

## Best Practices

1. **Error Handling**: Catch and log specific exceptions. Use custom exceptions from `ici.core.exceptions`.

2. **Configuration**: Make your ingestor configurable with reasonable defaults. Document required configuration.

3. **Rate Limiting**: Implement rate limiting and retry logic to avoid overwhelming the data source.

4. **Incremental Fetching**: Optimize fetch_new_data to only retrieve necessary data.

5. **Data Transformation**: Convert data to the standardized format expected by preprocessors.

6. **Logging**: Use structured logging with action, message, and data fields.

7. **Timeout Handling**: Set appropriate timeouts for network requests.

8. **Authentication**: Implement robust authentication logic with refresh capabilities.

9. **Testing**: Write comprehensive unit tests with mocked external dependencies.

10. **Documentation**: Clearly document your ingestor's purpose, configuration, and requirements.

## Example Ingestors

Explore existing ingestors for reference:
- `ici/adapters/ingestors/telegram.py` - For Telegram data
- `ici/adapters/ingestors/whatsapp.py` - For WhatsApp data
