"""
WhatsApp ingestor implementation using WhatsApp Web JS via a Node.js service.
"""

import asyncio
import os
import time
import json
import sys
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
        
        # Add user info properties
        self._user_info = None
        self._user_info_file = None
    
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
            self._user_info_file = whatsapp_config.get("user_info_file", os.path.join("db", "whatsapp", "user_info.json"))
            
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
            
            # Load cached user info
            await self._load_user_info()
            
            # If authenticated, try to get user info
            if self._auth_status == "CONNECTED":
                try:
                    await self.get_user_info()
                except Exception as e:
                    self.logger.warning({
                        "action": "USER_INFO_RETRIEVAL_WARNING",
                        "message": f"Authenticated but couldn't get user info during initialization: {str(e)}",
                        "data": {"error": str(e)}
                    })
            
            self.logger.info({
                "action": "INGESTOR_INITIALIZED",
                "message": "WhatsApp ingestor initialized successfully",
                "data": {
                    "service_url": self._service_url,
                    "session_id": self._session_id,
                    "auth_status": self._auth_status,
                    "user_id": self.get_current_user_id()
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
            Dict[str, Any]: Dictionary containing all WhatsApp data organized by chat_id
                {
                    "conversations": {
                        "chat_id_1": [messages],
                        "chat_id_2": [messages],
                        ...
                    }
                }
                
        Raises:
            DataFetchError: If data fetch fails
        """
        return await self._fetch_chat_data(
            log_prefix="FETCH_FULL_DATA"
        )
    
    async def fetch_new_data(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Fetch new WhatsApp messages since a specified time.
        
        Args:
            since: Timestamp to fetch messages from (defaults to last 24 hours)
            
        Returns:
            Dict[str, Any]: Dictionary containing new messages organized by chat_id
                {
                    "conversations": {
                        "chat_id_1": [messages],
                        "chat_id_2": [messages],
                        ...
                    }
                }
                
        Raises:
            DataFetchError: If data fetch fails
        """
        # If no since provided, default to last 24 hours
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(days=1)
        
        since_str = since.isoformat()
        
        async def filter_since(chat_id):
            return await self._fetch_chat_messages(chat_id, since)
        
        result = await self._fetch_chat_data(
            message_filter=filter_since,
            log_prefix="FETCH_NEW_DATA",
            additional_log_data={"since": since_str}
        )
        
        return result
    
    async def fetch_data_in_range(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """
        Fetch message data within a specific date range.
        
        Args:
            start: Start timestamp for data range.
            end: End timestamp for data range.
            
        Returns:
            Dict[str, Any]: Dictionary containing conversations and messages in range.
                {
                    "conversations": {
                        "chat_id_1": [messages],
                        "chat_id_2": [messages],
                        ...
                    }
                }
        """
        # Ensure timestamps are timezone aware
        start = ensure_tz_aware(start)
        end = ensure_tz_aware(end)
        
        # Convert to ISO format for logging
        start_str = start.isoformat()
        end_str = end.isoformat()
        
        async def filter_by_range(chat_id):
            messages = await self._fetch_chat_messages(chat_id)
            return [
                msg for msg in messages 
                if self._is_message_in_timeframe(msg, start, end)
            ]
        
        return await self._fetch_chat_data(
            message_filter=filter_by_range,
            log_prefix="FETCH_DATA_IN_RANGE",
            additional_log_data={
                "start": start_str, 
                "end": end_str, 
                "session_id": self._session_id
            }
        )
    
    async def _fetch_chat_data(
        self,
        message_filter=None,
        log_prefix="FETCH_DATA",
        additional_log_data=None
    ) -> Dict[str, Any]:
        """
        Fetch chat data with optional filtering.
        
        Args:
            message_filter: Optional filter function for messages
            log_prefix: Prefix for logging actions
            additional_log_data: Additional data to include in logs
            
        Returns:
            Dict[str, Any]: Dictionary containing conversations and message counts
            
        Raises:
            DataFetchError: If data fetch fails
        """
        if not self._is_initialized:
            raise ConfigurationError("Ingestor not initialized. Call initialize() first.")
        
        # Ensure authenticated
        await self._ensure_session()
        
        # Log start of fetching
        log_data = {"session_id": self._session_id}
        if additional_log_data:
            log_data.update(additional_log_data)
            
        self.logger.info({
            "action": f"{log_prefix}_START",
            "message": "Starting WhatsApp data fetch",
            "data": log_data
        })
        
        try:
            # Fetch chats
            chats = await self._fetch_chats()
            
            # Prepare result format
            result = {
                "conversations": {}
            }
            
            total_messages = 0
            total_reply_messages = 0
            
            # Fetch messages for each chat
            for chat in chats:
                chat_id = chat.get("id")
                if not chat_id:
                    continue
                
                # Apply filter function if provided, otherwise fetch all messages
                if message_filter:
                    messages = await message_filter(chat_id)
                else:
                    messages = await self._fetch_chat_messages(chat_id)
                
                # Calculate reply statistics for this chat
                reply_count = sum(1 for msg in messages if self._is_reply(msg))
                total_reply_messages += reply_count
                
                # Add chat name to each message for better context
                for message in messages:
                    message["chat_name"] = chat.get("name", "Unknown Chat")
                    # Add reply flag for easier identification
                    message["is_reply"] = self._is_reply(message)
                
                # Add messages to result
                result["conversations"][chat_id] = messages
                total_messages += len(messages)
                
                # Log progress
                self.logger.info({
                    "action": f"{log_prefix}_CHAT_COMPLETE",
                    "message": f"Fetched {len(messages)} messages from chat {chat.get('name', 'Unknown')}",
                    "data": {
                        "chat_id": chat_id,
                        "message_count": len(messages),
                        "reply_count": reply_count,
                        "reply_percentage": f"{(reply_count / len(messages) * 100):.1f}%" if messages else "0%"
                    }
                })
            
            # Add metadata
            result["metadata"] = {
                "source": "whatsapp",
                "total_chats": len(chats),
                "total_messages": total_messages,
                "total_reply_messages": total_reply_messages,
                "reply_percentage": f"{(total_reply_messages / total_messages * 100):.1f}%" if total_messages else "0%",
                "fetch_time": datetime.now(timezone.utc).isoformat()
            }
            
            # Log completion
            self.logger.info({
                "action": f"{log_prefix}_COMPLETE",
                "message": f"Completed WhatsApp data fetch: {len(chats)} chats, {total_messages} messages",
                "data": {
                    "chat_count": len(chats),
                    "message_count": total_messages,
                    "reply_count": total_reply_messages
                }
            })
            
            return result
            
        except Exception as e:
            self.logger.error({
                "action": f"{log_prefix}_ERROR",
                "message": f"Error fetching WhatsApp data: {str(e)}",
                "data": {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "session_id": self._session_id
                }
            })
            raise DataFetchError(f"Failed to fetch WhatsApp data: {str(e)}") from e
    
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
        Fetch all messages from a specific chat.
        
        Args:
            chat_id: The ID of the chat to fetch messages from
            since: Optional timestamp to filter messages from
            
        Returns:
            List[Dict[str, Any]]: List of message objects
            
        Raises:
            DataFetchError: If message fetch fails
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
                    messages = data.get("messages", [])
                    
                    # Transform messages to ensure they have all required fields
                    for message in messages:
                        # Map author or from to sender_id for consistent identification
                        if "author" in message:
                            message["sender_id"] = message["author"]
                        elif "from" in message:
                            message["sender_id"] = message["from"]
                        
                        # Process reply/quoted message data if available
                        if message.get("hasQuotedMsg", False):
                            self.logger.debug({
                                "action": "QUOTED_MESSAGE_DETECTED",
                                "message": f"Found quoted message in {message.get('id', 'unknown')}",
                                "data": {
                                    "message_id": message.get("id"),
                                    "has_quoted_msg": message.get("hasQuotedMsg"),
                                    "quoted_msg_id": message.get("quotedMsgId"),
                                    "quoted_participant": message.get("quotedParticipant")
                                }
                            })
                            
                            # Standardize reply fields for consistency with Telegram
                            message["reply_to_id"] = message.get("quotedMsgId")
                            
                            # Include quoted message data if available
                            if "quotedMsg" in message:
                                quoted_msg = message.get("quotedMsg", {})
                                message["reply_data"] = {
                                    "text": quoted_msg.get("body", ""),
                                    "sender_id": quoted_msg.get("sender", ""),
                                    "timestamp": quoted_msg.get("timestamp")
                                }
                    
                    self.logger.debug({
                        "action": "MESSAGES_TRANSFORMED",
                        "message": f"Added sender_id and reply data to {len(messages)} messages",
                        "data": {"chat_id": chat_id, "message_count": len(messages)}
                    })
                    
                    # Log the structure of the first message for debugging if available
                    if messages and len(messages) > 0:
                        # Get the first message keys for debugging
                        first_msg = messages[0]
                        
                        # Check for quoted message data
                        reply_fields = {
                            "hasQuotedMsg": first_msg.get("hasQuotedMsg", False),
                            "quotedMsgId": "quotedMsgId" in first_msg,
                            "reply_to_id": "reply_to_id" in first_msg,
                            "reply_data": "reply_data" in first_msg
                        }
                        
                        self.logger.debug({
                            "action": "MESSAGE_STRUCTURE",
                            "message": "Sample message structure after transformation",
                            "data": {
                                "has_sender_id": "sender_id" in first_msg,
                                "has_author": "author" in first_msg,
                                "has_from": "from" in first_msg,
                                "reply_fields": reply_fields,
                                "keys": list(first_msg.keys())
                            }
                        })
                    
                    return messages
                    
            except aiohttp.ClientError as e:
                self.logger.error({
                    "action": "FETCH_MESSAGES_ERROR",
                    "message": f"Error fetching messages for chat {chat_id}: {str(e)}",
                    "data": {"error": str(e), "session_id": self._session_id, "chat_id": chat_id}
                })
                raise DataFetchError(f"Failed to fetch WhatsApp messages: {str(e)}") from e

    def _is_message_in_timeframe(self, message: Dict[str, Any], start: datetime, end: datetime) -> bool:
        """
        Check if a message falls within a specified timeframe.
        
        Args:
            message: The message to check
            start: Start timestamp
            end: End timestamp
            
        Returns:
            bool: True if the message is within the timeframe, False otherwise
        """
        if "timestamp" not in message:
            return False
        
        # Convert WhatsApp timestamp (milliseconds) to datetime
        timestamp = message["timestamp"]
        if timestamp > 1600000000000:  # Likely in milliseconds if very large
            timestamp = timestamp / 1000
        
        message_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        
        # Check if message is within timeframe
        return start <= message_time <= end

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
                    
                    # Get user info after successful authentication
                    try:
                        user_info = await self.get_user_info()
                        self.logger.error({
                            "action": "USER_INFO_AFTER_AUTH",
                            "message": "User information retrieved after authentication",
                            "data": {"user_id": user_info.get("id")}
                        })
                    except Exception as e:
                        self.logger.warning({
                            "action": "USER_INFO_AFTER_AUTH_ERROR",
                            "message": f"Error getting user info after authentication: {str(e)}",
                            "data": {"error": str(e)}
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

    # User information methods
    
    async def get_user_info(self) -> Dict[str, Any]:
        """
        Get information about the current authenticated WhatsApp user.
        
        Returns:
            Dict[str, Any]: Dictionary containing user information such as user_id, name, etc.
            
        Raises:
            DataFetchError: If retrieval fails
            AuthenticationError: If not authenticated
        """
        if not self._is_initialized:
            raise ConfigurationError("Ingestor not initialized. Call initialize() first.")
        
        if not await self.is_authenticated():
            raise AuthenticationError("Not authenticated with WhatsApp")
        
        try:
            # Return cached info if available and connected
            if self._user_info and self._auth_status == "CONNECTED":
                return self._user_info
            
            # Fetch from service
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self._service_url}/api/user-info",
                    timeout=self._request_timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise DataFetchError(f"Failed to fetch user info: {error_text}")
                    
                    data = await response.json()
                    user_info = data.get("user", {})
                    
                    # Cache the info
                    if user_info and "id" in user_info:
                        self._user_info = user_info
                        await self._save_user_info()
                        
                        self.logger.info({
                            "action": "USER_INFO_RETRIEVED",
                            "message": "WhatsApp user info retrieved and cached",
                            "data": {"user_id": user_info["id"]}
                        })

                    # print("--------------------------------")
                    # print("user_info")
                    # print(user_info)
                    # print("--------------------------------")

                    return user_info
        
        except aiohttp.ClientError as e:
            self.logger.error({
                "action": "GET_USER_INFO_ERROR",
                "message": f"Error fetching user info: {str(e)}",
                "data": {"error": str(e)}
            })
            raise DataFetchError(f"Failed to fetch WhatsApp user info: {str(e)}") from e
    
    async def _save_user_info(self) -> None:
        """Save user info to persistent storage."""
        if not self._user_info:
            return
            
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self._user_info_file), exist_ok=True)
            
            # Save to file
            with open(self._user_info_file, "w") as f:
                json.dump(self._user_info, f, indent=2)
                
            self.logger.debug({
                "action": "USER_INFO_SAVED",
                "message": "WhatsApp user info saved to disk",
                "data": {"file": self._user_info_file}
            })
        except Exception as e:
            self.logger.warning({
                "action": "USER_INFO_SAVE_ERROR",
                "message": f"Failed to save user info: {str(e)}",
                "data": {"error": str(e)}
            })
    
    async def _load_user_info(self) -> None:
        """Load user info from persistent storage."""
        try:
            if os.path.exists(self._user_info_file):
                with open(self._user_info_file, "r") as f:
                    self._user_info = json.load(f)
                    
                self.logger.debug({
                    "action": "USER_INFO_LOADED",
                    "message": "WhatsApp user info loaded from disk",
                    "data": {"user_id": self._user_info.get("id")}
                })
        except Exception as e:
            self.logger.warning({
                "action": "USER_INFO_LOAD_ERROR",
                "message": f"Failed to load user info: {str(e)}",
                "data": {"error": str(e)}
            })
    
    def get_current_user_id(self) -> Optional[str]:
        """
        Get the current WhatsApp user ID if available.
        
        Returns:
            Optional[str]: The user ID or None if not available
        """
        if self._user_info and "id" in self._user_info:
            return self._user_info["id"]
        return None

    def _is_reply(self, message: Dict[str, Any]) -> bool:
        """
        Check if a message is a reply to another message.
        
        Args:
            message: Message to check
            
        Returns:
            bool: True if it's a reply, False otherwise
        """
        return bool(
            message.get("hasQuotedMsg", False) or
            message.get("quotedMsgId") or
            message.get("reply_to_id")
        )

    def _get_reply_info(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract standardized reply information from a message.
        
        Args:
            message: Message to extract reply info from
            
        Returns:
            Dict[str, Any]: Reply information or empty dict if not a reply
        """
        if not self._is_reply(message):
            return {}
        
        reply_info = {
            "is_reply": True,
            "reply_to_id": message.get("reply_to_id") or message.get("quotedMsgId")
        }
        
        # Add quoted message data if available
        if "reply_data" in message:
            reply_info["reply_data"] = message["reply_data"]
        elif "quotedMsg" in message:
            quoted_msg = message.get("quotedMsg", {})
            reply_info["reply_data"] = {
                "text": quoted_msg.get("body", ""),
                "sender_id": quoted_msg.get("sender", ""),
                "timestamp": quoted_msg.get("timestamp")
            }
        
        # Add quoted participant if available
        if "quotedParticipant" in message:
            reply_info["quoted_participant"] = message["quotedParticipant"]
        
        return reply_info 