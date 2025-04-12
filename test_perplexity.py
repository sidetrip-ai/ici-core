#!/usr/bin/env python3
"""
Test script for Perplexity API integration with Telegram chat context.
"""

import os
import asyncio
import json
import yaml
from datetime import datetime
from ici.adapters.external_services.perplexity_api import PerplexityAPI
from ici.adapters.loggers import StructuredLogger
from ici.utils.config import get_component_config

def get_fake_chat_context():
    """
    Generate  Telegram chat context about Prakhar discussing Token 2049 event in Dubai.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    fake_chat = [
        {
            "timestamp": f"{today} 10:15:23",
            "sender": "Prakhar",
            "message": "Hey, have you heard about Token 2049 happening in Dubai?"
        },
        {
            "timestamp": f"{today} 10:16:05",
            "sender": "Friend",
            "message": "Yeah, it's one of the biggest crypto conferences. Are you going?"
        },
        {
            "timestamp": f"{today} 10:17:30",
            "sender": "Prakhar",
            "message": "Definitely! I just got my ticket. It's happening on April 30th and May 1st."
        },
        {
            "timestamp": f"{today} 10:18:45",
            "sender": "Friend",
            "message": "That's awesome! Have you booked your accommodation yet?"
        },
        {
            "timestamp": f"{today} 10:20:12",
            "sender": "Prakhar",
            "message": "Not yet. I need to figure out where to stay. Preferably somewhere close to the conference venue."
        },
        {
            "timestamp": f"{today} 10:21:33",
            "sender": "Friend",
            "message": "I heard it's being held at Madinat Jumeirah. You might want to look for hotels in that area."
        },
        {
            "timestamp": f"{today} 10:23:05",
            "sender": "Prakhar",
            "message": "Thanks for the tip! I'm also interested in checking out some good restaurants and maybe doing some sightseeing while I'm there."
        },
        {
            "timestamp": f"{today} 10:24:17",
            "sender": "Friend",
            "message": "Dubai has amazing restaurants and attractions. Burj Khalifa is a must-visit!"
        },
        {
            "timestamp": f"{today} 10:25:40",
            "sender": "Prakhar",
            "message": "Perfect! I'll probably stay for about 5 days in total to have time for both the conference and exploring the city."
        }
    ]
    
    # Convert fake chat to readable context
    context = "\nTelegram Chat History:\n\n"
    for message in fake_chat:
        context += f"[{message['timestamp']}] {message['sender']}: {message['message']}\n"
    
    return context

async def test_perplexity_api():
    """Test Perplexity API with Telegram chat context about Token 2049 in Dubai."""
    # Setup logger
    logger = StructuredLogger("perplexity_test")
    
    # Initialize API
    perplexity_api = PerplexityAPI()
    await perplexity_api.initialize()
    
    # Get fake chat context
    chat_context = get_fake_chat_context()
    print("\n==== FAKE TELEGRAM CHAT CONTEXT ====\n")
    print(chat_context)
    
    # Get user input first
    print("\n==== ENTER YOUR TRAVEL PLANNING REQUEST ====\n")
    user_request = input("> ")
    
    if not user_request.strip():
        user_request = "Below is my convo with my friend Prakhar. Generate a travel plan for him"
    
    # Create the combined query in exactly the format requested
    combined_query = f"{user_request}\n\n{chat_context}\n\nPlease include:\n"
    combined_query += """1. Accommodation options near Madinat Jumeirah (venue for Token 2049)
2. Transportation recommendations
3. Crypto/Web3 related side events or meetups
4. Dubai attractions for a tech enthusiast
5. Restaurant recommendations
6. A 5-day itinerary that balances conference attendance and exploration"""
    
    # Use this as the query
    query = combined_query
    
    print(f"\nProcessing query with chat context: {query}\n")
    
    try:
        # Call the API with chat context
        result = await perplexity_api.plan_travel(chat_context, query)
        
        print("\n==== TRAVEL PLAN RESULT ====\n")
        print(result)
        print("\n============================\n")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    
    # Clean up
    await perplexity_api.close()

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_perplexity_api())
