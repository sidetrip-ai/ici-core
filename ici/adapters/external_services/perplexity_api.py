"""
Perplexity API client for web search integration.

This module provides a client for interacting with the Perplexity API
to perform web searches for real-time information such as travel planning.
"""

import os
import json
import aiohttp
from typing import Dict, Any, List, Optional
import asyncio

from ici.adapters.loggers import StructuredLogger
from ici.utils.config import get_component_config
from ici.core.exceptions import ConfigurationError


class PerplexityAPI:
    """
    Client for the Perplexity API service.
    
    This client enables real-time web search capabilities, particularly
    for travel planning based on chat data.
    """
    
    def __init__(self, logger_name: str = "perplexity_api"):
        """
        Initialize the Perplexity API client.
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = StructuredLogger(name=logger_name)
        self._is_initialized = False
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        
        # API configuration
        self._api_key = None
        self._api_url = "https://api.perplexity.ai/chat/completions"
        self._model = "sonar"  # Default model with web search capability
        self._request_timeout = 60  # Default timeout in seconds
        self._session = None
    
    async def initialize(self) -> None:
        """
        Initialize the Perplexity API client with configuration parameters.
        
        Loads API key and other settings from config.yaml.
        
        Returns:
            None
            
        Raises:
            ConfigurationError: If initialization fails
        """
        try:
            self.logger.info({
                "action": "PERPLEXITY_API_INIT_START",
                "message": "Initializing Perplexity API client"
            })
            
            # Load Perplexity API configuration
            try:
                # First try to load from system.external_services.perplexity
                try:
                    perplexity_config = get_component_config("system.external_services.perplexity", self._config_path)
                except:
                    # Fall back to external_services.perplexity
                    perplexity_config = get_component_config("external_services.perplexity", self._config_path)
                
                # Extract API key (required)
                if "api_key" not in perplexity_config:
                    # Check if API key is set in environment variable
                    env_api_key = os.environ.get("PERPLEXITY_API_KEY")
                    if env_api_key:
                        self._api_key = env_api_key
                    else:
                        # Explicitly set the hardcoded API key as fallback
                        self._api_key = "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"
                        self.logger.warning({
                            "action": "PERPLEXITY_API_KEY_HARDCODED",
                            "message": "Using hardcoded Perplexity API key as fallback"
                        })
                else:
                    self._api_key = perplexity_config["api_key"]
                
                # Extract optional configuration parameters
                if "api_url" in perplexity_config:
                    self._api_url = perplexity_config["api_url"]
                
                if "model" in perplexity_config:
                    self._model = perplexity_config["model"]
                
                if "request_timeout" in perplexity_config:
                    self._request_timeout = int(perplexity_config["request_timeout"])
                
                self.logger.info({
                    "action": "PERPLEXITY_API_CONFIG_LOADED",
                    "message": "Loaded Perplexity API configuration",
                    "data": {
                        "api_url": self._api_url,
                        "model": self._model,
                        "timeout": self._request_timeout
                    }
                })
                
            except Exception as e:
                # If we can't load from config, try environment variables
                env_api_key = os.environ.get("PERPLEXITY_API_KEY")
                if not env_api_key:
                    raise ConfigurationError(f"Failed to load Perplexity API configuration: {str(e)}")
                
                self._api_key = env_api_key
                self.logger.warning({
                    "action": "PERPLEXITY_API_CONFIG_FROM_ENV",
                    "message": f"Using Perplexity API key from environment variables. Config error: {str(e)}",
                })
            
            # Create HTTP session
            self._session = aiohttp.ClientSession()
            self._is_initialized = True
            
            self.logger.info({
                "action": "PERPLEXITY_API_INIT_SUCCESS",
                "message": "Perplexity API client initialized successfully"
            })
            
        except Exception as e:
            self.logger.error({
                "action": "PERPLEXITY_API_INIT_ERROR",
                "message": f"Failed to initialize Perplexity API client: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise ConfigurationError(f"Perplexity API initialization failed: {str(e)}") from e
    
    async def close(self) -> None:
        """
        Close the HTTP session.
        """
        if self._session:
            await self._session.close()
            self._session = None
            self._is_initialized = False
    
    async def search(self, query: str) -> Dict[str, Any]:
        """
        Perform a web search using the Perplexity API.
        
        Args:
            query: The search query
            
        Returns:
            Dict[str, Any]: Search results from Perplexity API
            
        Raises:
            Exception: If the API request fails
        """
        if not self._is_initialized:
            raise Exception("Perplexity API client not initialized. Call initialize() first.")
        
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}"
        }
        
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant with web search capabilities."},
                {"role": "user", "content": query}
            ]
        }
        
        self.logger.info({
            "action": "PERPLEXITY_API_SEARCH_START",
            "message": f"Performing web search with Perplexity API: {query[:100]}..."
        })
        
        try:
            async with self._session.post(
                self._api_url,
                headers=headers,
                json=payload,
                timeout=self._request_timeout
            ) as response:
                response_data = await response.json()
                
                if response.status != 200:
                    self.logger.error({
                        "action": "PERPLEXITY_API_SEARCH_ERROR",
                        "message": f"Perplexity API request failed with status {response.status}",
                        "data": {
                            "status": response.status,
                            "response": response_data
                        }
                    })
                    raise Exception(f"Perplexity API request failed: {response_data.get('error', {}).get('message', 'Unknown error')}")
                
                self.logger.info({
                    "action": "PERPLEXITY_API_SEARCH_SUCCESS",
                    "message": "Successfully retrieved search results from Perplexity API"
                })
                
                return response_data
                
        except asyncio.TimeoutError:
            self.logger.error({
                "action": "PERPLEXITY_API_TIMEOUT",
                "message": f"Perplexity API request timed out after {self._request_timeout} seconds",
                "data": {"timeout": self._request_timeout}
            })
            raise Exception(f"Perplexity API request timed out after {self._request_timeout} seconds")
            
        except Exception as e:
            self.logger.error({
                "action": "PERPLEXITY_API_SEARCH_ERROR",
                "message": f"Failed to search with Perplexity API: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise Exception(f"Failed to search with Perplexity API: {str(e)}")
    
    async def plan_travel(self, chat_context: str, trip_request: str) -> str:
        """
        Generate a travel plan based on chat context and trip request.
        
        Args:
            chat_context: Relevant context from Telegram chats
            trip_request: Specific travel request to plan for
            
        Returns:
            str: Detailed travel plan with real-time information
            
        Raises:
            Exception: If the API request fails
        """
        if not self._is_initialized:
            raise Exception("Perplexity API client not initialized. Call initialize() first.")
        
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        # Debug log the incoming request
        self.logger.info({
            "action": "PERPLEXITY_TRAVEL_REQUEST_DEBUG",
            "message": "Processing travel request",
            "data": {"trip_request": trip_request}
        })
        
        # Remove command prefix if it's still present
        if trip_request.startswith("/travel ") or trip_request.startswith("/trip "):
            trip_request = trip_request.split(" ", 1)[1]
            self.logger.info({
                "action": "PERPLEXITY_COMMAND_REMOVED",
                "message": "Removed command prefix from request",
                "data": {"cleaned_request": trip_request}
            })
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}"
        }
        
        # Craft a specialized prompt for travel planning
        prompt = f"""
I need a detailed travel plan based on the following conversation context:

{chat_context}

Specific request: {trip_request}

Please provide a comprehensive travel plan including:
1. Destination details and best time to visit
2. Travel logistics (transportation options, visa requirements if applicable)
3. Accommodation recommendations
4. Must-see attractions and activities
5. Food and dining recommendations
6. Estimated budget
7. Practical tips and local insights

Use up-to-date information from the web for accurate planning.
"""
        
        # Explicitly construct a valid payload for the Perplexity API
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system", 
                    "content": "You are a travel planning expert with access to real-time information through web search. Create detailed, actionable travel plans with practical information."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
        }
        
        # Extra validation to ensure we have proper role values
        for msg in payload["messages"]:
            if msg["role"] not in ["system", "user", "assistant"]:
                self.logger.error({
                    "action": "PERPLEXITY_INVALID_ROLE",
                    "message": f"Invalid role detected: {msg['role']}",
                    "data": {"messages": payload["messages"]}
                })
                # Fix the invalid role
                msg["role"] = "user"
        
        self.logger.info({
            "action": "PERPLEXITY_TRAVEL_PLANNING_START",
            "message": f"Generating travel plan for request: {trip_request[:100]}..."
        })
        
        try:
            async with self._session.post(
                self._api_url,
                headers=headers,
                json=payload,
                timeout=self._request_timeout
            ) as response:
                response_data = await response.json()
                
                if response.status != 200:
                    self.logger.error({
                        "action": "PERPLEXITY_TRAVEL_PLANNING_ERROR",
                        "message": f"Perplexity API request failed with status {response.status}",
                        "data": {
                            "status": response.status,
                            "response": response_data
                        }
                    })
                    raise Exception(f"Perplexity API request failed: {response_data.get('error', {}).get('message', 'Unknown error')}")
                
                # Extract the response content
                try:
                    assistant_response = response_data["choices"][0]["message"]["content"]
                    
                    self.logger.info({
                        "action": "PERPLEXITY_TRAVEL_PLANNING_SUCCESS",
                        "message": "Successfully generated travel plan with Perplexity API"
                    })
                    
                    return assistant_response
                    
                except (KeyError, IndexError) as e:
                    self.logger.error({
                        "action": "PERPLEXITY_RESPONSE_PARSING_ERROR",
                        "message": f"Failed to parse Perplexity API response: {str(e)}",
                        "data": {"error": str(e), "response": response_data}
                    })
                    raise Exception(f"Failed to parse Perplexity API response: {str(e)}")
                
        except asyncio.TimeoutError:
            self.logger.error({
                "action": "PERPLEXITY_API_TIMEOUT",
                "message": f"Perplexity API request timed out after {self._request_timeout} seconds",
                "data": {"timeout": self._request_timeout}
            })
            raise Exception(f"Perplexity API request timed out after {self._request_timeout} seconds")
            
        except Exception as e:
            self.logger.error({
                "action": "PERPLEXITY_TRAVEL_PLANNING_ERROR",
                "message": f"Failed to generate travel plan with Perplexity API: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise Exception(f"Failed to generate travel plan with Perplexity API: {str(e)}")
    
    async def extract_travel_entities(self, chat_content: str) -> Dict[str, Any]:
        """
        Extract travel-related entities from chat content.
        
        Args:
            chat_content: Text content from chat messages
            
        Returns:
            Dict[str, Any]: Dictionary of extracted travel entities (destinations, dates, preferences, etc.)
            
        Raises:
            Exception: If the API request fails
        """
        if not self._is_initialized:
            raise Exception("Perplexity API client not initialized. Call initialize() first.")
        
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}"
        }
        
        # Craft a specialized prompt for entity extraction
        prompt = f"""
Extract all travel-related entities from the following chat conversation:

{chat_content}

Please identify and categorize:
1. Destinations (cities, countries, specific places)
2. Date ranges or travel periods mentioned
3. Traveler preferences (accommodation, activities, budget level, etc.)
4. Any constraints or special requirements
5. Transportation preferences

Format the response as a structured JSON object with these categories.
"""
        
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": "You are a precise entity extraction assistant specialized in travel planning. Extract and categorize travel-related entities from conversations into structured data."},
                {"role": "user", "content": prompt}
            ]
        }
        
        self.logger.info({
            "action": "PERPLEXITY_ENTITY_EXTRACTION_START",
            "message": "Extracting travel entities from chat content"
        })
        
        try:
            async with self._session.post(
                self._api_url,
                headers=headers,
                json=payload,
                timeout=self._request_timeout
            ) as response:
                response_data = await response.json()
                
                if response.status != 200:
                    self.logger.error({
                        "action": "PERPLEXITY_ENTITY_EXTRACTION_ERROR",
                        "message": f"Perplexity API request failed with status {response.status}",
                        "data": {
                            "status": response.status,
                            "response": response_data
                        }
                    })
                    raise Exception(f"Perplexity API request failed: {response_data.get('error', {}).get('message', 'Unknown error')}")
                
                # Extract the response content
                try:
                    assistant_response = response_data["choices"][0]["message"]["content"]
                    
                    # Try to parse the JSON response
                    # The response might not be valid JSON if the model didn't follow instructions perfectly
                    try:
                        # Look for JSON content in the response
                        json_start = assistant_response.find('{')
                        json_end = assistant_response.rfind('}') + 1
                        
                        if json_start >= 0 and json_end > json_start:
                            json_str = assistant_response[json_start:json_end]
                            entities = json.loads(json_str)
                        else:
                            # Return as unstructured if JSON parsing fails
                            entities = {"raw_response": assistant_response}
                        
                        self.logger.info({
                            "action": "PERPLEXITY_ENTITY_EXTRACTION_SUCCESS",
                            "message": "Successfully extracted travel entities from chat content"
                        })
                        
                        return entities
                        
                    except json.JSONDecodeError:
                        # Return unstructured response if JSON parsing fails
                        self.logger.warning({
                            "action": "PERPLEXITY_JSON_PARSE_WARNING",
                            "message": "Could not parse entity extraction result as JSON, returning raw text",
                        })
                        return {"raw_response": assistant_response}
                    
                except (KeyError, IndexError) as e:
                    self.logger.error({
                        "action": "PERPLEXITY_RESPONSE_PARSING_ERROR",
                        "message": f"Failed to parse Perplexity API response: {str(e)}",
                        "data": {"error": str(e), "response": response_data}
                    })
                    raise Exception(f"Failed to parse Perplexity API response: {str(e)}")
                
        except asyncio.TimeoutError:
            self.logger.error({
                "action": "PERPLEXITY_API_TIMEOUT",
                "message": f"Perplexity API request timed out after {self._request_timeout} seconds",
                "data": {"timeout": self._request_timeout}
            })
            raise Exception(f"Perplexity API request timed out after {self._request_timeout} seconds")
            
        except Exception as e:
            self.logger.error({
                "action": "PERPLEXITY_ENTITY_EXTRACTION_ERROR",
                "message": f"Failed to extract travel entities with Perplexity API: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise Exception(f"Failed to extract travel entities with Perplexity API: {str(e)}")
