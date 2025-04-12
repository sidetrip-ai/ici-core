#!/usr/bin/env python3
"""
Test script for two-stage travel planning:
1. First analyze chat context with LLM to get travel preferences
2. Then use that analysis with Perplexity API for detailed itineraries
"""

import os
import asyncio
import json
from ici.adapters.external_services.perplexity_api import PerplexityAPI
from ici.adapters.loggers import StructuredLogger
from ici.utils.config import get_component_config

# Configure logging
logger = StructuredLogger("two_stage_travel")

async def get_llm_analysis(mock_chat_data):
    """
    Simulate the LLM analyzing chat context for travel preferences.
    In the real system, this would use the actual LLM.
    """
    print("\n=== STAGE 1: LLM Analysis of Chat Context ===")
    print(f"Analyzing mock chat data: {mock_chat_data}")
    
    # In a real implementation, this would call the LLM
    # Here we're mocking the LLM's response
    analysis = f"""
DESTINATION: {mock_chat_data['preferred_destination']}
ITINERARY TYPE: {mock_chat_data['traveler_type']}
DURATION: {mock_chat_data['duration']}
"""
    print("\n=== LLM Analysis Result ===")
    print(analysis)
    return analysis

async def get_perplexity_itinerary(llm_analysis):
    """
    Use Perplexity API to generate a detailed itinerary based on LLM analysis.
    """
    print("\n=== STAGE 2: Perplexity API Detailed Itinerary ===")
    print("Passing LLM analysis to Perplexity API...")
    
    # Initialize Perplexity API
    perplexity_api = PerplexityAPI()
    await perplexity_api.initialize()
    
    try:
        # Convert LLM analysis to a detailed travel query
        travel_query = f"Create a detailed travel itinerary based on this analysis: {llm_analysis}"
        
        # Get detailed itinerary from Perplexity
        itinerary = await perplexity_api.plan_travel("default", travel_query)
        
        print("\n=== Perplexity Detailed Itinerary ===")
        print(itinerary)
        
        return itinerary
    finally:
        # Clean up
        await perplexity_api.close()

async def main():
    """Main entry point for the two-stage travel planning process."""
    # These would normally come from Telegram chat data
    # In this mock version, we'll use predefined examples
    mock_chat_samples = [
        {
            "name": "Luxury Beach Vacation",
            "chat_data": {
                "preferred_destination": "Maldives",
                "traveler_type": "luxury",
                "duration": "7 days",
                "special_interests": "snorkeling, spa, fine dining"
            }
        },
        {
            "name": "Adventure Mountain Trip",
            "chat_data": {
                "preferred_destination": "Swiss Alps",
                "traveler_type": "adventure",
                "duration": "10 days",
                "special_interests": "hiking, skiing, mountain views"
            }
        },
        {
            "name": "Cultural City Exploration",
            "chat_data": {
                "preferred_destination": "Kyoto, Japan",
                "traveler_type": "cultural",
                "duration": "5 days",
                "special_interests": "temples, traditional food, tea ceremonies"
            }
        }
    ]
    
    # Let user select a mock chat to use
    print("Available mock chat examples:")
    for i, sample in enumerate(mock_chat_samples):
        print(f"{i+1}. {sample['name']}")
    
    selection = input("\nSelect a mock chat example (1-3) or type 'custom' to create your own: ")
    
    if selection.lower() == 'custom':
        # Allow user to input custom preferences
        destination = input("Enter preferred destination: ")
        traveler_type = input("Enter traveler type (luxury, adventure, budget, family, etc.): ")
        duration = input("Enter trip duration: ")
        interests = input("Enter special interests (comma separated): ")
        
        mock_chat_data = {
            "preferred_destination": destination,
            "traveler_type": traveler_type,
            "duration": duration,
            "special_interests": interests
        }
    else:
        try:
            # Use selected mock chat
            index = int(selection) - 1
            mock_chat_data = mock_chat_samples[index]["chat_data"]
        except (ValueError, IndexError):
            print("Invalid selection. Using default example.")
            mock_chat_data = mock_chat_samples[0]["chat_data"]
    
    # Stage 1: Get LLM analysis of chat data
    llm_analysis = await get_llm_analysis(mock_chat_data)
    
    # Stage 2: Get detailed itinerary from Perplexity API
    await get_perplexity_itinerary(llm_analysis)

if __name__ == "__main__":
    asyncio.run(main())
