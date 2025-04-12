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
        Process a query with smart travel planning awareness.
        
        First analyzes the query to understand if it:
        1. Is travel-related
        2. Requires checking Telegram chat context
        3. Needs real-time information from Perplexity API
        
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
            # Get active chat id for this user
            chat_id = self._active_chats.get(user_id, "default")
            
            # Step 1: Check for explicit travel commands
            if query.strip().startswith(self._travel_command_prefix) or query.strip().startswith("/trip"):
                self.logger.info({
                    "action": "EXPLICIT_TRAVEL_COMMAND",
                    "message": "Processing explicit travel command",
                    "data": {"user_id": user_id, "query": query}
                })
                return await self._handle_travel_command(source, user_id, query, additional_info)
            
            # Step 2: Smart detection - First evaluate if the query is travel-related
            is_travel_query = await self._detect_travel_query(query)
            needs_real_time_info = await self._needs_real_time_info(query)
            
            self.logger.info({
                "action": "QUERY_ANALYSIS",
                "message": "Analyzed user query",
                "data": {
                    "user_id": user_id, 
                    "chat_id": chat_id,
                    "is_travel_query": is_travel_query,
                    "needs_real_time_info": needs_real_time_info
                }
            })
            
            # Step 3: If travel-related and needs real-time info, use Perplexity API
            if is_travel_query and needs_real_time_info:
                self.logger.info({
                    "action": "AUTO_TRAVEL_QUERY",
                    "message": "Automatically handling travel query with Perplexity API",
                    "data": {"user_id": user_id, "chat_id": chat_id}
                })
                
                try:
                    # Generate travel plan with real-time info from Perplexity
                    travel_plan = await self._travel_planner.plan_trip(chat_id, query)
                    
                    # Format the response to indicate it used real-time data
                    formatted_response = f"📍 **Travel Information** (with real-time data)\n\n{travel_plan}"
                    
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
                            formatted_response,
                            {"generated_with": "perplexity_api", "travel_plan": True}
                        )
                    
                    return formatted_response
                    
                except Exception as e:
                    self.logger.error({
                        "action": "AUTO_TRAVEL_ERROR",
                        "message": f"Failed to generate travel plan: {str(e)}",
                        "data": {"error": str(e), "user_id": user_id, "chat_id": chat_id}
                    })
                    # Fall back to default processing if travel planning fails
            
            # Step 4: If travel-related but doesn't need real-time info, or if not travel-related
            # Use default processing with potential Telegram context enhancement
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
        
        Uses a comprehensive set of keywords, patterns, and contextual clues
        to determine if the query is about travel or vacation planning.
        
        Args:
            query: The user query to analyze
            
        Returns:
            bool: True if the query is travel-related
        """
        # List of travel-related keywords and phrases - expanded for better detection
        travel_keywords = [
            "travel to", "trip to", "visit", "vacation", "holiday", "getaway",
            "flight", "hotel", "accommodation", "booking", "itinerary", "lodging",
            "tourist", "tourism", "sightseeing", "attractions", "places to see", "excursion",
            "travel plan", "plan a trip", "weekend getaway", "city break", "road trip",
            "tour", "journey", "expedition", "backpacking", "cruise", "resort",
            "destination", "sightsee", "explore", "adventure", "discover",
            "itinerary", "route", "landmark", "monument", "sightsee", "tour guide",
            "ticket", "reservation", "transit", "transport", "airline", "airport",
            "layover", "stopover", "business trip", "family trip", "holiday package",
            "visa", "passport", "customs", "border", "international", "domestic",
            "check-in", "check-out", "place to stay", "accommodations", "hostel"
        ]
        
        # Destination indicators
        destinations = [
            "beach", "mountain", "island", "city", "country", "continent", "coast",
            "capital", "national park", "resort town", "village", "landmark", "wonder",
            "historical site", "museum", "gallery", "theme park", "safari", "trail"
        ]
        
        # Activity keywords
        activities = [
            "hiking", "swimming", "diving", "snorkeling", "skiing", "snowboarding",
            "surfing", "paragliding", "sightseeing", "shopping", "tasting", "sampling",
            "tour", "guided tour", "self-guided", "cruise", "boat ride", "train journey",
            "road trip", "cycling", "camping", "glamping", "photography", "wildlife",
            "backpacking", "trekking", "walk", "stroll", "visit", "experience"
        ]
        
        # Expanded patterns for trip planning requests
        plan_trip_patterns = [
            r"plan\s+(?:a|my|our|the)\s+(?:trip|vacation|holiday|getaway|visit|journey|tour)",
            r"(?:help|assist)(?:\s+me|\s+us)?\s+(?:plan|arrange|organize|book|prepare|schedule)(?:\s+a|\s+my|\s+our|\s+the)?\s+(?:trip|vacation|holiday|travel|getaway|visit)",
            r"(?:need|looking\s+for|want|seeking)(?:\s+help|\s+assistance|\s+advice)?\s+(?:planning|organizing|arranging|booking|scheduling)(?:\s+a|\s+my|\s+our|\s+the)?\s+(?:trip|vacation|holiday|getaway|travel)",
            r"(?:can|could|would)\s+you\s+(?:plan|suggest|recommend|book|arrange|organize)(?:\s+a|\s+my|\s+our|\s+the)?\s+(?:trip|vacation|holiday|getaway|travel|visit)",
            r"what(?:'s|\s+is|\s+are)\s+(?:the\s+best|good|great|recommended|popular)\s+(?:places?|spots?|locations?|destinations?|attractions?|sites?)\s+(?:to|for)\s+(?:visit|see|explore|experience|travel|vacation)",
            r"where\s+(?:should|can|could)\s+(?:i|we|one|someone)\s+(?:go|travel|visit|stay|lodge|spend)(?:\s+for|\s+during|\s+on|\s+in)?\s+(?:a|my|our|the)?\s+(?:trip|vacation|holiday|weekend|getaway|break)",
            r"(?:i|we)(?:'m|\s+am|\s+are|\s+will\s+be)\s+(?:going|traveling|heading|flying|driving|taking\s+a\s+trip)\s+to\s+([A-Za-z\s]+)(?:\s+and|\s+need|\s+want|\s+would\s+like)\s+(?:recommendations|suggestions|advice|tips|information)"
        ]
        
        # Time-related travel indicators
        time_patterns = [
            r"(?:this|next|coming)\s+(?:weekend|week|month|summer|winter|spring|fall|season)",
            r"(?:in|this|next)\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)",
            r"(?:for|during)\s+(?:\d+)\s+(?:days?|weeks?|nights?|months?)",
            r"(?:from|between)\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+(?:to|and|until|through)\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)"
        ]
        
        # Convert query to lowercase for case-insensitive matching
        query_lower = query.lower()
        
        # Check for travel keywords
        for keyword in travel_keywords:
            if keyword in query_lower:
                return True
                
        # Check for destinations with travel context
        for destination in destinations:
            destination_patterns = [
                f"(?:go|travel|visit|fly|drive)\s+to\s+(?:the\s+)?{destination}",
                f"(?:going|traveling|visiting|flying|driving)\s+to\s+(?:the\s+)?{destination}",
                f"(?:best|top|popular|recommended)\s+{destination}s?\s+to\s+(?:visit|see|explore|experience)",
                f"(?:spend|spending)\s+(?:time|vacation|holiday)\s+(?:at|in|on)\s+(?:the\s+)?{destination}"
            ]
            
            for pattern in destination_patterns:
                if re.search(pattern, query_lower):
                    return True
        
        # Check for activities in travel context
        for activity in activities:
            activity_patterns = [
                f"(?:go|do|try|experience)\s+{activity}\s+(?:in|at|on|during)\s+(?:my|our|the)\s+(?:trip|vacation|holiday|getaway|visit)",
                f"(?:places?|spots?|locations?)\s+(?:for|to)\s+{activity}",
                f"(?:best|top|great|recommended)\s+{activity}\s+(?:in|at|on|near)\s+([A-Za-z\s]+)"
            ]
            
            for pattern in activity_patterns:
                if re.search(pattern, query_lower):
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
    
    async def _needs_real_time_info(self, query: str) -> bool:
        """
        Determine if a query requires real-time information from Perplexity API.
        
        Analyzes the query to check if it would benefit from up-to-date information
        like current travel conditions, recent recommendations, or time-sensitive data.
        
        Args:
            query: The user query to analyze
            
        Returns:
            bool: True if real-time information would be beneficial
        """
        # Keywords indicating need for current/up-to-date information
        real_time_keywords = [
            "current", "latest", "recent", "update", "today", "now", "this week",
            "this month", "this year", "currently", "present", "contemporary",
            "up-to-date", "up to date", "newest", "modern", "happening",
            "trending", "popular", "hot", "recommended", "suggested", "best",
            "top", "highly rated", "well-reviewed", "weather", "forecast",
            "conditions", "situation", "status", "open", "closed", "hours",
            "schedule", "timetable", "prices", "rates", "fees", "cost",
            "availability", "booking", "reservation", "ticket", "entry",
            "event", "festival", "celebration", "holiday", "upcoming"
        ]
        
        # Time-sensitive patterns indicating need for current information
        time_sensitive_patterns = [
            r"(?:this|next|coming|upcoming)\s+(?:week|weekend|month|season)",
            r"(?:right|just)\s+now",
            r"(?:happening|occurring|taking\s+place)\s+(?:now|currently|presently|these days|this time)",
            r"(?:latest|newest|most\s+recent|up-to-date)\s+(?:information|details|news|updates)",
            r"what(?:'s|\s+is)\s+(?:happening|going\s+on|taking\s+place)\s+(?:in|at|during)\s+([A-Za-z\s]+)\s+(?:now|currently|these days|this time|this month|this year|this season)"
        ]
        
        # Patterns for specific real-time information needs
        specific_info_patterns = [
            # Weather patterns
            r"(?:weather|temperature|climate|forecast)\s+(?:in|at|for|during)\s+([A-Za-z\s]+)",
            # Events and happenings
            r"(?:events|shows|performances|exhibitions|festivals|celebrations)\s+(?:in|at|near|around)\s+([A-Za-z\s]+)",
            # Pricing and availability
            r"(?:prices|costs|rates|fees|charges)\s+(?:of|for)\s+(?:tickets|entry|admission|accommodation|hotels|flights)",
            r"(?:availability|bookings|reservations)\s+(?:for|of)\s+(?:rooms|flights|tickets|tours|activities)",
            # Travel conditions
            r"(?:travel|road|flight|transport|transportation)\s+(?:conditions|status|situation|restrictions|advisories|warnings)",
            # Opening times and schedules
            r"(?:opening|closing|operation)\s+(?:times|hours|days|schedule|status)\s+(?:of|for)\s+(?:attractions|sites|museums|parks|places)",
            # Currency exchange and financial info
            r"(?:exchange|conversion)\s+(?:rate|rates|ratio)\s+(?:for|of|between)\s+(?:currency|currencies|cash|money)"
        ]
        
        # Planning complex trips that benefit from up-to-date recommendations
        complex_planning_patterns = [
            r"(?:plan|arrange|organize)\s+(?:a|my|our)\s+(?:complete|comprehensive|detailed|full|entire)\s+(?:trip|itinerary|vacation|holiday|journey|travel)\s+(?:to|in|around|through)\s+([A-Za-z\s]+)",
            r"(?:what|which)\s+(?:are|is)\s+(?:the|some)\s+(?:best|good|recommended|popular|must-see|must-visit|top)\s+(?:places|attractions|spots|sites|destinations|locations|activities|things\s+to\s+do)\s+(?:in|at|near|around)\s+([A-Za-z\s]+)",
            r"(?:help|assist)\s+(?:me|us)\s+(?:create|make|develop|design)\s+(?:a|an|my|our)\s+(?:itinerary|schedule|plan|agenda)\s+(?:for|of)\s+(?:a|my|our)\s+(?:trip|visit|vacation|holiday|stay)\s+(?:to|in|at)\s+([A-Za-z\s]+)"
        ]
        
        # Convert query to lowercase for case-insensitive matching
        query_lower = query.lower()
        
        # Check for real-time keywords
        for keyword in real_time_keywords:
            if keyword in query_lower:
                return True
        
        # Check for time-sensitive patterns
        for pattern in time_sensitive_patterns:
            if re.search(pattern, query_lower):
                return True
        
        # Check for specific real-time information needs
        for pattern in specific_info_patterns:
            if re.search(pattern, query_lower):
                return True
        
        # Check for complex planning patterns that benefit from up-to-date info
        for pattern in complex_planning_patterns:
            if re.search(pattern, query_lower):
                return True
        
        # If query mentions specific countries, cities, or landmarks, it likely needs real-time info
        # This is a simpler heuristic for common destination names
        common_destinations = [
            "paris", "london", "new york", "tokyo", "rome", "barcelona", "sydney",
            "bali", "dubai", "amsterdam", "singapore", "hong kong", "las vegas", "miami",
            "hawaii", "thailand", "greece", "italy", "spain", "france", "japan",
            "australia", "canada", "mexico", "brazil", "peru", "egypt", "morocco",
            "south africa", "india", "china", "russia", "germany", "switzerland",
            "costa rica", "bora bora", "maldives", "fiji", "tahiti", "santorini",
            "venice", "florence", "prague", "vienna", "budapest", "istanbul",
            "jerusalem", "rio de janeiro", "buenos aires", "cancun", "machu picchu",
            "grand canyon", "yellowstone", "disney", "universal studios", "eiffel tower",
            "taj mahal", "great wall", "pyramids", "colosseum", "statue of liberty",
            "goa", "mumbai", "delhi", "bangalore", "jaipur", "agra", "varanasi"
        ]
        
        for destination in common_destinations:
            if destination in query_lower:
                # If a specific destination is mentioned with question about what to do/see
                if any(pattern in query_lower for pattern in ["what to do", "what to see", "where to go", "where to stay", "how to get"]):
                    return True
        
        # By default, don't assume real-time info is needed
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
