# WhatsApp Python Ingestor Specification

## Overview

This document outlines the technical specifications for the WhatsApp Python ingestor component. This Python class will implement the Ingestor interface and communicate with the Node.js WhatsApp service to fetch and process WhatsApp messages.

## Architecture

### Component Structure

```
┌─────────────────────────────────────────────────┐
│             WhatsAppIngestor Class              │
├─────────────────────────────────────────────────┤
│ ┌─────────────┐  ┌───────────────┐             │
│ │ HTTP Client │  │ WebSocket     │             │
│ │             │  │ Client        │             │
│ └─────────────┘  └───────────────┘             │
│                                                 │
│ ┌─────────────────────────────────────────────┐ │
│ │             Methods                         │ │
│ │ ┌───────────────┐  ┌─────────────────────┐ │ │
│ │ │ initialize()  │  │ fetch_full_data()   │ │ │
│ │ └───────────────┘  └─────────────────────┘ │ │
│ │ ┌───────────────┐  ┌─────────────────────┐ │ │
│ │ │ fetch_new_data│  │fetch_data_in_range()│ │ │
│ │ └───────────────┘  └─────────────────────┘ │ │
│ │ ┌───────────────┐                         │ │
│ │ │ healthcheck() │                         │ │
│ │ └───────────────┘                         │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

## Implementation

### WhatsApp Ingestor Class

The WhatsAppIngestor class will implement the standard Ingestor interface:

```python
"""
WhatsApp ingestor implementation using WhatsApp Web JS via a Node.js service.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, cast

import aiohttp
import websockets
from ici.core.interfaces.ingestor import Ingestor
from ici.adapters.loggers import StructuredLogger
from ici.utils.config import get_component_config, load_config
from ici.core.exceptions import ConfigurationError
from ici.utils.datetime_utils import from_isoformat, ensure_tz_aware


class WhatsAppIngestor(Ingestor):
    """
    Ingests messages from WhatsApp using WhatsApp Web JS via a Node.js service.
    
    Required config parameters:
    - service_url: URL of the WhatsApp Node.js service
    - websocket_url: WebSocket URL for real-time events
    - request_timeout: Timeout for HTTP requests in seconds
    """
    
    def __init__(self, logger_name: str = "whatsapp_ingestor"):
        """
        Initialize the WhatsApp ingestor.
        
        Args:
            logger_name: Name for the logger instance.
        """
        self.logger = StructuredLogger(name=logger_name)
        self._config = None
        self._service_url = None
        self._websocket_url = None
        self._request_timeout = 30  # Default timeout in seconds
        self._websocket = None
        self._message_queue = asyncio.Queue()
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        self._is_listening = False
        self._listener_task = None
    
    async def initialize(self) -> None:
        """
        Initialize the ingestor with configuration from config.yaml.
        
        Returns:
            None
            
        Raises:
            ConfigurationError: If required configuration parameters are missing.
        """
        try:
            # Load config from file if it exists
            try:
                full_config = load_config(self._config_path)
                whatsapp_config = get_component_config("ingestors.whatsapp", self._config_path)
                self.logger.debug({
                    "action": "CONFIG_LOADED",
                    "message": "WhatsApp configuration loaded successfully"
                })
            except Exception as e:
                raise ConfigurationError(f"Failed to load configuration: {str(e)}") from e
            
            # Validate configuration
            required_params = ["service_url", "websocket_url"]
            missing_params = [param for param in required_params if param not in whatsapp_config]
            
            if missing_params:
                raise ConfigurationError(f"Missing required parameters: {', '.join(missing_params)}")
            
            # Store the configuration
            self._config = whatsapp_config
            self._service_url = whatsapp_config["service_url"]
            self._websocket_url = whatsapp_config["websocket_url"]
            
            # Set request timeout if provided
            if "request_timeout" in whatsapp_config:
                self._request_timeout = int(whatsapp_config["request_timeout"])
            
            # Initialize the WhatsApp service and get QR code if needed
            await self._initialize_whatsapp_service()
            
            # Start WebSocket listener for real-time updates
            await self._start_websocket_listener()
            
            self.logger.info({
                "action": "INGESTOR_INITIALIZED",
                "message": "WhatsApp ingestor initialized successfully"
            })
            
        except Exception as e:
            error_message = f"Failed to initialize WhatsApp ingestor: {str(e)}"
            self.logger.error({
                "action": "INITIALIZATION_ERROR",
                "message": error_message,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise ConfigurationError(error_message) from e
    
    async def _initialize_whatsapp_service(self) -> Dict[str, Any]:
        """
        Initialize the WhatsApp service and handle QR code if needed.
        
        Returns:
            Dict[str, Any]: Service status information
        """
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self._service_url}/initialize",
                    timeout=self._request_timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ConfigurationError(f"Failed to initialize WhatsApp service: {error_text}")
                    
                    data = await response.json()
                    
                    # Check if we need to display QR code
                    if not data.get("ready", False) and data.get("qrCode"):
                        qr_code = data["qrCode"]
                        # Display QR code for scanning
                        print("\n" + "=" * 80)
                        print("SCAN THIS QR CODE WITH WHATSAPP")
                        print("=" * 80)
                        print(f"Open WhatsApp on your phone, go to Settings > WhatsApp Web/Desktop")
                        print(f"Scan the QR code displayed at {self._service_url}/initialize in a browser")
                        print("=" * 80 + "\n")
                        
                        self.logger.info({
                            "action": "QR_CODE_GENERATED",
                            "message": "QR code displayed for WhatsApp authentication"
                        })
                    
                    return data
                    
            except aiohttp.ClientError as e:
                self.logger.error({
                    "action": "SERVICE_CONNECTION_ERROR",
                    "message": f"Failed to connect to WhatsApp service: {str(e)}",
                    "data": {"error": str(e), "error_type": type(e).__name__}
                })
                raise ConfigurationError(f"Failed to connect to WhatsApp service: {str(e)}") from e
    
    async def _start_websocket_listener(self) -> None:
        """
        Start a WebSocket listener for real-time updates.
        """
        if self._is_listening:
            return
        
        self._is_listening = True
        self._listener_task = asyncio.create_task(self._listen_for_updates())
        
        self.logger.debug({
            "action": "WEBSOCKET_LISTENER_STARTED",
            "message": "Started WebSocket listener for real-time updates"
        })
    
    async def _listen_for_updates(self) -> None:
        """
        Listen for updates from the WebSocket connection.
        """
        retry_delay = 1
        max_retry_delay = 60
        
        while self._is_listening:
            try:
                async with websockets.connect(self._websocket_url) as websocket:
                    self._websocket = websocket
                    retry_delay = 1  # Reset retry delay on successful connection
                    
                    self.logger.debug({
                        "action": "WEBSOCKET_CONNECTED",
                        "message": "Connected to WebSocket server"
                    })
                    
                    while True:
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        # Process different event types
                        if data.get("type") == "message":
                            # Add to message queue for processing
                            await self._message_queue.put(data.get("data"))
                            
                            self.logger.debug({
                                "action": "WEBSOCKET_MESSAGE_RECEIVED",
                                "message": "Received message event from WebSocket"
                            })
                        
                        elif data.get("type") == "status":
                            self.logger.info({
                                "action": "WHATSAPP_STATUS_UPDATE",
                                "message": f"WhatsApp status update: {data.get('status')}",
                                "data": {"status": data.get("status")}
                            })
                        
                        elif data.get("type") == "qr":
                            self.logger.info({
                                "action": "WHATSAPP_QR_UPDATED",
                                "message": "WhatsApp QR code updated"
                            })
                        
            except (websockets.exceptions.ConnectionClosed, 
                    websockets.exceptions.ConnectionClosedError,
                    websockets.exceptions.ConnectionClosedOK) as e:
                self.logger.warning({
                    "action": "WEBSOCKET_DISCONNECTED",
                    "message": f"WebSocket connection closed: {str(e)}",
                    "data": {"error": str(e), "error_type": type(e).__name__}
                })
            
            except Exception as e:
                self.logger.error({
                    "action": "WEBSOCKET_ERROR",
                    "message": f"WebSocket error: {str(e)}",
                    "data": {"error": str(e), "error_type": type(e).__name__}
                })
            
            # Only retry if still listening
            if self._is_listening:
                self.logger.info({
                    "action": "WEBSOCKET_RETRY",
                    "message": f"Retrying WebSocket connection in {retry_delay} seconds",
                    "data": {"retry_delay": retry_delay}
                })
                
                await asyncio.sleep(retry_delay)
                
                # Exponential backoff with maximum
                retry_delay = min(retry_delay * 2, max_retry_delay)
    
    async def _stop_websocket_listener(self) -> None:
        """
        Stop the WebSocket listener.
        """
        self._is_listening = False
        
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
        
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
        
        self.logger.debug({
            "action": "WEBSOCKET_LISTENER_STOPPED",
            "message": "Stopped WebSocket listener"
        })
    
    async def fetch_full_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch all available WhatsApp conversations and their messages.
        
        Returns:
            Dict[str, List[Dict[str, Any]]]: Dictionary containing conversations and messages.
        """
        self.logger.info({
            "action": "FETCH_FULL_DATA_START",
            "message": "Fetching all available WhatsApp conversations and messages"
        })
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self._service_url}/messages",
                    timeout=self._request_timeout
                ) as response:
                    if response.status != 200:
                        self.logger.error({
                            "action": "FETCH_FULL_DATA_ERROR",
                            "message": f"Error fetching data: {response.status}",
                            "data": {"status_code": response.status}
                        })
                        return {"conversations": [], "messages": []}
                    
                    data = await response.json()
                    
                    self.logger.info({
                        "action": "FETCH_FULL_DATA_COMPLETE",
                        "message": f"Fetched {len(data.get('conversations', []))} conversations and {len(data.get('messages', []))} messages",
                        "data": {
                            "conversation_count": len(data.get('conversations', [])),
                            "message_count": len(data.get('messages', []))
                        }
                    })
                    
                    return data
                    
            except aiohttp.ClientError as e:
                self.logger.error({
                    "action": "FETCH_FULL_DATA_ERROR",
                    "message": f"Client error when fetching data: {str(e)}",
                    "data": {"error": str(e), "error_type": type(e).__name__}
                })
                return {"conversations": [], "messages": []}
                
            except Exception as e:
                self.logger.error({
                    "action": "FETCH_FULL_DATA_ERROR",
                    "message": f"Error fetching data: {str(e)}",
                    "data": {"error": str(e), "error_type": type(e).__name__}
                })
                return {"conversations": [], "messages": []}
    
    async def fetch_new_data(self, since: Optional[datetime] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch new message data since the given timestamp.
        
        Args:
            since: Optional timestamp to fetch data from.
                  If None, defaults to 24 hours ago.
                  
        Returns:
            Dict[str, List[Dict[str, Any]]]: Dictionary containing conversations and new messages.
        """
        # Default to last 24 hours if no timestamp provided
        if since is None:
            since = datetime.now(tz=timezone.utc) - timedelta(days=1)
        
        # Ensure timestamp is timezone aware
        since = ensure_tz_aware(since)
        
        # Convert to ISO format for API
        since_str = since.isoformat()
        
        self.logger.info({
            "action": "FETCH_NEW_DATA_START",
            "message": f"Fetching new WhatsApp data since {since_str}",
            "data": {"since": since_str}
        })
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self._service_url}/messages",
                    params={"since": since_str},
                    timeout=self._request_timeout
                ) as response:
                    if response.status != 200:
                        self.logger.error({
                            "action": "FETCH_NEW_DATA_ERROR",
                            "message": f"Error fetching new data: {response.status}",
                            "data": {"status_code": response.status}
                        })
                        return {"conversations": [], "messages": []}
                    
                    data = await response.json()
                    
                    self.logger.info({
                        "action": "FETCH_NEW_DATA_COMPLETE",
                        "message": f"Fetched {len(data.get('conversations', []))} conversations and {len(data.get('messages', []))} messages since {since_str}",
                        "data": {
                            "conversation_count": len(data.get('conversations', [])),
                            "message_count": len(data.get('messages', [])),
                            "since": since_str
                        }
                    })
                    
                    return data
                    
            except aiohttp.ClientError as e:
                self.logger.error({
                    "action": "FETCH_NEW_DATA_ERROR",
                    "message": f"Client error when fetching new data: {str(e)}",
                    "data": {"error": str(e), "error_type": type(e).__name__, "since": since_str}
                })
                return {"conversations": [], "messages": []}
                
            except Exception as e:
                self.logger.error({
                    "action": "FETCH_NEW_DATA_ERROR",
                    "message": f"Error fetching new data: {str(e)}",
                    "data": {"error": str(e), "error_type": type(e).__name__, "since": since_str}
                })
                return {"conversations": [], "messages": []}
    
    async def fetch_data_in_range(self, start: datetime, end: datetime) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch message data within a specific date range.
        
        Args:
            start: Start timestamp for data range.
            end: End timestamp for data range.
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: Dictionary containing conversations and messages in range.
        """
        # Ensure timestamps are timezone aware
        start = ensure_tz_aware(start)
        end = ensure_tz_aware(end)
        
        # Convert to ISO format for API
        start_str = start.isoformat()
        end_str = end.isoformat()
        
        self.logger.info({
            "action": "FETCH_DATA_IN_RANGE_START",
            "message": f"Fetching WhatsApp data from {start_str} to {end_str}",
            "data": {"start": start_str, "end": end_str}
        })
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self._service_url}/messages",
                    params={"since": start_str, "until": end_str},
                    timeout=self._request_timeout
                ) as response:
                    if response.status != 200:
                        self.logger.error({
                            "action": "FETCH_DATA_IN_RANGE_ERROR",
                            "message": f"Error fetching data in range: {response.status}",
                            "data": {"status_code": response.status}
                        })
                        return {"conversations": [], "messages": []}
                    
                    data = await response.json()
                    
                    self.logger.info({
                        "action": "FETCH_DATA_IN_RANGE_COMPLETE",
                        "message": f"Fetched {len(data.get('conversations', []))} conversations and {len(data.get('messages', []))} messages in date range",
                        "data": {
                            "conversation_count": len(data.get('conversations', [])),
                            "message_count": len(data.get('messages', [])),
                            "start": start_str,
                            "end": end_str
                        }
                    })
                    
                    return data
                    
            except aiohttp.ClientError as e:
                self.logger.error({
                    "action": "FETCH_DATA_IN_RANGE_ERROR",
                    "message": f"Client error when fetching data in range: {str(e)}",
                    "data": {"error": str(e), "error_type": type(e).__name__, "start": start_str, "end": end_str}
                })
                return {"conversations": [], "messages": []}
                
            except Exception as e:
                self.logger.error({
                    "action": "FETCH_DATA_IN_RANGE_ERROR",
                    "message": f"Error fetching data in range: {str(e)}",
                    "data": {"error": str(e), "error_type": type(e).__name__, "start": start_str, "end": end_str}
                })
                return {"conversations": [], "messages": []}
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Check if the ingestor is properly configured and can connect to the WhatsApp service.
        
        Returns:
            Dict[str, Any]: Dictionary containing health status information.
        """
        try:
            self.logger.info({
                "action": "HEALTHCHECK_START",
                "message": "Performing WhatsApp ingestor health check"
            })
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self._service_url}/status",
                    timeout=self._request_timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ConfigurationError(f"WhatsApp service returned non-200 status: {response.status}, {error_text}")
                    
                    status_data = await response.json()
                    
                    health_status = {
                        "healthy": status_data.get("ready", False),
                        "message": "Connected to WhatsApp" if status_data.get("ready", False) else "WhatsApp not connected, QR code needs to be scanned",
                        "details": {
                            "service_url": self._service_url,
                            "websocket_url": self._websocket_url,
                            "connection_status": "ready" if status_data.get("ready", False) else "waiting_for_qr"
                        }
                    }
                    
                    self.logger.info({
                        "action": "HEALTHCHECK_SUCCESS" if health_status["healthy"] else "HEALTHCHECK_WAITING",
                        "message": health_status["message"],
                        "data": health_status
                    })
                    
                    return health_status
                    
        except Exception as e:
            error_message = f"Health check failed: {str(e)}"
            
            health_status = {
                "healthy": False,
                "message": error_message,
                "details": {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "service_url": self._service_url,
                    "websocket_url": self._websocket_url
                }
            }
            
            self.logger.error({
                "action": "HEALTHCHECK_FAILED",
                "message": error_message,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            
            return health_status
    
    async def __del__(self) -> None:
        """
        Clean up resources when the ingestor is deleted.
        """
        if hasattr(self, '_is_listening') and self._is_listening:
            await self._stop_websocket_listener()


class WhatsAppPreprocessor:
    """
    Preprocesses WhatsApp messages before they are stored.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the WhatsApp preprocessor.
        
        Args:
            config: Optional configuration for the preprocessor.
        """
        self.config = config or {}
        self.logger = StructuredLogger(name="whatsapp_preprocessor")
    
    def process(self, data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Process raw message data from WhatsApp.
        
        Args:
            data: Raw message data.
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: Processed message data.
        """
        self.logger.info({
            "action": "PREPROCESSING_START",
            "message": f"Preprocessing {len(data.get('messages', []))} WhatsApp messages",
            "data": {"message_count": len(data.get('messages', []))}
        })
        
        # Apply preprocessing steps to messages
        processed_messages = []
        for message in data.get("messages", []):
            processed_message = self._preprocess_message(message)
            if processed_message:
                processed_messages.append(processed_message)
        
        # Return processed data
        result = {
            "conversations": data.get("conversations", []),
            "messages": processed_messages
        }
        
        self.logger.info({
            "action": "PREPROCESSING_COMPLETE",
            "message": f"Preprocessing complete, {len(processed_messages)} messages after processing",
            "data": {"processed_message_count": len(processed_messages)}
        })
        
        return result
    
    def _preprocess_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Preprocess a single message.
        
        Args:
            message: Raw message data.
            
        Returns:
            Optional[Dict[str, Any]]: Processed message or None if message should be filtered out.
        """
        # Create a copy to avoid modifying the original
        processed = message.copy()
        
        # Add source if not present
        if "source" not in processed:
            processed["source"] = "whatsapp"
        
        # Clean URLs if configured
        if self.config.get("clean_urls", False) and "text" in processed:
            processed["text"] = self._clean_urls(processed["text"])
        
        # Skip system messages if configured
        if self.config.get("remove_system_messages", False):
            # Identify system messages (e.g., "Messages and calls are end-to-end encrypted")
            system_patterns = [
                "Messages and calls are end-to-end encrypted",
                "changed the group description",
                "changed the subject from",
                "added you",
                "left",
                "removed",
                "changed this group's settings",
                "changed their phone number"
            ]
            
            if any(pattern in processed.get("text", "") for pattern in system_patterns):
                return None
        
        # Format date consistently if needed
        if "date" in processed and not processed["date"].endswith("Z"):
            # Convert timestamp to ISO format with Z suffix
            try:
                timestamp = float(processed["date"]) / 1000.0 if isinstance(processed["date"], (int, float)) else float(processed["date"])
                processed["date"] = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
            except (ValueError, TypeError):
                # If conversion fails, keep the original
                pass
        
        return processed
    
    def _clean_urls(self, text: str) -> str:
        """
        Clean URLs in message text.
        
        Args:
            text: Original message text.
            
        Returns:
            str: Text with cleaned URLs.
        """
        # This is a simple example - implement more sophisticated URL cleaning if needed
        import re
        
        # Replace URLs with a placeholder or clean version
        url_pattern = r'https?://[^\s]+'
        return re.sub(url_pattern, "[URL]", text)
```

## Testing Strategy

### Unit Testing

The WhatsApp ingestor should be tested with the following unit tests:

```python
# test_whatsapp_ingestor.py
import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from ici.adapters.ingestors.whatsapp import WhatsAppIngestor, WhatsAppPreprocessor


@pytest.fixture
def mock_aiohttp_response():
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "conversations": [
            {
                "id": "1234567890@c.us",
                "name": "Test Contact",
                "last_message": {
                    "id": "msg123",
                    "date": "2023-06-15T10:30:00Z",
                    "text": "Hello there"
                },
                "last_updated": "2023-06-15T10:30:00Z",
                "total_messages": 42
            }
        ],
        "messages": [
            {
                "id": "msg123",
                "conversation_id": "1234567890@c.us",
                "date": "2023-06-15T10:30:00Z",
                "text": "Hello there",
                "from_user": True,
                "sender_id": "sender_id@c.us",
                "conversation_name": "Test Contact",
                "source": "whatsapp"
            }
        ]
    })
    return mock_response


@pytest.fixture
def mock_whatsapp_ingestor():
    with patch('ici.adapters.ingestors.whatsapp.get_component_config') as mock_get_config:
        mock_get_config.return_value = {
            "service_url": "http://localhost:3000",
            "websocket_url": "ws://localhost:3001",
            "request_timeout": 30
        }
        
        ingestor = WhatsAppIngestor()
        return ingestor


class TestWhatsAppIngestor:
    @pytest.mark.asyncio
    async def test_initialize(self, mock_whatsapp_ingestor):
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"ready": True})
            mock_get.return_value.__aenter__.return_value = mock_response
            
            await mock_whatsapp_ingestor.initialize()
            
            assert mock_whatsapp_ingestor._service_url == "http://localhost:3000"
            assert mock_whatsapp_ingestor._websocket_url == "ws://localhost:3001"
            assert mock_whatsapp_ingestor._request_timeout == 30
    
    @pytest.mark.asyncio
    async def test_fetch_full_data(self, mock_whatsapp_ingestor, mock_aiohttp_response):
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_aiohttp_response
            
            # Initialize first
            mock_whatsapp_ingestor._service_url = "http://localhost:3000"
            mock_whatsapp_ingestor._websocket_url = "ws://localhost:3001"
            mock_whatsapp_ingestor._request_timeout = 30
            
            result = await mock_whatsapp_ingestor.fetch_full_data()
            
            assert "conversations" in result
            assert "messages" in result
            assert len(result["conversations"]) == 1
            assert len(result["messages"]) == 1
            assert result["messages"][0]["id"] == "msg123"
    
    @pytest.mark.asyncio
    async def test_fetch_new_data(self, mock_whatsapp_ingestor, mock_aiohttp_response):
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_aiohttp_response
            
            # Initialize first
            mock_whatsapp_ingestor._service_url = "http://localhost:3000"
            mock_whatsapp_ingestor._websocket_url = "ws://localhost:3001"
            mock_whatsapp_ingestor._request_timeout = 30
            
            since = datetime.now(timezone.utc) - timedelta(days=1)
            result = await mock_whatsapp_ingestor.fetch_new_data(since)
            
            assert "conversations" in result
            assert "messages" in result
            assert len(result["messages"]) == 1
            
            # Verify the since parameter was used
            assert "since" in mock_get.call_args[1]["params"]
    
    @pytest.mark.asyncio
    async def test_healthcheck(self, mock_whatsapp_ingestor):
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"ready": True})
            mock_get.return_value.__aenter__.return_value = mock_response
            
            # Initialize first
            mock_whatsapp_ingestor._service_url = "http://localhost:3000"
            mock_whatsapp_ingestor._websocket_url = "ws://localhost:3001"
            mock_whatsapp_ingestor._request_timeout = 30
            
            result = await mock_whatsapp_ingestor.healthcheck()
            
            assert result["healthy"] is True
            assert "Connected to WhatsApp" in result["message"]


class TestWhatsAppPreprocessor:
    def test_process(self):
        # Create sample data
        data = {
            "conversations": [
                {
                    "id": "1234567890@c.us",
                    "name": "Test Contact"
                }
            ],
            "messages": [
                {
                    "id": "msg1",
                    "conversation_id": "1234567890@c.us",
                    "date": "2023-06-15T10:30:00Z",
                    "text": "Check this link https://example.com/test",
                    "from_user": True,
                    "sender_id": "sender_id@c.us"
                },
                {
                    "id": "msg2",
                    "conversation_id": "1234567890@c.us",
                    "date": "2023-06-15T10:35:00Z",
                    "text": "Messages and calls are end-to-end encrypted",
                    "from_user": False,
                    "sender_id": "system"
                }
            ]
        }
        
        # Create preprocessor with config to clean URLs and remove system messages
        preprocessor = WhatsAppPreprocessor({
            "clean_urls": True,
            "remove_system_messages": True
        })
        
        # Process the data
        result = preprocessor.process(data)
        
        # Verify results
        assert len(result["messages"]) == 1  # System message should be removed
        assert "[URL]" in result["messages"][0]["text"]  # URL should be cleaned
        assert result["messages"][0]["source"] == "whatsapp"  # Source should be added
```

## Integration with Pipeline

The WhatsApp ingestor should be registered in the same way as other ingestors in the dynamic ingestion pipeline:

```yaml
# In config.yaml
ingestors:
  - id: "@user/whatsapp_ingestor"
    ingestor:
      type: WhatsAppIngestor
      config:
        service_url: "http://localhost:3000"
        websocket_url: "ws://localhost:3001"
        request_timeout: 30
    preprocessor:
      type: WhatsAppPreprocessor
      config:
        clean_urls: true
        remove_system_messages: true
```

## Usage Example

```python
async def example_usage():
    # Create and initialize the ingestor
    ingestor = WhatsAppIngestor()
    await ingestor.initialize()
    
    # Check health to verify connection
    health = await ingestor.healthcheck()
    print(f"WhatsApp connection status: {health['message']}")
    
    # Fetch recent messages (last 24 hours)
    data = await ingestor.fetch_new_data()
    
    # Create and use preprocessor
    preprocessor = WhatsAppPreprocessor({"clean_urls": True})
    processed_data = preprocessor.process(data)
    
    # Print some stats
    print(f"Retrieved {len(processed_data['conversations'])} conversations")
    print(f"Retrieved {len(processed_data['messages'])} messages")
    
    # Show most recent messages
    if processed_data['messages']:
        print("\nMost recent messages:")
        for msg in sorted(processed_data['messages'], 
                         key=lambda m: m.get('date', ''), reverse=True)[:5]:
            print(f"[{msg.get('date')}] {msg.get('conversation_name')}: {msg.get('text')}")
```

## Security Considerations

1. **Data Security**:
   - All HTTP requests to the Node.js service should be over HTTPS in production
   - WebSocket connections should use secure WebSockets (WSS)
   - Sensitive data (messages, contact info) should be handled according to privacy requirements

2. **Error Handling**:
   - All external calls should have proper timeout handling
   - Circuit breakers should be implemented for service resilience
   - Exponential backoff for connection retries

3. **Authentication**:
   - Consider adding API key authentication between Python and Node.js services
   - Implement proper session handling for WhatsApp authentication

## Future Enhancements

1. **Media Support**:
   - Add handling for images, audio, and document messages
   - Implement media downloading and processing

2. **Session Management**:
   - Improve session persistence between restarts
   - Add ability to manage multiple WhatsApp accounts

3. **Performance Optimizations**:
   - Implement caching for frequently accessed data
   - Add batching for large message sets
   - Optimize WebSocket communication

## Conclusion

The WhatsApp Python ingestor component provides a robust interface to the Node.js WhatsApp service, enabling seamless integration of WhatsApp messaging data into the ICI system. By implementing the standard Ingestor interface, it maintains compatibility with the existing architecture while extending functionality to include this popular messaging platform. 