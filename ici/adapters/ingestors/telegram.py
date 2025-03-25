"""
Telegram ingestor implementation using MTProto via Telethon.
"""

import asyncio
import os
import time
import sys
import yaml
import threading
import json
import traceback
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Iterator, List, Optional, cast, Generator, Tuple

from telethon import TelegramClient
from telethon.tl.types import User, Chat, Dialog, Message, InputPeerUser
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from telethon.sessions import StringSession

from ici.core.interfaces.ingestor import Ingestor
from ici.adapters.loggers import StructuredLogger
from ici.utils.config import get_component_config, load_config
from ici.core.exceptions import ConfigurationError
from ici.utils.datetime_utils import from_isoformat, ensure_tz_aware


class TelegramIngestor(Ingestor):
    """
    Ingests messages from Telegram using MTProto.
    Fetches only direct message chats (not groups or channels).
    
    Required config parameters:
    - api_id: Telegram API ID from https://my.telegram.org
    - api_hash: Telegram API hash from https://my.telegram.org
    - phone_number: Your phone number with country code
    - session_string: Telegram session string for authentication
      (or session_file: Path to save session authentication)
    """
    
    def __init__(self, logger_name: str = "telegram_ingestor"):
        """
        Initialize the Telegram ingestor.
        
        Args:
            logger_name: Name for the logger instance.
        """
        self.logger = StructuredLogger(name=logger_name)
        self._config = None
        self._request_delay = 0.5  # Default delay between requests in seconds
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        self._session_string = None  # Cache the session string for reuse
    
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
                telegram_config = get_component_config("ingestors.telegram", self._config_path)
                self.logger.debug({
                    "action": "CONFIG_LOADED",
                    "message": "Configuration loaded successfully",
                    "data": {"config": full_config}
                })
            except Exception as e:
                raise ConfigurationError(f"Failed to load configuration: {str(e)}") from e
            
            # Validate configuration
            required_params = ["api_id", "api_hash", "phone_number"]
            missing_params = [param for param in required_params if param not in telegram_config]
            
            if missing_params:
                raise ConfigurationError(f"Missing required parameters: {', '.join(missing_params)}")
            
            # Store the entire config for later use
            self._config = telegram_config
            
            # Set request delay
            if "request_delay" in telegram_config:
                self._request_delay = float(telegram_config["request_delay"])
            
            # Cache session string if available
            if "session_string" in telegram_config:
                self._session_string = telegram_config["session_string"]
            
            self.logger.info({
                "action": "INGESTOR_INITIALIZED",
                "message": "Telegram ingestor initialized successfully"
            })
            
        except Exception as e:
            error_message = f"Failed to initialize Telegram ingestor: {str(e)}"
            self.logger.error({
                "action": "INITIALIZATION_ERROR",
                "message": error_message,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise ConfigurationError(error_message) from e
    
    async def fetch_full_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch all available direct message conversations and their messages.
        
        Returns:
            Dict[str, List[Dict[str, Any]]]: Dictionary containing conversations and messages.
        """
        self.logger.info({
            "action": "FETCH_FULL_DATA_START",
            "message": "Fetching all available conversations and messages"
        })
        
        result = await self._fetch_all_conversations()
        
        self.logger.info({
            "action": "FETCH_FULL_DATA_COMPLETE",
            "message": f"Fetched {len(result.get('conversations', []))} conversations"
        })
        
        return result
    
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
        
        # Convert to ISO format for Telegram API
        since_str = since.isoformat()
        now_str = datetime.now(timezone.utc).isoformat()
        
        self.logger.info({
            "action": "FETCH_NEW_DATA_START",
            "message": f"Fetching new data since {since_str}",
            "data": {"since": since_str}
        })
        
        result = await self._fetch_conversations_in_range(since_str, now_str)
        
        self.logger.info({
            "action": "FETCH_NEW_DATA_COMPLETE",
            "message": f"Fetched data for {len(result.get('conversations', []))} conversations since {since_str}",
            "data": {"since": since_str}
        })
        
        return result
    
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
        
        # Convert to ISO format for Telegram API
        start_str = start.isoformat()
        end_str = end.isoformat()
        
        self.logger.info({
            "action": "FETCH_DATA_IN_RANGE_START",
            "message": f"Fetching data from {start_str} to {end_str}",
            "data": {"start": start_str, "end": end_str}
        })
        
        result = await self._fetch_conversations_in_range(start_str, end_str)
        
        self.logger.info({
            "action": "FETCH_DATA_IN_RANGE_COMPLETE",
            "message": f"Fetched data for {len(result.get('conversations', []))} conversations in date range",
            "data": {"start": start_str, "end": end_str}
        })
        
        return result
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Check if the ingestor is properly configured and can connect to Telegram.
        
        Returns:
            Dict[str, Any]: Dictionary containing health status information.
        """
        try:
            self.logger.info({
                "action": "HEALTHCHECK_START",
                "message": "Performing Telegram ingestor health check"
            })
            
            user_result = await self._test_connection()
            
            health_status = {
                "healthy": True,
                "message": f"Connected to Telegram as {user_result.get('first_name', '')} {user_result.get('last_name', '')}",
                "details": {
                    "user_id": user_result.get("id"),
                    "username": user_result.get("username"),
                    "api_id": self._config.get("api_id") if self._config else None
                }
            }
            
            self.logger.info({
                "action": "HEALTHCHECK_SUCCESS",
                "message": "Telegram ingestor health check passed",
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
                    "error_type": type(e).__name__
                }
            }
            
            self.logger.error({
                "action": "HEALTHCHECK_FAILED",
                "message": error_message,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            
            return health_status
    
    async def _create_client(self) -> TelegramClient:
        """
        Create a new Telegram client using the stored configuration.
        
        Returns:
            TelegramClient: A newly created and connected Telegram client
            
        Raises:
            Exception: If client creation or connection fails
        """
        if not self._config:
            raise ConfigurationError("Ingestor not initialized, call initialize() first")
        
        # Extract configuration
        api_id = self._config.get("api_id")
        api_hash = self._config.get("api_hash")
        phone_number = self._config.get("phone_number")
        session_string = self._config.get("session_string")
        
        # Create session
        if self._session_string and self._session_string != "your_telegram_session_string" and self._session_string != "":
            session = StringSession(self._session_string)
            self.logger.debug({
                "action": "SESSION_STRING_USED",
                "message": "Using cached session string"
            })
        elif "session_string" in self._config and session_string != "your_telegram_session_string" and session_string != "":
            session = StringSession(self._config["session_string"])
            # Cache it for future use
            self._session_string = self._config["session_string"]
        else:
            # Use session file as fallback
            session_file = self._config.get("session_file", "telegram_session")
            # Create directory if needed
            if session_file and "/" in session_file:
                session_dir = os.path.dirname(session_file)
                os.makedirs(session_dir, exist_ok=True)
            session = StringSession()  # Create empty string session for login
        
        # Create a new client with the current thread's event loop
        client = TelegramClient(session, api_id, api_hash)
        
        # Connect the client
        try:
            self.logger.debug({
                "action": "CLIENT_CONNECTING",
                "message": "Connecting to Telegram"
            })
            
            await client.start(phone_number)
            
            # Get user info for logging
            me = await client.get_me()
            self.logger.debug({
                "action": "CLIENT_CONNECTED",
                "message": "Connected to Telegram",
                "data": {
                    "user_id": me.id,
                    "username": me.username,
                    "first_name": me.first_name
                }
            })
            
            # Extract the session string after successful login
            if isinstance(session, StringSession) and (self._session_string == "your_telegram_session_string" or self._session_string == ""):
                # Get the session as string
                current_session_string = client.session.save()
                self.logger.debug({
                    "action": "SESSION_STRING_EXTRACTED",
                    "message": "Session string extracted after successful login"
                })
                
                # Cache it for future use
                self._session_string = current_session_string
                
                # Display the session string to the user
                print("\n" + "=" * 80)
                print("IMPORTANT: TELEGRAM SESSION STRING GENERATED")
                print("=" * 80)
                print(f"Add this to your .env file:")
                print(f"TELEGRAM_SESSION_STRING={self._session_string}")
                print("=" * 80 + "\n")
                
                self.logger.info({
                    "action": "SESSION_STRING_DISPLAYED",
                    "message": "Displayed session string to user for saving in .env file"
                })
                
                # Update the in-memory config
                if self._config and self._session_string:
                    self._config["session_string"] = self._session_string
            
            return client
            
        except Exception as e:
            # Make sure to clean up if there was an error
            try:
                await client.disconnect()
            except:
                pass
                
            self.logger.error({
                "action": "CLIENT_CONNECTION_ERROR",
                "message": f"Failed to connect client: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise
    
    async def _with_client(self, operation):
        """
        Execute an operation with a fresh client connection.
        
        Args:
            operation: Async function that takes a client as parameter
            
        Returns:
            Any: Result of the operation
            
        Raises:
            Exception: If client connection or operation fails
        """
        client = None
        try:
            # Create and connect a fresh client
            client = await self._create_client()
            
            # Execute the operation with the client
            return await operation(client)
            
        finally:
            # Always disconnect the client
            if client:
                try:
                    await client.disconnect()
                    self.logger.debug({
                        "action": "CLIENT_DISCONNECTED",
                        "message": "Disconnected Telegram client"
                    })
                except Exception as e:
                    self.logger.warning({
                        "action": "CLIENT_DISCONNECT_ERROR",
                        "message": f"Error disconnecting client: {str(e)}",
                        "data": {"error": str(e)}
                    })
    
    async def _test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Telegram by creating a client and getting user info.
        
        Returns:
            Dict[str, Any]: User information if successful
        """
        return await self._with_client(self._get_me)
    
    async def _get_me(self, client: TelegramClient) -> Dict[str, Any]:
        """
        Get current user information.
        
        Args:
            client: Connected TelegramClient
            
        Returns:
            Dict[str, Any]: User information
        """
        me = await client.get_me()
        return {
            "user_id": me.id,
            "username": me.username,
            "first_name": me.first_name
        }
    
    async def _get_conversations(self, client: TelegramClient, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get a list of direct message conversations.
        
        Args:
            client: Connected TelegramClient
            limit: Maximum number of conversations to fetch
            
        Returns:
            List[Dict[str, Any]]: List of conversation metadata.
        """
        try:
            conversations = []
            offset_date = None
            offset_id = 0
            offset_peer = InputPeerUser(0, 0)
            
            # Get dialogs (chats/conversations)
            dialogs = await client.get_dialogs(limit=limit)
            
            for dialog in dialogs:
                if dialog.is_user:  # Only include direct message chats
                    entity = dialog.entity
                    
                    # Extract the most recent message if available
                    last_message = None
                    if dialog.message:
                        msg = dialog.message
                        last_message = {
                            "id": msg.id,
                            "date": msg.date.isoformat(),
                            "text": msg.text if hasattr(msg, "text") else "",
                        }
                    
                    # Create conversation metadata
                    conversation = {
                        "id": entity.id,
                        "name": entity.first_name or "",
                        "username": entity.username or "",
                        "last_message": last_message,
                        "last_updated": dialog.date.isoformat() if dialog.date else None,
                        "total_messages": dialog.unread_count  # This is just unread count, not total
                    }
                    
                    conversations.append(conversation)
            
            self.logger.debug({
                "action": "CONVERSATIONS_FETCHED",
                "message": f"Fetched {len(conversations)} direct message conversations",
                "data": {"count": len(conversations)}
            })
            
            return conversations
            
        except FloodWaitError as e:
            # Handle rate limiting
            wait_time = e.seconds
            self.logger.warning({
                "action": "RATE_LIMITED",
                "message": f"Rate limited by Telegram, waiting {wait_time} seconds",
                "data": {"wait_time": wait_time}
            })
            await asyncio.sleep(wait_time)
            # Return empty list, caller should retry
            return []
            
        except Exception as e:
            self.logger.error({
                "action": "TELEGRAM_GET_CONVERSATIONS_ERROR",
                "message": "Error retrieving conversations",
                "exception": {
                    "type": type(e).__name__,
                    "message": str(e),
                    "traceback": traceback.format_exc().splitlines()
                }
            })
            raise
    
    async def _get_messages(self, client: TelegramClient, conversation_id: int, 
                        limit: int = 100, min_id: int = None, 
                        max_id: int = None) -> List[Dict[str, Any]]:
        """
        Get messages from a specific conversation.
        
        Args:
            client: Connected TelegramClient
            conversation_id: ID of the conversation to fetch messages from.
            limit: Maximum number of messages to fetch.
            min_id: Minimum message ID (for pagination).
            max_id: Maximum message ID (for pagination).
            
        Returns:
            List[Dict[str, Any]]: List of message data.
        """
        try:
            messages = []
            
            # Get the entity for this conversation
            entity = await client.get_entity(conversation_id)
            self.logger.info({
                "action": "TELEGRAM_GET_MESSAGES_ENTITY",
                "message": f"Fetched entity for conversation {conversation_id}",
                "data": {
                    # "entity": entity,
                    "limit": limit,
                    "min_id": min_id,
                    "max_id": max_id
                }
            })
            
            # Get messages from this entity
            telegram_messages = await client.get_messages(
                entity,
                limit=limit
            )

            # self.logger.info({
            #     "action": "TELEGRAM_GET_MESSAGES_ENTITY",
            #     "message": f"Fetched entity for conversation {conversation_id}",
            #     "data": {"telegram_messages": telegram_messages}
            # })
            
            # Process each message
            for msg in telegram_messages:
                # Skip non-text messages for now
                if not hasattr(msg, 'text') or not msg.text:
                    continue
                
                # Create message object
                message = {
                    "id": msg.id,
                    "conversation_id": conversation_id,
                    "date": msg.date.isoformat(),
                    "text": msg.text,
                    "from_user": True if msg.out else False,  # True if sent by the user
                    "sender_id": msg.from_id.user_id if msg.from_id else None,
                    "sender_name": None,  # Will be filled in later if needed
                    "reply_to_msg_id": msg.reply_to.reply_to_msg_id if msg.reply_to else None
                }

                self.logger.info({
                    "action": "TELEGRAM_GET_MESSAGES_MESSAGE",
                    "message": f"Fetched message {message['id']} from conversation {conversation_id}",
                    "data": {"message": message}
                })
                
                messages.append(message)
            
            self.logger.debug({
                "action": "MESSAGES_FETCHED",
                "message": f"Fetched {len(messages)} messages from conversation {conversation_id}",
                "data": {
                    "conversation_id": conversation_id,
                    "message_count": len(messages)
                }
            })
            
            # Add delay to avoid rate limiting
            await asyncio.sleep(self._request_delay)

            return messages
            
        except FloodWaitError as e:
            # Handle rate limiting
            wait_time = e.seconds
            self.logger.warning({
                "action": "RATE_LIMITED",
                "message": f"Rate limited by Telegram, waiting {wait_time} seconds",
                "data": {"wait_time": wait_time}
            })
            await asyncio.sleep(wait_time)
            # Return empty list, caller should retry
            return []
            
        except Exception as e:
            self.logger.error({
                "action": "TELEGRAM_GET_MESSAGES_ERROR",
                "message": f"Error retrieving messages from conversation {conversation_id}",
                "data": {
                    "conversation_id": conversation_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            })
            # Return empty list on error
            return []
    
    async def _get_messages_in_date_range(self, client: TelegramClient, conversation_id: int, 
                                     start_date: str, end_date: str, 
                                     limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get messages from a conversation within a specified date range.
        
        Args:
            client: Connected TelegramClient
            conversation_id: ID of the conversation.
            start_date: Start date in ISO format.
            end_date: End date in ISO format.
            limit: Maximum number of messages to fetch.
            
        Returns:
            List[Dict[str, Any]]: List of message data.
        """
        try:
            self.logger.info({
                "action": "WORKING_ON_DATE_RANGE",
                "message": f"Working on date range: {start_date} to {end_date}",
                "data": {
                    "start_date": start_date,
                    "end_date": end_date
                }
            })
            # Convert dates to datetime objects
            start_datetime = from_isoformat(start_date)
            end_datetime = from_isoformat(end_date)

            self.logger.info({
                "action": "WORKING_ON_GET_MESSAGES  ",
                "message": f"Working on getting messages for conversation {conversation_id}",
                "data": {
                    "conversation_id": conversation_id,
                    "start_date": start_date,
                    "end_date": end_date
                }
            })
            # Get messages without date filtering first
            all_messages = await self._get_messages(client, conversation_id, limit=limit)
            
            # Filter by date range
            filtered_messages = []
            for message in all_messages:
                message_date = from_isoformat(message["date"])
                if start_datetime <= message_date <= end_datetime:
                    filtered_messages.append(message)
            
            self.logger.debug({
                "action": "MESSAGES_DATE_FILTERED",
                "message": f"Filtered {len(filtered_messages)} messages in date range",
                "data": {
                    "conversation_id": conversation_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "message_count": len(filtered_messages)
                }
            })
            
            # Add delay to avoid rate limiting
            await asyncio.sleep(self._request_delay)
            
            return filtered_messages
            
        except Exception as e:
            self.logger.error({
                "action": "TELEGRAM_GET_MESSAGES_DATE_RANGE_ERROR",
                "message": f"Error retrieving messages in date range for conversation {conversation_id}",
                "data": {
                    "conversation_id": conversation_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            })
            # Return empty list on error
            return []
    
    async def _fetch_all_conversations(self) -> Dict[str, Any]:
        """
        Fetch all direct message conversations and their messages.
        
        Returns:
            Dict[str, Any]: Dictionary with conversations and messages.
        """
        async def fetch_operation(client):
            result = {
                "conversations": [],
                "messages": []
            }
            
            # Get all direct message conversations
            conversations = await self._get_conversations(client)
            result["conversations"] = conversations

            self.logger.info({
                "action": "TELEGRAM_FETCH_CONVERSATIONS",
                "message": f"Fetched {len(conversations)} conversations",
                "data": {"conversations": conversations}
            })
            
            # Get messages from each conversation
            for conversation in conversations:
                conversation_id = conversation["id"]
                
                self.logger.info({
                    "action": "TELEGRAM_FETCH_CONVERSATION",
                    "message": f"Fetching messages from: {conversation['name']}",
                    "data": {
                        "conversation_id": conversation_id,
                        "conversation_name": conversation["name"]
                    }
                })
                
                # Get messages from this conversation
                messages = await self._get_messages(client, conversation_id)
                
                # Add conversation metadata to each message
                for message in messages:
                    message["conversation_name"] = conversation["name"]
                    message["conversation_username"] = conversation["username"]
                    message["source"] = "telegram"
                
                result["messages"].extend(messages)
                
                # Add delay to avoid rate limiting
                await asyncio.sleep(self._request_delay)
            
            return result
        
        # Execute with a fresh client
        return await self._with_client(fetch_operation)
    
    async def _fetch_conversations_in_range(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Fetch conversations and messages within a specified date range.
        
        Args:
            start_date: Start date in ISO format.
            end_date: End date in ISO format.
            
        Returns:
            Dict[str, Any]: Dictionary with conversations and filtered messages.
        """
        async def fetch_operation(client):
            result = {
                "conversations": [],
                "messages": []
            }
            
            # Get all direct message conversations
            conversations = await self._get_conversations(client)
            result["conversations"] = conversations

            self.logger.info({
                "action": "TELEGRAM_FETCH_CONVERSATIONS",
                "message": f"Fetched {len(conversations)} conversations",
                "data": {"conversations": conversations}
            })
            
            self.logger.info({
                "action": "TELEGRAM_FETCH_DATE_RANGE",
                "message": f"Fetching messages in date range: {start_date} to {end_date}",
                "data": {
                    "start_date": start_date,
                    "end_date": end_date
                }
            })
            
            # Get messages from each conversation in the date range
            for conversation in conversations:
                conversation_id = conversation["id"]
                
                # Get messages in date range
                messages = await self._get_messages_in_date_range(
                    client, 
                    conversation_id, 
                    start_date, 
                    end_date
                )
                
                # Skip if no messages in this range
                if not messages:
                    continue
                
                # Add conversation metadata to each message
                for message in messages:
                    message["conversation_name"] = conversation["name"]
                    message["conversation_username"] = conversation["username"]
                    message["source"] = "telegram"
                
                result["messages"].extend(messages)
                
                # Add delay to avoid rate limiting
                await asyncio.sleep(self._request_delay)
            
            return result
            
        # Execute with a fresh client
        return await self._with_client(fetch_operation)