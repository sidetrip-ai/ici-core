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
        
        # User info properties
        self._user_info = None
        self._user_info_file = os.path.join("db", "telegram", "user_info.json")
    
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
            
            # Set fetch limits and options with validation
            try:
                # Validate and set max_chats
                self._max_chats = int(telegram_config.get("max_chats", 100))
                if self._max_chats != -1 and self._max_chats <= 0:
                    self.logger.warning({
                        "action": "CONFIG_WARNING",
                        "message": "Invalid max_chats value, must be -1 or > 0, using default (100)",
                        "data": {"provided_value": self._max_chats, "default": 100}
                    })
                    self._max_chats = 100
                
                # Validate and set max_messages_per_chat
                self._max_messages_per_chat = int(telegram_config.get("max_messages_per_chat", 100))
                if self._max_messages_per_chat != -1 and self._max_messages_per_chat <= 0:
                    self.logger.warning({
                        "action": "CONFIG_WARNING",
                        "message": "Invalid max_messages_per_chat value, must be -1 or > 0, using default (100)",
                        "data": {"provided_value": self._max_messages_per_chat, "default": 100}
                    })
                    self._max_messages_per_chat = 100
                
                # Validate and set batch_size 
                self._batch_size = int(telegram_config.get("batch_size", 50))
                if self._batch_size <= 0:
                    self.logger.warning({
                        "action": "CONFIG_WARNING",
                        "message": "Invalid batch_size value, must be > 0, using default (50)",
                        "data": {"provided_value": self._batch_size, "default": 50}
                    })
                    self._batch_size = 50
                
                # Convert all ignored_chats to strings for consistent comparison
                ignored_chats = telegram_config.get("ignored_chats", [])
                self._ignored_chats = [str(chat_id) for chat_id in ignored_chats]
                
                # Validate and set request delay
                self._request_delay = float(telegram_config.get("request_delay", 1.0))
                if self._request_delay < 0.1:
                    self.logger.warning({
                        "action": "CONFIG_WARNING",
                        "message": "Request delay too small, using minimum (0.1s) to avoid rate limits",
                        "data": {"provided_value": self._request_delay, "minimum": 0.1}
                    })
                    self._request_delay = 0.1
            except (ValueError, TypeError) as e:
                raise ConfigurationError(f"Invalid configuration parameter: {str(e)}") from e
            
            # Cache session string if available
            if "session_string" in telegram_config:
                self._session_string = telegram_config["session_string"]
            
            # Load cached user info
            await self._load_user_info()
            
            # Try to get user info if we have a session string
            if self._session_string and self._session_string != "your_telegram_session_string":
                try:
                    await self.get_user_info()
                except Exception as e:
                    self.logger.warning({
                        "action": "USER_INFO_RETRIEVAL_WARNING",
                        "message": f"Could not get user info during initialization: {str(e)}",
                        "data": {"error": str(e)}
                    })
            
            self.logger.info({
                "action": "INGESTOR_INITIALIZED",
                "message": "Telegram ingestor initialized successfully",
                "data": {
                    "max_chats": self._max_chats,
                    "max_messages_per_chat": self._max_messages_per_chat, 
                    "batch_size": self._batch_size,
                    "request_delay": self._request_delay,
                    "ignored_chats_count": len(self._ignored_chats),
                    "user_id": self.get_current_user_id()
                }
            })
            
        except Exception as e:
            error_message = f"Failed to initialize Telegram ingestor: {str(e)}"
            self.logger.error({
                "action": "INITIALIZATION_ERROR",
                "message": error_message,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise ConfigurationError(error_message) from e
    
    async def fetch_full_data(self) -> Dict[str, Any]:
        """
        Fetch all available conversations and their messages with relationship context.
        
        Returns:
            Dict[str, Any]: Dictionary containing conversations organized by chat_id with detailed metadata.
                {
                    "conversations": {
                        "chat_id_1": [messages],
                        "chat_id_2": [messages],
                        ...
                    },
                    "conversation_details": {
                        "chat_id_1": {conversation metadata},
                        "chat_id_2": {conversation metadata},
                        ...
                    }
                }
        """
        self.logger.info({
            "action": "FETCH_FULL_DATA_START",
            "message": "Fetching all available conversations and messages"
        })
        
        result = await self._fetch_all_conversations()
        
        self.logger.info({
            "action": "FETCH_FULL_DATA_COMPLETE",
            "message": f"Fetched {len(result.get('conversations', {}))} conversations",
            "data": {
                "conversation_count": len(result.get('conversations', {})),
                "conversation_details_count": len(result.get('conversation_details', {}))
            }
        })
        
        return result
    
    async def fetch_new_data(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Fetch new message data since the given timestamp.
        
        Args:
            since: Optional timestamp to fetch data from.
                  If None, defaults to 24 hours ago.
                  
        Returns:
            Dict[str, Any]: Dictionary containing conversations organized by chat_id with detailed metadata.
                {
                    "conversations": {
                        "chat_id_1": [messages],
                        "chat_id_2": [messages],
                        ...
                    },
                    "conversation_details": {
                        "chat_id_1": {conversation metadata},
                        "chat_id_2": {conversation metadata},
                        ...
                    }
                }
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
            "message": f"Fetched data for {len(result.get('conversations', {}))} conversations since {since_str}",
            "data": {
                "since": since_str,
                "conversation_count": len(result.get('conversations', {})),
                "conversation_details_count": len(result.get('conversation_details', {}))
            }
        })
        
        return result
    
    async def fetch_data_in_range(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """
        Fetch message data within a specific date range.
        
        Args:
            start: Start timestamp for data range.
            end: End timestamp for data range.
            
        Returns:
            Dict[str, Any]: Dictionary containing conversations organized by chat_id with detailed metadata.
                {
                    "conversations": {
                        "chat_id_1": [messages],
                        "chat_id_2": [messages],
                        ...
                    },
                    "conversation_details": {
                        "chat_id_1": {conversation metadata},
                        "chat_id_2": {conversation metadata},
                        ...
                    }
                }
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
            "message": f"Fetched data for {len(result.get('conversations', {}))} conversations in date range",
            "data": {
                "start": start_str, 
                "end": end_str,
                "conversation_count": len(result.get('conversations', {})),
                "conversation_details_count": len(result.get('conversation_details', {}))
            }
        })
        
        return result
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Perform a health check of the Telegram ingestor.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            # Test the connection
            test_result = await self._test_connection()
            
            health_status = {
                "healthy": True,
                "message": f"Connected to Telegram as {test_result.get('first_name', '')} {test_result.get('last_name', '')}",
                "details": {
                    "user_id": test_result.get("user_id"),
                    "username": test_result.get("username"),
                    "api_id": self._config.get("api_id") if self._config else None
                }
            }
            
            self.logger.info({
                "action": "HEALTHCHECK_COMPLETE",
                "message": "Telegram ingestor health check completed successfully",
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
    
    # User information methods
    
    async def get_user_info(self) -> Dict[str, Any]:
        """
        Get information about the current authenticated Telegram user.
        
        Returns:
            Dict[str, Any]: Dictionary containing user information such as user_id, username, etc.
            
        Raises:
            DataFetchError: If retrieval fails
        """
        try:
            # Return cached info if available
            if self._user_info:
                return self._user_info
            
            # Fetch from Telegram API
            user_info = await self._test_connection()
            
            # Cache the info
            if user_info and "user_id" in user_info:
                self._user_info = user_info
                await self._save_user_info()
                
                self.logger.info({
                    "action": "USER_INFO_RETRIEVED",
                    "message": "Telegram user info retrieved and cached",
                    "data": {"user_id": user_info["user_id"]}
                })
            
            return user_info
        
        except Exception as e:
            self.logger.error({
                "action": "GET_USER_INFO_ERROR",
                "message": f"Error fetching user info: {str(e)}",
                "data": {"error": str(e)}
            })
            raise DataFetchError(f"Failed to fetch Telegram user info: {str(e)}") from e
    
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
                "message": "Telegram user info saved to disk",
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
                    "message": "Telegram user info loaded from disk",
                    "data": {"user_id": self._user_info.get("user_id")}
                })
        except Exception as e:
            self.logger.warning({
                "action": "USER_INFO_LOAD_ERROR",
                "message": f"Failed to load user info: {str(e)}",
                "data": {"error": str(e)}
            })
    
    def get_current_user_id(self) -> Optional[str]:
        """
        Get the current Telegram user ID if available.
        
        Returns:
            Optional[str]: The user ID or None if not available
        """
        if self._user_info and "user_id" in self._user_info:
            return str(self._user_info["user_id"])
        return None
    
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
    
    async def _get_conversations(self, client: TelegramClient, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get a list of conversations with enhanced metadata.
        
        Args:
            client: Connected TelegramClient
            limit: Maximum number of conversations to fetch (overrides config if provided)
            
        Returns:
            List[Dict[str, Any]]: List of conversation metadata.
        """
        try:
            # Use provided limit or config value
            if limit is None:
                limit = self._max_chats
            
            # If limit is -1, use None for no limit in Telethon API
            telethon_limit = None if limit == -1 else limit
            
            self.logger.info({
                "action": "GET_CONVERSATIONS_START",
                "message": f"Fetching conversations with limit: {limit}",
                "data": {
                    "limit": limit,
                    "ignored_chats_count": len(self._ignored_chats)
                }
            })
            
            # Get dialogs (chats/conversations)
            dialogs = await client.get_dialogs(limit=telethon_limit)
            
            # Filter out ignored chats
            if self._ignored_chats:
                filtered_dialogs = []
                for dialog in dialogs:
                    entity_id = str(dialog.entity.id)
                    if entity_id not in self._ignored_chats:
                        filtered_dialogs.append(dialog)
                    else:
                        self.logger.info({
                            "action": "IGNORED_CHAT",
                            "message": f"Ignoring chat {entity_id} as configured",
                            "data": {"chat_id": entity_id}
                        })
                dialogs = filtered_dialogs
            
            # Process dialogs into the expected format
            conversations = []
            
            for dialog in dialogs:
                entity = dialog.entity
                
                # Extract the name based on entity type
                name = None
                is_group = False
                
                if hasattr(entity, 'title'):
                    # Channel or group
                    name = entity.title
                    is_group = True
                else:
                    # User or bot
                    first_name = getattr(entity, 'first_name', '')
                    last_name = getattr(entity, 'last_name', '')
                    if first_name or last_name:
                        name = f"{first_name} {last_name}".strip()
                    elif hasattr(entity, 'username'):
                        name = entity.username
                
                # Skip if we couldn't determine a name
                if not name:
                    self.logger.warning({
                        "action": "UNNAMED_ENTITY",
                        "message": "Skipping entity with no name",
                        "data": {"entity_id": entity.id if hasattr(entity, 'id') else "unknown"}
                    })
                    continue
                
                # Get last message info if available
                last_message = None
                if dialog.message:
                    last_message = {
                        "id": dialog.message.id,
                        "text": dialog.message.message if hasattr(dialog.message, 'message') else "",
                        "date": dialog.message.date.isoformat() if dialog.message.date else None
                    }
                
                # Create conversation metadata with WhatsApp compatibility
                conversation = {
                    "id": entity.id,
                    "name": name,
                    "username": entity.username if hasattr(entity, 'username') else None,
                    "last_message": last_message,
                    "last_updated": dialog.date.isoformat() if dialog.date else None,
                    "unread_count": dialog.unread_count,
                    "is_group": is_group,
                    "chat_type": "group" if is_group else "private",
                    "source": "telegram",
                    # Additional fields for WhatsApp compatibility
                    "chatId": str(entity.id),  # WhatsApp uses chatId
                    "isGroup": is_group  # WhatsApp uses isGroup
                }
                
                conversations.append(conversation)
            
            self.logger.info({
                "action": "GET_CONVERSATIONS_COMPLETE",
                "message": f"Fetched {len(conversations)} conversations",
                "data": {
                    "conversation_count": len(conversations),
                    "original_count": len(dialogs),
                    "filtered_count": len(dialogs) - len(conversations)
                }
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
                "action": "GET_CONVERSATIONS_ERROR",
                "message": "Error retrieving conversations",
                "data": {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc().splitlines()
                }
            })
            raise
    
    async def _get_messages(self, client: TelegramClient, conversation_id: int, 
                        limit: Optional[int] = None, min_id: int = None, 
                        max_id: int = None) -> List[Dict[str, Any]]:
        """
        Get messages from a specific conversation with full relationship context.
        Uses batched fetching to manage rate limits and memory usage.
        
        Args:
            client: Connected TelegramClient
            conversation_id: ID of the conversation to fetch messages from.
            limit: Maximum number of messages to fetch. If None, uses config value.
            min_id: Minimum message ID (for pagination).
            max_id: Maximum message ID (for pagination).
            
        Returns:
            List[Dict[str, Any]]: List of message data.
        """
        try:
            # Use provided limit or config value
            if limit is None:
                limit = self._max_messages_per_chat
                
            self.logger.info({
                "action": "GET_MESSAGES_START",
                "message": f"Getting messages for conversation {conversation_id}",
                "data": {
                    "conversation_id": conversation_id,
                    "limit": limit,
                    "min_id": min_id,
                    "max_id": max_id
                }
            })
            
            # Get the entity for this conversation
            entity = await client.get_entity(conversation_id)
            
            # Fetch messages in batches
            telegram_messages = await self._fetch_messages_in_batches(client, entity, limit)
            
            # Process messages into our format
            messages = []
            message_lookup = {}
            
            # First pass - create basic message objects and build lookup
            for msg in telegram_messages:
                # Skip messages without dates
                if msg.date is None:
                    self.logger.warning({
                        "action": "NULL_DATE_DETECTED",
                        "message": f"Message with ID {msg.id} has None date, skipping",
                        "data": {
                            "message_id": msg.id,
                            "conversation_id": conversation_id
                        }
                    })
                    continue
                
                # Extract sender info using a robust approach following Telethon docs
                sender_id = None
                sender_name = None
                
                # 1. First try using the sender attribute directly (already cached)
                if hasattr(msg, 'sender') and msg.sender:
                    sender_id = msg.sender_id
                    if hasattr(msg.sender, 'first_name'):
                        sender_name = msg.sender.first_name
                        if hasattr(msg.sender, 'last_name') and msg.sender.last_name:
                            sender_name += f" {msg.sender.last_name}"
                    elif hasattr(msg.sender, 'title'):
                        sender_name = msg.sender.title
                # 2. If no sender but we have a sender_id, try alternative lookup methods
                elif msg.sender_id:
                    sender_id = msg.sender_id
                    try:
                        # Try getting the input entity first (more reliable with fallbacks)
                        input_entity = await client.get_input_entity(sender_id)
                        # Then use the input entity to safely get the full entity
                        sender = await client.get_entity(input_entity)
                        
                        if hasattr(sender, 'first_name'):
                            sender_name = sender.first_name
                            if hasattr(sender, 'last_name') and sender.last_name:
                                sender_name += f" {sender.last_name}"
                        elif hasattr(sender, 'title'):
                            sender_name = sender.title
                    except Exception as e:
                        # 3. Gracefully handle lookup failure with a placeholder
                        self.logger.warning({
                            "action": "SENDER_LOOKUP_FAILED",
                            "message": f"Failed to get info for sender {sender_id}, using placeholder",
                            "data": {
                                "sender_id": sender_id,
                                "error": str(e),
                                "error_type": type(e).__name__
                            }
                        })
                        # Use a placeholder name rather than failing
                        sender_name = f"User {sender_id}"
                
                # Create message object in the expected format
                message_obj = {
                    "id": msg.id,
                    "conversation_id": conversation_id,
                    "text": self._extract_message_text(msg),
                    "date": msg.date.isoformat(),
                    "timestamp": int(msg.date.timestamp()),
                    "sender_id": sender_id,
                    "from_id": sender_id,  # Add from_id field to match the sender_id for preprocessor compatibility
                    "sender_name": sender_name,
                    "is_outgoing": msg.out if hasattr(msg, 'out') else False,
                    "reply_to_id": msg.reply_to.reply_to_msg_id if msg.reply_to else None,
                    # Fields for WhatsApp compatibility
                    "messageId": str(msg.id),
                    "chatId": str(conversation_id)
                }
                
                messages.append(message_obj)
                message_lookup[msg.id] = message_obj
            
            # Log message fields for debugging
            if messages and len(messages) > 0:
                first_msg = messages[0]
                self.logger.debug({
                    "action": "TELEGRAM_MESSAGE_FIELDS",
                    "message": "Telegram message fields available after processing",
                    "data": {
                        "has_sender_id": "sender_id" in first_msg,
                        "has_from_id": "from_id" in first_msg,
                        "sample_keys": list(first_msg.keys())[:10]  # Show first 10 keys to avoid huge log
                    }
                })
            
            # Second pass - establish relationships between messages
            for message in messages:
                if message["reply_to_id"]:
                    # Look up the reply message if it exists in our set
                    reply_to = message_lookup.get(message["reply_to_id"])
                    if reply_to:
                        message["reply_to"] = {
                            "id": reply_to["id"],
                            "date": reply_to["date"],
                            "text": reply_to["text"][:100] + ("..." if len(reply_to["text"]) > 100 else ""),
                            "sender_name": reply_to["sender_name"]
                        }
            
            self.logger.info({
                "action": "GET_MESSAGES_COMPLETE",
                "message": f"Retrieved {len(messages)} messages from conversation {conversation_id}",
                "data": {
                    "conversation_id": conversation_id,
                    "message_count": len(messages),
                    "original_count": len(telegram_messages),
                    "filtered_count": len(telegram_messages) - len(messages)
                }
            })
            
            return messages
            
        except FloodWaitError as e:
            # Implement exponential backoff
            wait_time = e.seconds
            
            # Add a small buffer to the wait time
            wait_time = max(wait_time, 1) * 1.1
            
            self.logger.warning({
                "action": "RATE_LIMITED",
                "message": f"Rate limited by Telegram, waiting {wait_time:.1f} seconds",
                "data": {
                    "conversation_id": conversation_id,
                    "wait_time": wait_time,
                    "telegram_seconds": e.seconds
                }
            })
            await asyncio.sleep(wait_time)
            # Return empty list, caller should retry
            return []
            
        except Exception as e:
            self.logger.error({
                "action": "GET_MESSAGES_ERROR",
                "message": f"Error retrieving messages from conversation {conversation_id}",
                "data": {
                    "conversation_id": conversation_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc().splitlines()
                }
            })
            # Return empty list on error
            return []
    
    async def _get_messages_in_date_range(self, client: TelegramClient, conversation_id: int, 
                                     start_date: str, end_date: str, 
                                     limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get messages from a conversation within a specified date range with relationship context.
        Uses batched fetching to manage rate limits and memory usage.
        
        Args:
            client: Connected TelegramClient
            conversation_id: ID of the conversation.
            start_date: Start date in ISO format.
            end_date: End date in ISO format.
            limit: Maximum number of messages to fetch. If None, uses config value.
            
        Returns:
            List[Dict[str, Any]]: List of message data with relationship context.
        """
        try:
            # Use provided limit or config value
            if limit is None:
                limit = self._max_messages_per_chat
                
            self.logger.info({
                "action": "GET_MESSAGES_DATE_RANGE_START",
                "message": f"Getting messages in date range: {start_date} to {end_date}",
                "data": {
                    "conversation_id": conversation_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "limit": limit
                }
            })
            
            # Convert dates to datetime objects
            start_datetime = from_isoformat(start_date)
            end_datetime = from_isoformat(end_date)

            # First get all messages using our optimized fetching method
            # Use a larger limit since we'll be filtering by date
            fetch_limit = limit if limit != -1 else -1
            messages = await self._get_messages(client, conversation_id, limit=fetch_limit)
            
            # Filter by date range
            filtered_messages = []
            skipped_null_dates = 0
            
            for message in messages:
                # Skip messages with no date
                if message["date"] is None:
                    skipped_null_dates += 1
                    continue
                    
                message_date = from_isoformat(message["date"])
                if start_datetime <= message_date <= end_datetime:
                    filtered_messages.append(message)
                    
                    # Stop if we've reached the limit
                    if limit != -1 and len(filtered_messages) >= limit:
                        break
            
            # Log skipped messages count if any
            if skipped_null_dates > 0:
                self.logger.warning({
                    "action": "NULL_DATES_SKIPPED",
                    "message": f"Skipped {skipped_null_dates} messages with None date in conversation {conversation_id}",
                    "data": {
                        "conversation_id": conversation_id,
                        "skipped_messages": skipped_null_dates,
                        "total_messages": len(messages)
                    }
                })
            
            self.logger.info({
                "action": "GET_MESSAGES_DATE_RANGE_COMPLETE",
                "message": f"Filtered {len(filtered_messages)} messages in date range",
                "data": {
                    "conversation_id": conversation_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "filtered_message_count": len(filtered_messages),
                    "total_message_count": len(messages)
                }
            })
            
            return filtered_messages
            
        except FloodWaitError as e:
            # Implement exponential backoff similar to _get_messages
            wait_time = e.seconds
            
            # Add a small buffer to the wait time
            wait_time = max(wait_time, 1) * 1.1
            
            self.logger.warning({
                "action": "RATE_LIMITED",
                "message": f"Rate limited by Telegram, waiting {wait_time:.1f} seconds",
                "data": {
                    "conversation_id": conversation_id,
                    "wait_time": wait_time,
                    "telegram_seconds": e.seconds,
                    "start_date": start_date,
                    "end_date": end_date
                }
            })
            await asyncio.sleep(wait_time)
            # Return empty list, caller should retry
            return []
            
        except Exception as e:
            self.logger.error({
                "action": "GET_MESSAGES_DATE_RANGE_ERROR",
                "message": f"Error retrieving messages in date range for conversation {conversation_id}",
                "data": {
                    "conversation_id": conversation_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc().splitlines()
                }
            })
            # Return empty list on error
            return []
    
    async def _fetch_all_conversations(self) -> Dict[str, Any]:
        """
        Fetch all conversations and their messages with relationship context.
        
        Returns:
            Dict[str, Any]: Dictionary with conversations organized by chat_id
                {
                    "conversations": {
                        "chat_id_1": [messages],
                        "chat_id_2": [messages],
                        ...
                    },
                    "conversation_details": {
                        "chat_id_1": {conversation metadata},
                        "chat_id_2": {conversation metadata},
                        ...
                    }
                }
        """
        async def fetch_operation(client):
            # Structure similar to WhatsApp ingestor output
            result = {
                "conversations": {},  # Dictionary of conversation_id -> [messages]
                "conversation_details": {}  # Dictionary of conversation metadata
            }
            
            # Get all conversations
            conversations = await self._get_conversations(client)

            self.logger.info({
                "action": "TELEGRAM_FETCH_CONVERSATIONS",
                "message": f"Fetched {len(conversations)} conversations",
                "data": {"conversation_count": len(conversations)}
            })
            
            # Store conversation details for metadata access
            for conversation in conversations:
                chat_id = str(conversation["id"])
                result["conversation_details"][chat_id] = conversation
            
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
                
                # Skip if no messages
                if not messages:
                    continue
                
                # Add conversation metadata to each message
                for message in messages:
                    message["conversation_name"] = conversation["name"]
                    message["conversation_username"] = conversation.get("username")
                    message["source"] = "telegram"
                    message["is_group"] = conversation.get("is_group", False)
                    message["chat_type"] = conversation.get("chat_type", "private")
                
                # Store messages organized by conversation ID - similar to WhatsApp structure
                result["conversations"][str(conversation_id)] = messages
                
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
            Dict[str, Any]: Dictionary with conversations organized by chat_id
                {
                    "conversations": {
                        "chat_id_1": [messages],
                        "chat_id_2": [messages],
                        ...
                    },
                    "conversation_details": {
                        "chat_id_1": {conversation metadata},
                        "chat_id_2": {conversation metadata},
                        ...
                    }
                }
        """
        async def fetch_operation(client):
            # Structure similar to WhatsApp ingestor output
            result = {
                "conversations": {},  # Dictionary of conversation_id -> [messages]
                "conversation_details": {}  # Dictionary of conversation metadata
            }
            
            # Get all conversations
            conversations = await self._get_conversations(client)

            self.logger.info({
                "action": "TELEGRAM_FETCH_CONVERSATIONS",
                "message": f"Fetched {len(conversations)} conversations",
                "data": {"conversation_count": len(conversations)}
            })
            
            # Store conversation details for metadata access
            for conversation in conversations:
                chat_id = str(conversation["id"])
                result["conversation_details"][chat_id] = conversation
            
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
                    message["conversation_username"] = conversation.get("username")
                    message["source"] = "telegram"
                    message["is_group"] = conversation.get("is_group", False)
                    message["chat_type"] = conversation.get("chat_type", "private")
                
                # Store messages organized by conversation ID - similar to WhatsApp structure
                result["conversations"][str(conversation_id)] = messages
                
                # Add delay to avoid rate limiting
                await asyncio.sleep(self._request_delay)
            
            return result
            
        # Execute with a fresh client
        return await self._with_client(fetch_operation)

    async def _fetch_messages_in_batches(self, client: TelegramClient, entity, total_limit: int) -> List[Any]:
        """
        Fetch messages in batches to manage rate limiting and memory usage.
        
        Args:
            client: Connected TelegramClient
            entity: Telegram entity (user, chat, or channel) to fetch messages from
            total_limit: Maximum number of messages to fetch (-1 for all available)
            
        Returns:
            List of Telegram Message objects
        """
        # Get batch size and delay from config
        batch_size = self._batch_size
        delay = self._request_delay
        
        self.logger.info({
            "action": "FETCH_MESSAGES_BATCHED_START",
            "message": f"Fetching messages in batches from {getattr(entity, 'id', 'unknown')}",
            "data": {
                "entity_id": getattr(entity, 'id', 'unknown'),
                "total_limit": total_limit,
                "batch_size": batch_size,
                "delay": delay
            }
        })
        
        all_messages = []
        offset_id = 0
        batch_count = 0
        retry_count = 0
        max_retries = 5
        base_delay = self._request_delay
        
        while True:
            try:
                # Break if we have enough messages
                if total_limit != -1 and len(all_messages) >= total_limit:
                    break
                
                # Calculate the current batch limit
                current_limit = batch_size
                if total_limit != -1:
                    current_limit = min(batch_size, total_limit - len(all_messages))
                
                # Get the next batch of messages
                batch = await client.get_messages(
                    entity, 
                    limit=current_limit,
                    offset_id=offset_id
                )
                
                # Reset retry count after successful fetch
                retry_count = 0
                
                # Convert to list if it's an iterator
                batch_list = list(batch)
                batch_count += 1
                
                # Break if no more messages
                if not batch_list:
                    self.logger.info({
                        "action": "FETCH_MESSAGES_BATCH_EMPTY",
                        "message": "No more messages to fetch, reached end",
                        "data": {"total_fetched": len(all_messages)}
                    })
                    break
                
                # Add to our collection
                all_messages.extend(batch_list)
                
                # Update offset for next batch
                offset_id = batch_list[-1].id
                
                self.logger.info({
                    "action": "FETCH_MESSAGES_BATCH_COMPLETE",
                    "message": f"Fetched batch {batch_count} ({len(batch_list)} messages)",
                    "data": {
                        "batch_number": batch_count,
                        "batch_size": len(batch_list),
                        "total_fetched": len(all_messages),
                        "next_offset_id": offset_id
                    }
                })
                
                # Delay to respect rate limits
                await asyncio.sleep(delay)
                
            except FloodWaitError as e:
                # Implement exponential backoff
                retry_count += 1
                
                # Use the longer of Telegram's suggested wait time or our calculated backoff
                telegram_wait = e.seconds
                backoff_wait = base_delay * (2 ** retry_count)
                wait_time = max(telegram_wait, backoff_wait)
                
                # Cap maximum wait time at 5 minutes
                wait_time = min(wait_time, 300)
                
                self.logger.warning({
                    "action": "RATE_LIMITED",
                    "message": f"Rate limited by Telegram (retry {retry_count}/{max_retries}), waiting {wait_time:.1f} seconds",
                    "data": {
                        "telegram_wait": telegram_wait,
                        "backoff_wait": backoff_wait,
                        "actual_wait": wait_time,
                        "retry_count": retry_count,
                        "entity_id": getattr(entity, 'id', 'unknown')
                    }
                })
                
                # Sleep for the specified time
                await asyncio.sleep(wait_time)
                
                # If we've exceeded max retries, give up
                if retry_count >= max_retries:
                    self.logger.error({
                        "action": "RATE_LIMIT_MAX_RETRIES",
                        "message": f"Exceeded maximum retries ({max_retries}) for rate limiting",
                        "data": {
                            "entity_id": getattr(entity, 'id', 'unknown'),
                            "total_fetched": len(all_messages),
                            "max_retries": max_retries
                        }
                    })
                    break
                
                # Continue to retry
                continue  # Retry after waiting
                
            except Exception as e:
                self.logger.error({
                    "action": "FETCH_MESSAGES_BATCH_ERROR",
                    "message": f"Error fetching message batch: {str(e)}",
                    "data": {
                        "entity_id": getattr(entity, 'id', 'unknown'),
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "total_fetched": len(all_messages)
                    }
                })
                break  # Stop on error
        
        self.logger.info({
            "action": "FETCH_MESSAGES_BATCHED_COMPLETE",
            "message": f"Completed fetching {len(all_messages)} messages in {batch_count} batches",
            "data": {
                "entity_id": getattr(entity, 'id', 'unknown'),
                "total_messages": len(all_messages),
                "batch_count": batch_count
            }
        })
        
        return all_messages

    def _extract_message_text(self, msg):
        """
        Extract message text from a Telegram message object.
        
        Args:
            msg: Telegram message object
            
        Returns:
            str: Extracted message text
        """
        if hasattr(msg, 'message') and msg.message:
            return msg.message
        elif hasattr(msg, 'caption') and msg.caption:
            return msg.caption
        else:
            return ""