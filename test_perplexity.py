#!/usr/bin/env python3
"""
Simple test script for Perplexity API integration without Telegram dependencies.
"""

import os
import asyncio
import json
import yaml
from ici.adapters.external_services.perplexity_api import PerplexityAPI
from ici.adapters.loggers import StructuredLogger
from ici.utils.config import get_component_config

async def test_perplexity_api():
    """Test Perplexity API directly without any Telegram chat context."""
    # Setup logger
    logger = StructuredLogger("perplexity_test")
    
    # Initialize API
    perplexity_api = PerplexityAPI()
    await perplexity_api.initialize()
    
    # Sample travel query
    query = input("Enter your travel query: ")
    
    print(f"\nProcessing query: {query}\n")
    
    # Empty chat context since we're bypassing Telegram
    chat_context = "Previous conversation: This is a new conversation about travel."
    
    try:
        # Directly call the API
        result = await perplexity_api.plan_travel(chat_context, query)
        
        print("\n---- TRAVEL PLAN RESULT ----\n")
        print(result)
        print("\n---------------------------\n")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    
    # Clean up
    await perplexity_api.close()

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_perplexity_api())
