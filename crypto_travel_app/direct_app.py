#!/usr/bin/env python3
"""
Side Trip - Planning Your Next Side Trip - Flask backend implementation
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Use the confirmed working API key
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "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")

def get_chat_context():
    """
    Generate Telegram chat context about Prakhar discussing Token 2049 event in Dubai.
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
    
    # Return the raw chat data for frontend processing
    return fake_chat

def format_chat_context(chat_data):
    """Format chat data into text format for API"""
    context = "Telegram Chat History:\n\n"
    for message in chat_data:
        context += f"[{message['timestamp']}] {message['sender']}: {message['message']}\n"
    return context

# Direct Perplexity API implementation
async def call_perplexity_api(query):
    """Call Perplexity API directly using aiohttp"""
    url = "https://api.perplexity.ai/chat/completions"
    
    # API payload matching the format that works in test_perplexity.py
    payload = {
        "model": "sonar",  # Using sonar model with web search capability
        "messages": [
            {
                "role": "system",
                "content": "You are a travel planning expert with access to real-time information through web search. Create detailed, actionable travel plans with practical information."
            },
            {
                "role": "user",
                "content": query
            }
        ],
        "max_tokens": 2000,  # Increased token limit for detailed plans
        "temperature": 0.7,  # Balanced creativity
        "presence_penalty": 0,
        "frequency_penalty": 0
    }
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("choices", [{}])[0].get("message", {}).get("content", "No results found")
                else:
                    error_text = await response.text()
                    print(f"API Error Response: {error_text}")
                    return f"API Error ({response.status}): Unable to get travel plan. Please check your API key and try again."
    except Exception as e:
        print(f"Exception details: {str(e)}")
        return f"Error calling Perplexity API: {str(e)}"

async def get_travel_plan(user_input, chat_context_text):
    """Get travel plan based on user input and chat context"""
    try:
        # Use the exact user input as provided
        if not user_input.strip():
            user_input = "Please help plan a trip based on the chat conversation"
            
        # Create the combined query with the user's input
        combined_query = f"{user_input}\n\n{chat_context_text}\n\nPlease include:\n"
        combined_query += """1. Accommodation options near Madinat Jumeirah (venue for Token 2049)
2. Transportation recommendations
3. Crypto/Web3 related side events or meetups
4. Dubai attractions for a tech enthusiast
5. Restaurant recommendations
6. A 5-day itinerary that balances conference attendance and exploration"""
        
        # Call the API directly
        result = await call_perplexity_api(combined_query)
        
        return {"success": True, "travel_plan": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/api/chat-context')
def api_chat_context():
    """API endpoint to get chat context"""
    return jsonify(get_chat_context())

@app.route('/api/travel-plan', methods=['POST'])
def api_travel_plan():
    """API endpoint to get travel plan"""
    data = request.json
    user_input = data.get('user_input', '')
    
    # Get chat context
    chat_data = get_chat_context()
    chat_context_text = format_chat_context(chat_data)
    
    # Run async function with event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(get_travel_plan(user_input, chat_context_text))
        return jsonify(result)
    finally:
        loop.close()

if __name__ == '__main__':
    print("Starting Side Trip - Planning Your Next Side Trip...")
    print("Open http://127.0.0.1:5001 in your browser")
    app.run(debug=True, port=5001)
