"""
Travel-aware orchestrator implementation.

This module extends the DefaultOrchestrator to add travel planning capabilities
using Perplexity API and Telegram chat data.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple

from ici.adapters.orchestrators.default_orchestrator import DefaultOrchestrator
from ici.adapters.external_services.travel_planner import TravelPlanner
from ici.adapters.loggers import StructuredLogger
from ici.core.exceptions import OrchestratorError


class TravelOrchestrator(DefaultOrchestrator):
    """
    Travel-aware orchestrator for processing queries with travel planning capabilities.
    
    This orchestrator extends the DefaultOrchestrator to detect travel planning requests
    and leverage the Perplexity API for comprehensive travel planning.
    """
    
    def __init__(self, logger_name: str = "travel_orchestrator"):
        """
        Initialize the TravelOrchestrator.
        
        Args:
            logger_name: Name to use for the logger
        """
        super().__init__(logger_name=logger_name)
        
        # Initialize TravelPlanner
        self._travel_planner = None
        
        # Travel command prefix
        self._travel_command_prefix = "/travel"
        
        # Extended commands for travel functionality
        self._commands.update({
            "/travel": self._handle_travel_command,
            "/trip": self._handle_travel_command  # Alias for convenience
        })
    
    async def initialize(self) -> None:
        """
        Initialize the orchestrator with configuration parameters.
        
        Loads orchestrator configuration, initializes all components,
        and sets up the TravelPlanner.
        
        Returns:
            None
            
        Raises:
            OrchestratorError: If initialization fails
        """
        # Initialize default components first
        await super().initialize()
        
        try:
            self.logger.info({
                "action": "TRAVEL_ORCHESTRATOR_INIT_START",
                "message": "Initializing TravelOrchestrator"
            })
            
            # Initialize TravelPlanner
            self._travel_planner = TravelPlanner()
            await self._travel_planner.initialize()
            
            self.logger.info({
                "action": "TRAVEL_ORCHESTRATOR_INIT_SUCCESS",
                "message": "TravelOrchestrator initialized successfully"
            })
            
        except Exception as e:
            self.logger.error({
                "action": "TRAVEL_ORCHESTRATOR_INIT_ERROR",
                "message": f"Failed to initialize travel orchestrator: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise OrchestratorError(f"Travel orchestrator initialization failed: {str(e)}") from e
    
    async def process_query(self, source: str, user_id: str, query: str, additional_info: Dict[str, Any]) -> str:
        """
        Process a query with travel planning awareness.
        
        Checks if the query is a travel planning request and processes accordingly.
        If not, delegates to the default orchestrator processing.
        
        Args:
            source: The source of the query
            user_id: Identifier for the user making the request
            query: The user input/question to process
            additional_info: Dictionary containing additional attributes and values
            
        Returns:
            str: Response to the query
            
        Raises:
            OrchestratorError: If the orchestration process fails
        """
        if not self._is_initialized:
            raise OrchestratorError("Orchestrator not initialized")
        
        try:
            # Check for explicit travel commands
            if query.strip().startswith(self._travel_command_prefix) or query.strip().startswith("/trip"):
                return await self._handle_travel_command(source, user_id, query, additional_info)
            
            # Check for travel planning keywords
            is_travel_query = await self._detect_travel_query(query)
            
            # Get active chat id for this user
            chat_id = self._active_chats.get(user_id, "default")
            
            if is_travel_query:
                self.logger.info({
                    "action": "TRAVEL_QUERY_DETECTED",
                    "message": "Detected travel planning query",
                    "data": {"user_id": user_id, "chat_id": chat_id}
                })
                
                try:
                    # Generate travel plan
                    travel_plan = await self._travel_planner.plan_trip(chat_id, query)
                    
                    # Store in chat history if available
                    if self._chat_history_manager:
                        await self._chat_history_manager.add_message(
                            chat_id, 
                            "user",
                            query,
                            {"source": source, "user_id": user_id}
                        )
                        
                        await self._chat_history_manager.add_message(
                            chat_id,
                            "assistant",
                            travel_plan,
                            {"generated_with": "perplexity_api", "travel_plan": True}
                        )
                    
                    return travel_plan
                    
                except Exception as e:
                    self.logger.error({
                        "action": "TRAVEL_PLANNING_ERROR",
                        "message": f"Failed to generate travel plan: {str(e)}",
                        "data": {"error": str(e), "user_id": user_id, "chat_id": chat_id}
                    })
                    # Fall back to default processing if travel planning fails
            
            # If not a travel query or if travel processing failed, use default processing
            return await super().process_query(source, user_id, query, additional_info)
            
        except Exception as e:
            self.logger.error({
                "action": "QUERY_PROCESSING_ERROR",
                "message": f"Failed to process query: {str(e)}",
                "data": {"error": str(e), "user_id": user_id, "query": query}
            })
            return self._error_messages["generation_failed"]
    
    async def _detect_travel_query(self, query: str) -> bool:
        """
        Detect if a query is related to travel planning.
        
        Args:
            query: The user query to analyze
            
        Returns:
            bool: True if the query is travel-related
        """
        # List of travel-related keywords and phrases
        travel_keywords = [
            "travel to", "trip to", "visit", "vacation", "holiday",
            "flight", "hotel", "accommodation", "booking", "itinerary",
            "tourist", "tourism", "sightseeing", "attractions", "places to see",
            "travel plan", "plan a trip", "weekend getaway", "city break"
        ]
        
        # Check if query contains "plan a trip" or similar phrases
        plan_trip_patterns = [
            r"plan\s+(?:a|my|our)\s+trip",
            r"(?:help|assist)(?:\s+me|\s+us)?\s+(?:plan|arrange|organize)(?:\s+a|\s+my|\s+our)?\s+trip",
            r"(?:need|looking\s+for)(?:\s+help)?\s+(?:planning|organizing)(?:\s+a|\s+my|\s+our)?\s+(?:trip|vacation|holiday)",
            r"(?:can\s+you\s+plan|could\s+you\s+plan|would\s+you\s+plan)(?:\s+a|\s+my|\s+our)?\s+trip"
        ]
        
        # Convert query to lowercase for case-insensitive matching
        query_lower = query.lower()
        
        # Check for travel keywords
        for keyword in travel_keywords:
            if keyword in query_lower:
                return True
        
        # Check for planning patterns
        for pattern in plan_trip_patterns:
            if re.search(pattern, query_lower):
                return True
        
        # Check for multi-step pattern: check + plan
        check_patterns = [
            r"check\s+(?:what'?s\s+happening|what\s+is\s+happening)",
            r"see\s+(?:what'?s\s+happening|what\s+is\s+happening)"
        ]
        
        plan_patterns = [
            r"plan\s+(?:a|the|my|our)\s+(?:trip|vacation|holiday|travel)",
            r"plan\s+accordingly"
        ]
        
        for check_pattern in check_patterns:
            for plan_pattern in plan_patterns:
                combined_pattern = f"{check_pattern}.*{plan_pattern}"
                if re.search(combined_pattern, query_lower):
                    return True
        
        return False
    
    async def _handle_travel_command(self, source: str, user_id: str, query: str, additional_info: Dict[str, Any]) -> str:
        """
        Handle explicit travel planning commands.
        
        Args:
            source: The source of the query
            user_id: Identifier for the user making the request
            query: The user input/question to process
            additional_info: Dictionary containing additional attributes and values
            
        Returns:
            str: Travel plan or help text
        """
        # Log the incoming command for debugging
        self.logger.info({
            "action": "TRAVEL_COMMAND_RECEIVED",
            "message": "Received travel command",
            "data": {"query": query}
        })
        
        # Remove command prefix to get the actual query
        command_parts = query.strip().split(maxsplit=1)
        
        if len(command_parts) == 1:
            # Just the command with no query, show help
            return """
**Travel Planning Assistant**

Use the `/travel` command followed by your travel request to get a comprehensive travel plan.

Examples:
- `/travel Plan a weekend trip to New York`
- `/travel What are the best places to visit in Japan in spring?`
- `/travel I want to go hiking in Colorado next month`

You can also check what's happening in a chat with someone and plan a trip based on your conversation by using:
`/travel Check what's happening in my chat with [person] and plan a trip accordingly`
"""
        
        # Extract the actual travel query
        travel_query = command_parts[1]
        
        # Get active chat id for this user
        chat_id = self._active_chats.get(user_id, "default")
        
        try:
            # Check for special syntax to analyze chat with someone
            chat_with_pattern = r"(?:check|see)\s+what'?s\s+happening\s+(?:in|with)\s+(?:my\s+)?(?:chat\s+)?(?:with\s+)?([A-Za-z0-9_\s]+)"
            match = re.search(chat_with_pattern, travel_query, re.IGNORECASE)
            
            if match:
                person_name = match.group(1).strip()
                
                self.logger.info({
                    "action": "CHAT_ANALYSIS_REQUEST",
                    "message": f"Request to analyze chat with '{person_name}'",
                    "data": {"user_id": user_id, "person": person_name}
                })
                
                # TODO: Find the chat ID for the specified person
                # This would require additional logic to map person names to chat IDs
                # For now, just use the active chat
                
                # Generate travel plan
                travel_plan = await self._travel_planner.plan_trip(chat_id, travel_query)
                
                # Store in chat history
                if self._chat_history_manager:
                    await self._chat_history_manager.add_message(
                        chat_id, 
                        "user",
                        query,
                        {"source": source, "user_id": user_id}
                    )
                    
                    await self._chat_history_manager.add_message(
                        chat_id,
                        "assistant",
                        travel_plan,
                        {"generated_with": "perplexity_api", "travel_plan": True}
                    )
                
                return travel_plan
                
            else:
                # Regular travel planning request
                travel_plan = await self._travel_planner.plan_trip(chat_id, travel_query)
                
                # Store in chat history
                if self._chat_history_manager:
                    await self._chat_history_manager.add_message(
                        chat_id, 
                        "user",
                        query,
                        {"source": source, "user_id": user_id}
                    )
                    
                    await self._chat_history_manager.add_message(
                        chat_id,
                        "assistant",
                        travel_plan,
                        {"generated_with": "perplexity_api", "travel_plan": True}
                    )
                
                return travel_plan
            
        except Exception as e:
            self.logger.error({
                "action": "TRAVEL_COMMAND_ERROR",
                "message": f"Failed to process travel command: {str(e)}",
                "data": {"error": str(e), "user_id": user_id, "query": query}
            })
            return f"I'm sorry, I couldn't generate a travel plan: {str(e)}"
    
    async def close(self) -> None:
        """
        Properly close the orchestrator and its components.
        
        Ensures all resources are properly released.
        """
        # Close travel planner if initialized
        if self._travel_planner:
            await self._travel_planner.close()
        
        # Close default components
        await super().close()
