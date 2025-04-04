"""
WhatsApp ingestor implementation using WhatsApp Web JS via a Node.js service.
"""

import asyncio
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, cast

import aiohttp
from ici.core.interfaces.ingestor import Ingestor
from ici.adapters.loggers import StructuredLogger
from ici.utils.config import get_component_config, load_config
from ici.core.exceptions import ConfigurationError, IngestorError, DataFetchError, AuthenticationError
from ici.utils.datetime_utils import from_isoformat, ensure_tz_aware


class WhatsAppIngestor(Ingestor):
    """
    Ingests messages from WhatsApp using WhatsApp Web JS via a Node.js service.
    
    Required config parameters:
    - service_url: URL of the WhatsApp Node.js service
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
        self._request_timeout = 30  # Default timeout in seconds
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        self._session_id = None  # WhatsApp session ID
        self._session = None
        self._is_initialized = False
        self._auth_status = "DISCONNECTED"
    
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
            required_params = ["service_url"]
            missing_params = [param for param in required_params if param not in whatsapp_config]
            
            if missing_params:
                raise ConfigurationError(f"Missing required parameters: {', '.join(missing_params)}")
            
            # Store the configuration
            self._config = whatsapp_config
            self._service_url = whatsapp_config["service_url"]
            
            # Set session ID if provided, otherwise use a default
            self._session_id = whatsapp_config.get("session_id", "default_session")
            
            # Set request timeout if provided
            if "request_timeout" in whatsapp_config:
                self._request_timeout = int(whatsapp_config["request_timeout"])
            
            # Ensure service URL doesn't end with a slash
            if self._service_url.endswith("/"):
                self._service_url = self._service_url[:-1]
            
            # Create HTTP session
            self._session = aiohttp.ClientSession()
            self._is_initialized = True
            
            # Check the service status
            await self._update_auth_status()
            
            self.logger.info({
                "action": "INGESTOR_INITIALIZED",
                "message": "WhatsApp ingestor initialized successfully",
                "data": {
                    "service_url": self._service_url,
                    "session_id": self._session_id,
                    "auth_status": self._auth_status
                }
            })
            
        except Exception as e:
            error_message = f"Failed to initialize WhatsApp ingestor: {str(e)}"
            self.logger.error({
                "action": "INITIALIZATION_ERROR",
                "message": error_message,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise ConfigurationError(error_message) from e
    
    async def fetch_full_data(self) -> Dict[str, Any]:
        """
        Fetch all WhatsApp messages and conversations.
        
        This method fetches all available chats and their messages.
        
        Returns:
            Dict[str, Any]: Dictionary containing all WhatsApp data
            
        Raises:
            DataFetchError: If data fetch fails
        """
        if not self._is_initialized:
            raise ConfigurationError("Ingestor not initialized. Call initialize() first.")
        
        try:
            # Ensure session is connected
            await self._ensure_session()
            
            self.logger.info({
                "action": "FETCH_FULL_DATA_START",
                "message": "Fetching all WhatsApp messages"
            })
            
            # Fetch all chats
            chats = await self._fetch_chats()
            
            # Fetch messages for each chat
            all_messages = []
            
            for chat in chats:
                chat_id = chat.get("id")
                if not chat_id:
                    continue
                
                try:
                    messages = await self._fetch_chat_messages(chat_id)
                    # Add chat info to each message
                    for msg in messages:
                        msg["chatId"] = chat_id
                        msg["chatName"] = chat.get("name")
                        msg["isGroup"] = chat.get("isGroup", False)
                    
                    all_messages.extend(messages)
                    
                except Exception as e:
                    self.logger.warning({
                        "action": "FETCH_CHAT_MESSAGES_ERROR",
                        "message": f"Error fetching messages for chat {chat_id}: {str(e)}",
                        "data": {"chat_id": chat_id, "error": str(e)}
                    })
            
            # Sort messages by timestamp
            all_messages.sort(key=lambda x: x.get("timestamp", 0))
            
            self.logger.info({
                "action": "FETCH_FULL_DATA_COMPLETE",
                "message": f"Fetched {len(all_messages)} messages from {len(chats)} chats"
            })
            
            return {
                "messages": all_messages,
                "conversations": chats
            }
            
        except Exception as e:
            self.logger.error({
                "action": "FETCH_FULL_DATA_ERROR",
                "message": f"Error fetching WhatsApp data: {str(e)}",
                "data": {"error": str(e)}
            })
            raise DataFetchError(f"Failed to fetch WhatsApp data: {str(e)}") from e
    
    async def fetch_new_data(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Fetch new WhatsApp messages since a specified time.
        
        Args:
            since: Timestamp to fetch messages from (defaults to last 24 hours)
            
        Returns:
            Dict[str, Any]: Dictionary containing new messages and conversations
            
        Raises:
            DataFetchError: If data fetch fails
        """
        if not self._is_initialized:
            raise ConfigurationError("Ingestor not initialized. Call initialize() first.")
        
        # If no since provided, default to last 24 hours
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(days=1)
        
        try:
            # Ensure session is connected
            print("Ensuring session")
            await self._ensure_session()
            
            since_str = since.isoformat()
            self.logger.info({
                "action": "FETCH_NEW_DATA_START",
                "message": f"Fetching WhatsApp messages since {since_str}",
                "data": {"since": since_str}
            })
            
            # Fetch all chats
            chats = await self._fetch_chats()
            
            # Fetch new messages for each chat
            all_messages = []
            
            for chat in chats:
                chat_id = chat.get("id")
                if not chat_id:
                    continue
                
                try:
                    messages = await self._fetch_chat_messages(chat_id, since)
                    # Add chat info to each message
                    for msg in messages:
                        msg["chatId"] = chat_id
                        msg["chatName"] = chat.get("name")
                        msg["isGroup"] = chat.get("isGroup", False)
                    
                    all_messages.extend(messages)
                    
                except Exception as e:
                    self.logger.warning({
                        "action": "FETCH_CHAT_MESSAGES_ERROR",
                        "message": f"Error fetching messages for chat {chat_id}: {str(e)}",
                        "data": {"chat_id": chat_id, "error": str(e)}
                    })
            
            # Sort messages by timestamp
            all_messages.sort(key=lambda x: x.get("timestamp", 0))
            
            self.logger.info({
                "action": "FETCH_NEW_DATA_COMPLETE",
                "message": f"Fetched {len(all_messages)} new messages from {len(chats)} chats since {since_str}"
            })
            
            return {
                "messages": all_messages,
                "conversations": chats
            }
            
        except Exception as e:
            self.logger.error({
                "action": "FETCH_NEW_DATA_ERROR",
                "message": f"Error fetching new WhatsApp data: {str(e)}",
                "data": {"error": str(e), "since": since.isoformat() if since else None}
            })
            raise DataFetchError(f"Failed to fetch new WhatsApp data: {str(e)}") from e
    
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
            "data": {"start": start_str, "end": end_str, "session_id": self._session_id}
        })
        
        # Ensure we have a WhatsApp session
        await self._ensure_session()
        
        try:
            # Get all chats
            chats = await self._fetch_chats()
            
            # Get messages for each chat and filter by date range
            all_messages = []
            for chat in chats:
                chat_id = chat.get("id")
                messages = await self._fetch_chat_messages(chat_id)
                
                # Filter messages by timestamp
                filtered_messages = [
                    msg for msg in messages 
                    if "timestamp" in msg and 
                    datetime.fromtimestamp(msg["timestamp"] / 1000, tz=timezone.utc) >= start and
                    datetime.fromtimestamp(msg["timestamp"] / 1000, tz=timezone.utc) <= end
                ]
                
                # Add chat metadata to messages
                for message in filtered_messages:
                    message["chat_name"] = chat.get("name", "")
                    message["source"] = "whatsapp"
                
                all_messages.extend(filtered_messages)
                
                # Add small delay to avoid rate limiting
                await asyncio.sleep(0.5)
            
            result = {
                "conversations": chats,
                "messages": all_messages
            }
            
            self.logger.info({
                "action": "FETCH_DATA_IN_RANGE_COMPLETE",
                "message": f"Fetched {len(chats)} chats and {len(all_messages)} messages in date range",
                "data": {
                    "chat_count": len(chats),
                    "message_count": len(all_messages),
                    "start": start_str,
                    "end": end_str,
                    "session_id": self._session_id
                }
            })
            
            return result
            
        except Exception as e:
            error_message = f"Failed to fetch WhatsApp data in range: {str(e)}"
            self.logger.error({
                "action": "FETCH_DATA_IN_RANGE_ERROR",
                "message": error_message,
                "data": {
                    "error": str(e), 
                    "error_type": type(e).__name__, 
                    "start": start_str, 
                    "end": end_str
                }
            })
            raise DataFetchError(error_message) from e
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Checks if the ingestor is properly configured and can connect to the WhatsApp service.

        Returns:
            Dict[str, Any]: A dictionary containing health status information:
                {
                    'healthy': bool,  # Whether the ingestor is functioning properly
                    'message': str,   # Optional message providing more details
                    'details': dict   # Optional additional details about the health check
                }

        Raises:
            IngestorError: If the health check itself encounters an error.
        """
        if not self._service_url:
            return {
                "healthy": False,
                "message": "WhatsApp ingestor not initialized",
                "details": {"error": "Call initialize() first"}
            }
        
        try:
            # Try to get session status
            session_status = await self._get_session_status()
            
            health_status = {
                "healthy": session_status.get("status") == "connected",
                "message": f"WhatsApp {session_status.get('status', 'not connected')}",
                "details": {
                    "service_url": self._service_url,
                    "session_id": self._session_id,
                    "connection_status": session_status.get("status", "unknown")
                }
            }
            
            self.logger.info({
                "action": "HEALTHCHECK_COMPLETE",
                "message": health_status["message"],
                "data": health_status
            })
            
            return health_status
            
        except Exception as e:
            error_message = f"Health check failed: {str(e)}"
            self.logger.error({
                "action": "HEALTHCHECK_ERROR",
                "message": error_message,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            
            return {
                "healthy": False,
                "message": error_message,
                "details": {
                    "service_url": self._service_url,
                    "session_id": self._session_id,
                    "error": str(e)
                }
            }
    
    # Helper methods
    
    async def _ensure_session(self) -> Dict[str, Any]:
        """
        Ensure that a WhatsApp session exists and is ready.
        
        Returns:
            Dict[str, Any]: Session status information
            
        Raises:
            DataFetchError: If session cannot be created or initialized
        """
        try:
            # Directly check the service status
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self._service_url}/api/status", timeout=self._request_timeout) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error({
                            "action": "STATUS_CHECK_ERROR",
                            "message": f"Error checking WhatsApp status: {error_text}",
                            "data": {"status_code": response.status, "error_text": error_text}
                        })
                        raise DataFetchError(f"Error checking WhatsApp status: Status code {response.status}, Response: {error_text}")
                    
                    status_data = await response.json()
                    
            # Check if service is connected
            if status_data.get("status", "").upper() != "CONNECTED":
                self.logger.error({
                    "action": "SERVICE_NOT_CONNECTED",
                    "message": f"WhatsApp service not connected. Status: {status_data.get('status', 'unknown')}",
                    "data": {"status": status_data.get("status", "unknown")}
                })
                
                # If QR code is available, provide instructions
                if status_data.get("hasQrCode", False):
                    print("\n" + "=" * 80)
                    print("SCAN THIS QR CODE WITH WHATSAPP")
                    print("=" * 80)
                    print("Open WhatsApp on your phone and scan the QR code available at:")
                    print(f"{self._service_url}/qrcode")
                    print("=" * 80 + "\n")
                
                raise DataFetchError(f"WhatsApp service not connected. Current status: {status_data.get('status', 'unknown')}")
            
            self.logger.info({
                "action": "SERVICE_CONNECTED",
                "message": "WhatsApp service is connected and ready",
                "data": {"status": status_data.get("status")}
            })
            
            return status_data
            
        except aiohttp.ClientError as e:
            self.logger.error({
                "action": "CONNECTION_ERROR",
                "message": f"Failed to connect to WhatsApp service: {str(e)}",
                "data": {"error": str(e), "service_url": self._service_url}
            })
            raise DataFetchError(f"Failed to connect to WhatsApp service: {str(e)}") from e
    
    async def _get_session_status(self) -> Dict[str, Any]:
        """
        Get the status of the WhatsApp session.
        
        Returns:
            Dict[str, Any]: Session status information
        """
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self._service_url}/sessions/{self._session_id}",
                    timeout=self._request_timeout
                ) as response:
                    if response.status == 404:
                        return {"success": False, "status": "not_found"}
                    
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                self.logger.error({
                    "action": "GET_SESSION_ERROR",
                    "message": f"Error getting session status: {str(e)}",
                    "data": {"error": str(e), "session_id": self._session_id}
                })
                return {"success": False, "status": "error", "error": str(e)}
    
    async def _create_session(self) -> Dict[str, Any]:
        """
        Create a new WhatsApp session.
        
        Returns:
            Dict[str, Any]: Session creation result
        """
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self._service_url}/sessions",
                    json={"sessionId": self._session_id},
                    timeout=self._request_timeout
                ) as response:
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                self.logger.error({
                    "action": "CREATE_SESSION_ERROR",
                    "message": f"Error creating session: {str(e)}",
                    "data": {"error": str(e), "session_id": self._session_id}
                })
                raise DataFetchError(f"Failed to create WhatsApp session: {str(e)}") from e
    
    async def _get_qr_code(self) -> Dict[str, Any]:
        """
        Get the QR code for WhatsApp authentication.
        
        Returns:
            Dict[str, Any]: QR code data
        """
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self._service_url}/sessions/{self._session_id}/qr",
                    timeout=self._request_timeout
                ) as response:
                    if response.status != 200:
                        return None
                    
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                self.logger.error({
                    "action": "GET_QR_ERROR",
                    "message": f"Error getting QR code: {str(e)}",
                    "data": {"error": str(e), "session_id": self._session_id}
                })
                return None
    
    async def _fetch_chats(self) -> List[Dict[str, Any]]:
        """
        Fetch all WhatsApp chats.
        
        Returns:
            List[Dict[str, Any]]: List of chat data
        """
        async with aiohttp.ClientSession() as session:
            try:
                print("Fetching chats")
                async with session.get(
                    f"{self._service_url}/api/chats",
                    timeout=self._request_timeout
                ) as response:
                    print("Chats fetched")
                    if response.status != 200:
                        error_text = await response.text()
                        raise DataFetchError(f"Failed to fetch chats: {error_text}")
                    
                    data = await response.json()
                    return data.get("chats", [])
                    
            except aiohttp.ClientError as e:
                print(e)
                self.logger.error({
                    "action": "FETCH_CHATS_ERROR",
                    "message": f"Error fetching chats: {str(e)}",
                    "data": {"error": str(e), "session_id": self._session_id}
                })
                raise DataFetchError(f"Failed to fetch WhatsApp chats: {str(e)}") from e
    
    async def _fetch_chat_messages(self, chat_id: str, since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Fetch messages from a specific chat.
        
        Args:
            chat_id: WhatsApp chat ID
            since: Optional timestamp to filter messages from
            
        Returns:
            List[Dict[str, Any]]: List of message data
        """
        async with aiohttp.ClientSession() as session:
            try:
                params = {"chatId": chat_id}
                # Add since parameter if provided
                if since:
                    params["since"] = int(since.timestamp() * 1000)  # Convert to milliseconds
                
                async with session.get(
                    f"{self._service_url}/api/messages",
                    params=params,
                    timeout=self._request_timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise DataFetchError(f"Failed to fetch messages for chat {chat_id}: {error_text}")
                    
                    data = await response.json()
                    return data.get("messages", [])
                    
            except aiohttp.ClientError as e:
                self.logger.error({
                    "action": "FETCH_MESSAGES_ERROR",
                    "message": f"Error fetching messages for chat {chat_id}: {str(e)}",
                    "data": {"error": str(e), "session_id": self._session_id, "chat_id": chat_id}
                })
                raise DataFetchError(f"Failed to fetch WhatsApp messages: {str(e)}") from e

    async def _update_auth_status(self) -> str:
        """
        Update the authentication status by checking with the WhatsApp service.
        
        Returns:
            str: Current authentication status
            
        Raises:
            DataFetchError: If status check fails
        """
        if not self._is_initialized:
            raise ConfigurationError("Ingestor not initialized. Call initialize() first.")
        
        try:
            self.logger.info({
                "action": "CHECKING_STATUS",
                "message": f"Checking WhatsApp status at {self._service_url}/api/status",
                "data": {"service_url": self._service_url}
            })
            
            async with self._session.get(f"{self._service_url}/api/status", timeout=30) as response:
                if response.status != 200:
                    error_text = await response.text()
                    self.logger.error({
                        "action": "STATUS_CHECK_ERROR",
                        "message": f"Error checking WhatsApp status: {error_text}",
                        "data": {"status_code": response.status, "error_text": error_text}
                    })
                    raise DataFetchError(f"Error checking WhatsApp status: Status code {response.status}, Response: {error_text}")
                
                data = await response.json()
                self.logger.info({
                    "action": "STATUS_CHECK_SUCCESS",
                    "message": f"WhatsApp status check successful: {data}",
                    "data": data
                })
                self._auth_status = data.get("status", "UNKNOWN").upper()
                return self._auth_status
                
        except aiohttp.ClientError as e:
            self.logger.error({
                "action": "CONNECTION_ERROR",
                "message": f"Failed to connect to WhatsApp service: {str(e)}",
                "data": {"error": str(e), "service_url": self._service_url}
            })
            raise DataFetchError(f"Failed to connect to WhatsApp service: {str(e)}") from e

    async def is_authenticated(self) -> bool:
        """
        Check if the WhatsApp session is authenticated.
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        await self._update_auth_status()
        return self._auth_status.upper() == "CONNECTED"

    async def get_authentication_url(self) -> str:
        """
        Get the URL for the authentication page with QR code.
        
        Returns:
            str: URL to the authentication page
        """
        return f"{self._service_url}/"

    async def wait_for_authentication(self, timeout_seconds: int = 300) -> bool:
        """
        Wait for the user to authenticate by scanning the QR code.
        
        Args:
            timeout_seconds (int): Maximum time to wait in seconds
            
        Returns:
            bool: True if authentication succeeded, False if timed out
            
        Raises:
            AuthenticationError: If authentication fails
        """
        if not self._is_initialized:
            raise ConfigurationError("Ingestor not initialized. Call initialize() first.")
        
        start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info({
                "action": "WAITING_FOR_AUTHENTICATION",
                "message": f"Waiting up to {timeout_seconds}s for WhatsApp authentication",
                "data": {"timeout_seconds": timeout_seconds}
            })
            
            while (datetime.now(timezone.utc) - start_time).total_seconds() < timeout_seconds:
                await self._update_auth_status()
                
                if self._auth_status == "CONNECTED":
                    self.logger.info({
                        "action": "AUTHENTICATION_SUCCESS",
                        "message": "WhatsApp authentication successful"
                    })
                    return True
                
                # If authentication failed, raise an error
                if self._auth_status == "AUTH_FAILURE":
                    raise AuthenticationError("WhatsApp authentication failed")
                
                # Wait before checking again
                await asyncio.sleep(3)
            
            # Timed out
            self.logger.warning({
                "action": "AUTHENTICATION_TIMEOUT",
                "message": "Timed out waiting for WhatsApp authentication",
                "data": {"timeout_seconds": timeout_seconds}
            })
            return False
            
        except AuthenticationError as e:
            self.logger.error({
                "action": "AUTHENTICATION_ERROR",
                "message": f"WhatsApp authentication error: {str(e)}",
                "data": {"error": str(e)}
            })
            raise
        except Exception as e:
            error_message = f"Error waiting for authentication: {str(e)}"
            self.logger.error({
                "action": "AUTHENTICATION_WAIT_ERROR",
                "message": error_message,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise AuthenticationError(error_message) from e

    async def close(self) -> None:
        """
        Close the ingestor and release resources.
        
        Returns:
            None
        """
        if self._session:
            await self._session.close()
            self._session = None
        
        self._is_initialized = False
        
        self.logger.info({
            "action": "INGESTOR_CLOSED",
            "message": "WhatsApp ingestor closed"
        })

    async def healthcheck(self) -> Dict[str, Any]:
        """
        Perform a health check of the ingestor.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        health_info = {
            "status": "healthy",
            "initialized": self._is_initialized,
            "auth_status": self._auth_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if not self._is_initialized:
            health_info["status"] = "not_initialized"
            return health_info
        
        try:
            # Check if we can reach the WhatsApp service
            async with self._session.get(f"{self._service_url}/api/status", timeout=5) as response:
                if response.status != 200:
                    health_info["status"] = "degraded"
                    health_info["service_error"] = f"Service returned status {response.status}"
                else:
                    data = await response.json()
                    health_info["service_status"] = data.get("status", "UNKNOWN")
                    health_info["service_initialized"] = data.get("initialized", False)
                    
                    # Update auth status
                    self._auth_status = data.get("status", "UNKNOWN").upper()
                    health_info["auth_status"] = self._auth_status
                    
        except Exception as e:
            health_info["status"] = "unhealthy"
            health_info["error"] = str(e)
            health_info["error_type"] = type(e).__name__
        
        return health_info 