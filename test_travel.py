#!/usr/bin/env python3
"""
Test script for the travel command functionality.
Bypasses Telegram data fetching to focus on testing the /travel command.
"""

import os
import sys
import asyncio
from typing import Dict, Any

# Add the current directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Load environment variables from .env file
try:
    from ici.utils.load_env import load_env
    load_env()
except ImportError as e:
    print(f"Warning: Could not load environment variables: {e}")

from ici.adapters.orchestrators.travel_orchestrator import TravelOrchestrator
from ici.adapters.loggers import StructuredLogger

logger = StructuredLogger(name="test_travel")

class SimplifiedTravelOrchestrator(TravelOrchestrator):
    """Modified TravelOrchestrator that skips Telegram initialization"""
    
    async def initialize(self) -> None:
        """Initialize only essential components, skipping Telegram"""
        self.logger.info({
            "action": "TRAVEL_ORCHESTRATOR_INIT_START",
            "message": "Initializing SimplifiedTravelOrchestrator (without Telegram)"
        })
        
        # Set initialized flag to prevent errors
        self._is_initialized = True
        
        # Initialize only the travel planner (which will initialize Perplexity API)
        self._travel_planner = self._create_travel_planner()
        await self._travel_planner.initialize()
        
        self.logger.info({
            "action": "TRAVEL_ORCHESTRATOR_INIT_SUCCESS",
            "message": "SimplifiedTravelOrchestrator initialized successfully"
        })
    
    def _create_travel_planner(self):
        """Create a TravelPlanner instance that skips Telegram initialization"""
        from ici.adapters.external_services.travel_planner import TravelPlanner
        
        # Create a modified TravelPlanner instance
        return TravelPlanner(logger_name="travel_planner")
    
    async def process_query(self, source: str, user_id: str, query: str, additional_info: Dict[str, Any]) -> str:
        """Process travel queries directly without additional checks"""
        if query.startswith("/travel ") or query.startswith("/trip "):
            # Extract the actual query from the command
            command_parts = query.strip().split(maxsplit=1)
            if len(command_parts) == 1:
                return "Please provide a travel request after the /travel command"
            
            travel_query = command_parts[1]
            
            # Force the travel_query to not include the command prefix
            if travel_query.startswith("/travel ") or travel_query.startswith("/trip "):
                travel_query = travel_query.split(maxsplit=1)[1]
            
            # Get active chat id
            chat_id = "test_chat"
            
            try:
                # Generate travel plan directly using the travel planner
                travel_plan = await self._travel_planner.plan_trip(chat_id, travel_query)
                return travel_plan
            except Exception as e:
                self.logger.error({
                    "action": "TEST_TRAVEL_ERROR",
                    "message": f"Failed to process travel query: {str(e)}",
                    "data": {"error": str(e), "query": query}
                })
                return f"Error processing travel query: {str(e)}"
        else:
            return "Please use the /travel command followed by your travel request"

async def test_travel_command():
    """Run a simplified test of the travel command"""
    print("\n=== TRAVEL COMMAND TESTER ===\n")
    print("This script bypasses Telegram to test the /travel command\n")
    
    # Initialize the simplified orchestrator
    orchestrator = SimplifiedTravelOrchestrator()
    await orchestrator.initialize()
    
    print("Orchestrator initialized. Enter /travel queries or 'exit' to quit.\n")
    
    while True:
        try:
            # Get user input
            user_input = input("> ")
            
            # Check for exit command
            if user_input.lower() in ["exit", "quit"]:
                break
                
            print("Processing your travel query...")
            
            # Process the query
            response = await orchestrator.process_query(
                source="test",
                user_id="test_user",
                query=user_input,
                additional_info={}
            )
            
            print("\nResponse:")
            print(response)
            print("\n" + "-" * 80 + "\n")
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {str(e)}")
    
    # Clean up
    await orchestrator.close()
    print("Test completed.")

if __name__ == "__main__":
    asyncio.run(test_travel_command())
