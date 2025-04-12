"""
Travel planner integration using Perplexity API and Telegram chat data.

This module analyzes Telegram chat data to extract travel-related queries
and generates comprehensive travel plans using the Perplexity API.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from ici.adapters.loggers import StructuredLogger
from ici.utils.config import get_component_config
from ici.core.exceptions import ConfigurationError
from ici.adapters.external_services.perplexity_api import PerplexityAPI


class TravelPlanner:
    """
    Travel planner that analyzes chat data and creates travel plans.
    
    This component extracts travel planning requests from Telegram chats
    and generates comprehensive travel plans using the Perplexity API
    for real-time information.
    """
    
    def __init__(self, logger_name: str = "travel_planner"):
        """
        Initialize the travel planner.
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = StructuredLogger(name=logger_name)
        self._is_initialized = False
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        
        # Perplexity API client
        self._perplexity_api = None
        
        # Configuration parameters
        self._context_window_days = 7  # Default: analyze chat context from last 7 days
        self._max_chat_messages = 100  # Default: max messages to include in context
        self._chat_history_dir = "db/telegram_chats"  # Default path for chat history
    
    async def initialize(self) -> None:
        """
        Initialize the travel planner with configuration parameters.
        
        Loads configuration from config.yaml and initializes the Perplexity API client.
        
        Returns:
            None
            
        Raises:
            ConfigurationError: If initialization fails
        """
        try:
            self.logger.info({
                "action": "TRAVEL_PLANNER_INIT_START",
                "message": "Initializing travel planner"
            })
            
            # Load travel planner configuration
            try:
                # First try to load from system.external_services.travel_planner
                try:
                    travel_planner_config = get_component_config("system.external_services.travel_planner", self._config_path)
                except:
                    # Fall back to external_services.travel_planner
                    try:
                        travel_planner_config = get_component_config("external_services.travel_planner", self._config_path)
                    except:
                        # If neither path works, use defaults
                        travel_planner_config = {}
                        self.logger.warning({
                            "action": "TRAVEL_PLANNER_CONFIG_DEFAULT",
                            "message": "Using default travel planner configuration"
                        })
                
                # Extract configuration parameters
                if "context_window_days" in travel_planner_config:
                    self._context_window_days = int(travel_planner_config["context_window_days"])
                
                if "max_chat_messages" in travel_planner_config:
                    self._max_chat_messages = int(travel_planner_config["max_chat_messages"])
                
                if "chat_history_dir" in travel_planner_config:
                    self._chat_history_dir = travel_planner_config["chat_history_dir"]
                
                self.logger.info({
                    "action": "TRAVEL_PLANNER_CONFIG_LOADED",
                    "message": "Loaded travel planner configuration",
                    "data": {
                        "context_window_days": self._context_window_days,
                        "max_chat_messages": self._max_chat_messages,
                        "chat_history_dir": self._chat_history_dir
                    }
                })
                
            except Exception as e:
                # Use defaults if configuration loading fails
                self.logger.warning({
                    "action": "TRAVEL_PLANNER_CONFIG_WARNING",
                    "message": f"Failed to load travel planner configuration: {str(e)}. Using defaults.",
                    "data": {"error": str(e)}
                })
            
            # Initialize Perplexity API client
            try:
                self._perplexity_api = PerplexityAPI()
                await self._perplexity_api.initialize()
                
                # Set the API key manually if not already set
                if not self._perplexity_api._api_key:
                    # Hardcode the API key as an absolute fallback
                    self._perplexity_api._api_key = "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"
                    self.logger.warning({
                        "action": "PERPLEXITY_API_KEY_FALLBACK",
                        "message": "Setting fallback Perplexity API key in TravelPlanner"
                    })
                
                self.logger.info({
                    "action": "PERPLEXITY_API_INITIALIZED",
                    "message": "Perplexity API client initialized successfully"
                })
                
            except Exception as e:
                self.logger.error({
                    "action": "PERPLEXITY_API_INIT_ERROR",
                    "message": f"Failed to initialize Perplexity API client: {str(e)}",
                    "data": {"error": str(e)}
                })
                raise ConfigurationError(f"Failed to initialize Perplexity API client: {str(e)}") from e
            
            self._is_initialized = True
            
            self.logger.info({
                "action": "TRAVEL_PLANNER_INIT_SUCCESS",
                "message": "Travel planner initialized successfully"
            })
            
        except Exception as e:
            self.logger.error({
                "action": "TRAVEL_PLANNER_INIT_ERROR",
                "message": f"Failed to initialize travel planner: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise ConfigurationError(f"Travel planner initialization failed: {str(e)}") from e
    
    async def close(self) -> None:
        """
        Close any open resources.
        """
        if self._perplexity_api:
            await self._perplexity_api.close()
    
    async def detect_travel_request(self, message_text: str) -> bool:
        """
        Detect if a message contains a travel planning request.
        
        Args:
            message_text: Text content of the message
            
        Returns:
            bool: True if the message is likely a travel planning request
        """
        # List of keywords and phrases that indicate travel planning
        travel_keywords = [
            "plan a trip", "travel to", "vacation", "holiday", "itinerary",
            "visit", "flight", "hotel", "accommodation", "booking",
            "tourist", "tourism", "sightseeing", "attractions", "places to see",
            "travel plan", "weekend getaway", "city break", "road trip"
        ]
        
        # Convert message to lowercase for case-insensitive matching
        message_lower = message_text.lower()
        
        # Check for travel keywords
        for keyword in travel_keywords:
            if keyword in message_lower:
                return True
        
        return False
    
    async def get_chat_context(self, chat_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve recent chat messages for a specific chat.
        
        Args:
            chat_id: ID of the chat to retrieve messages from
            limit: Maximum number of messages to retrieve
            
        Returns:
            List[Dict[str, Any]]: List of recent chat messages with metadata
        """
        try:
            # Construct path to chat history file
            chat_file_path = os.path.join(self._chat_history_dir, f"{chat_id}.json")
            
            # Check if chat history file exists
            if not os.path.exists(chat_file_path):
                self.logger.warning({
                    "action": "CHAT_HISTORY_NOT_FOUND",
                    "message": f"Chat history file not found for chat ID: {chat_id}",
                    "data": {"chat_id": chat_id, "path": chat_file_path}
                })
                return []
            
            # Read chat history file
            with open(chat_file_path, 'r') as f:
                chat_data = json.load(f)
            
            # Get recent messages (up to limit)
            messages = chat_data.get("messages", [])
            recent_messages = messages[-limit:] if len(messages) > limit else messages
            
            self.logger.info({
                "action": "CHAT_CONTEXT_RETRIEVED",
                "message": f"Retrieved {len(recent_messages)} messages for chat context",
                "data": {"chat_id": chat_id, "message_count": len(recent_messages)}
            })
            
            return recent_messages
            
        except Exception as e:
            self.logger.error({
                "action": "CHAT_CONTEXT_ERROR",
                "message": f"Failed to retrieve chat context: {str(e)}",
                "data": {"error": str(e), "chat_id": chat_id}
            })
            return []
    
    async def extract_chat_text(self, messages: List[Dict[str, Any]]) -> str:
        """
        Extract text content from chat messages.
        
        Args:
            messages: List of chat message dictionaries
            
        Returns:
            str: Concatenated text of messages formatted as a conversation
        """
        conversation = []
        
        for msg in messages:
            sender = msg.get("sender_name", "Unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            
            # Format message with sender and timestamp if available
            if timestamp:
                try:
                    # Convert timestamp to datetime if it's a string
                    if isinstance(timestamp, str):
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    else:
                        dt = timestamp
                    
                    time_str = dt.strftime("%Y-%m-%d %H:%M")
                    formatted_msg = f"[{time_str}] {sender}: {content}"
                except:
                    formatted_msg = f"{sender}: {content}"
            else:
                formatted_msg = f"{sender}: {content}"
            
            conversation.append(formatted_msg)
        
        return "\n".join(conversation)
    
    async def plan_trip(self, chat_id: str, query: str) -> str:
        """
        Generate a travel plan based on chat context and specific query.
        
        Args:
            chat_id: ID of the chat to use for context
            query: Specific travel planning query
            
        Returns:
            str: Generated travel plan
            
        Raises:
            Exception: If travel planning fails
        """
        if not self._is_initialized:
            raise Exception("Travel planner not initialized. Call initialize() first.")
        
        try:
            self.logger.info({
                "action": "TRAVEL_PLANNING_START",
                "message": f"Planning trip for chat {chat_id}",
                "data": {"chat_id": chat_id, "query": query}
            })
            
            # Get recent chat messages for context
            messages = await self.get_chat_context(chat_id, self._max_chat_messages)
            
            if not messages:
                self.logger.warning({
                    "action": "NO_CHAT_CONTEXT",
                    "message": f"No chat context available for chat ID: {chat_id}",
                    "data": {"chat_id": chat_id}
                })
                # Proceed with just the query, without context
                chat_context = ""
            else:
                # Extract text content from messages
                chat_context = await self.extract_chat_text(messages)
            
            # Generate travel plan using Perplexity API
            self.logger.info({
                "action": "TRAVEL_QUERY_DEBUG",
                "message": "About to call Perplexity API",
                "data": {"query": query, "query_type": type(query).__name__}
            })
            
            # Make sure we're not passing the command prefix
            if query.startswith("/travel ") or query.startswith("/trip "):
                # Strip the command prefix
                clean_query = query.split(" ", 1)[1]
                self.logger.info({
                    "action": "TRAVEL_QUERY_CLEANED",
                    "message": "Removed command prefix from query",
                    "data": {"original": query, "cleaned": clean_query}
                })
                query = clean_query
                
            travel_plan = await self._perplexity_api.plan_travel(chat_context, query)
            
            self.logger.info({
                "action": "TRAVEL_PLANNING_SUCCESS",
                "message": "Successfully generated travel plan",
                "data": {"chat_id": chat_id, "plan_length": len(travel_plan)}
            })
            
            return travel_plan
            
        except Exception as e:
            self.logger.error({
                "action": "TRAVEL_PLANNING_ERROR",
                "message": f"Failed to generate travel plan: {str(e)}",
                "data": {"error": str(e), "chat_id": chat_id}
            })
            raise Exception(f"Failed to generate travel plan: {str(e)}")
    
    async def extract_travel_entities_from_chat(self, chat_id: str) -> Dict[str, Any]:
        """
        Extract travel-related entities from a chat's recent messages.
        
        Args:
            chat_id: ID of the chat to analyze
            
        Returns:
            Dict[str, Any]: Dictionary of extracted travel entities
            
        Raises:
            Exception: If entity extraction fails
        """
        if not self._is_initialized:
            raise Exception("Travel planner not initialized. Call initialize() first.")
        
        try:
            self.logger.info({
                "action": "ENTITY_EXTRACTION_START",
                "message": f"Extracting travel entities from chat {chat_id}",
                "data": {"chat_id": chat_id}
            })
            
            # Get recent chat messages for context
            messages = await self.get_chat_context(chat_id, self._max_chat_messages)
            
            if not messages:
                self.logger.warning({
                    "action": "NO_CHAT_CONTEXT",
                    "message": f"No chat context available for chat ID: {chat_id}",
                    "data": {"chat_id": chat_id}
                })
                return {"error": "No chat context available"}
            
            # Extract text content from messages
            chat_context = await self.extract_chat_text(messages)
            
            # Extract travel entities using Perplexity API
            entities = await self._perplexity_api.extract_travel_entities(chat_context)
            
            self.logger.info({
                "action": "ENTITY_EXTRACTION_SUCCESS",
                "message": "Successfully extracted travel entities",
                "data": {"chat_id": chat_id, "entity_count": len(entities)}
            })
            
            return entities
            
        except Exception as e:
            self.logger.error({
                "action": "ENTITY_EXTRACTION_ERROR",
                "message": f"Failed to extract travel entities: {str(e)}",
                "data": {"error": str(e), "chat_id": chat_id}
            })
            raise Exception(f"Failed to extract travel entities: {str(e)}")
    
    async def process_message(self, message: Dict[str, Any]) -> Optional[str]:
        """
        Process an incoming message to detect and respond to travel planning requests.
        
        Args:
            message: Message dictionary with content and metadata
            
        Returns:
            Optional[str]: Travel plan response if the message is a travel request, None otherwise
        """
        if not self._is_initialized:
            raise Exception("Travel planner not initialized. Call initialize() first.")
        
        try:
            # Extract message content and metadata
            content = message.get("content", "")
            chat_id = message.get("chat_id", "")
            
            if not content or not chat_id:
                return None
            
            # Check if message is a travel planning request
            is_travel_request = await self.detect_travel_request(content)
            
            if not is_travel_request:
                return None
            
            self.logger.info({
                "action": "TRAVEL_REQUEST_DETECTED",
                "message": f"Detected travel planning request in chat {chat_id}",
                "data": {"chat_id": chat_id, "message_content": content[:100] + "..." if len(content) > 100 else content}
            })
            
            # Generate travel plan
            travel_plan = await self.plan_trip(chat_id, content)
            
            return travel_plan
            
        except Exception as e:
            self.logger.error({
                "action": "MESSAGE_PROCESSING_ERROR",
                "message": f"Failed to process message: {str(e)}",
                "data": {"error": str(e)}
            })
            return None
