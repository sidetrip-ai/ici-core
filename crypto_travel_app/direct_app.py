#!/usr/bin/env python3
"""
Side Trip - Planning Your Next Side Trip - Flask backend implementation
"""

import os
import json
import asyncio
import aiohttp
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# API keys
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY", "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")
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "044317b1-21ac-402f-9b65-1d98a3dcf2fd")

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

def get_email_history():
    """
    Generate fake email history for Prakhar's past hotel stays and travel bookings.
    """
    # Last year
    past_date = datetime.now().replace(year=datetime.now().year - 1)
    past_year = past_date.year
    
    fake_emails = [
        {
            "date": f"{past_year}-03-15",
            "subject": "Your Reservation at Marriott Hotel Singapore",
            "sender": "reservations@marriott.com",
            "recipient": "prakhar@gmail.com",
            "content": f"Dear Prakhar,\n\nThank you for choosing Marriott Hotel Singapore for your stay from {past_year}-03-25 to {past_year}-03-29. Your reservation details:\n\nRoom Type: Deluxe King Room\nRate: $280 per night\nTotal: $1,120 (4 nights)\n\nYour reservation includes complimentary breakfast and WiFi.\n\nWe look forward to welcoming you!\n\nMarriott Hotels"
        },
        {
            "date": f"{past_year}-04-20",
            "subject": "E-Ticket Confirmation: Singapore Airlines",
            "sender": "no-reply@singaporeair.com",
            "recipient": "prakhar@gmail.com",
            "content": f"Dear Prakhar,\n\nThank you for booking with Singapore Airlines. Your e-ticket details:\n\nFlight: SQ421\nFrom: Delhi (DEL) to Singapore (SIN)\nDate: {past_year}-03-24\nDeparture: 21:15\nClass: Business\nTicket Price: $2,450\n\nReturn:\nFlight: SQ422\nFrom: Singapore (SIN) to Delhi (DEL)\nDate: {past_year}-03-30\nDeparture: 07:45\nClass: Business\n\nWe wish you a pleasant journey!\n\nSingapore Airlines"
        },
        {
            "date": f"{past_year}-09-10",
            "subject": "Your Stay at Hilton London",
            "sender": "reservations@hilton.com",
            "recipient": "prakhar@gmail.com",
            "content": f"Dear Prakhar,\n\nThank you for your recent stay at Hilton London from {past_year}-09-02 to {past_year}-09-06. We hope you enjoyed your time with us.\n\nYour final bill details:\n\nRoom: Executive Suite\nRate: £340 per night\nRoom Service: £75\nSpa Services: £120\nTotal Charged: £1,555\n\nWe hope to welcome you back soon!\n\nHilton Hotels"
        },
        {
            "date": f"{past_year}-11-25",
            "subject": "Confirmation: Crypto Conference Miami",
            "sender": "registration@cryptoconf.com",
            "recipient": "prakhar@gmail.com",
            "content": f"Dear Prakhar,\n\nThank you for registering for Crypto Conference Miami {past_year}.\n\nDates: {past_year}-12-05 to {past_year}-12-07\nVenue: Miami Convention Center\nTicket Type: VIP Pass\nAmount Paid: $1,899\n\nYour VIP pass includes access to all keynotes, workshops, VIP networking events, and the exclusive afterparty.\n\nLooking forward to seeing you there!\n\nCrypto Conference Team"
        },
        {
            "date": f"{past_year}-12-01",
            "subject": "Your Reservation: W South Beach Hotel",
            "sender": "reservations@whotels.com",
            "recipient": "prakhar@gmail.com",
            "content": f"Dear Prakhar,\n\nYour reservation at W South Beach is confirmed for {past_year}-12-04 to {past_year}-12-08.\n\nRoom: Ocean View Suite\nRate: $495 per night\nTotal: $1,980 (4 nights)\n\nWe've noted your preferences for a high floor and early check-in. Our concierge will be in touch to arrange airport transportation.\n\nWe look forward to providing you with an exceptional experience!\n\nW Hotels"
        }
    ]
    
    return fake_emails

def summarize_email_history():
    """
    Create a summary of Prakhar's email history for use in travel planning.
    """
    emails = get_email_history()
    
    summary = "Email History Summary:\n\n"
    
    # Extract key information from emails
    summary += "Past Hotel Stays:\n"
    summary += "1. Marriott Hotel Singapore - Deluxe King Room at $280/night (4 nights) with breakfast included\n"
    summary += "2. Hilton London - Executive Suite at £340/night, spent additional £195 on room service and spa\n"
    summary += "3. W South Beach Miami - Ocean View Suite at $495/night (4 nights) with high floor preference\n\n"
    
    summary += "Travel Budget/Style:\n"
    summary += "1. Typically flies Business Class (paid $2,450 for Singapore Airlines round trip)\n"
    summary += "2. Prefers upscale hotels ($280-$495 per night range)\n"
    summary += "3. Attends premium conferences (paid $1,899 for VIP Pass to Crypto Conference Miami)\n"
    summary += "4. Enjoys hotels with amenities like spa services\n"
    summary += "5. Often requests early check-in and high floors\n"
    
    return summary

def format_chat_context(chat_data):
    """Format chat data into text format for API"""
    context = "Telegram Chat History:\n\n"
    for message in chat_data:
        context += f"[{message['timestamp']}] {message['sender']}: {message['message']}\n"
    return context

def get_combined_context():
    """Combine chat history with email summary for a more complete context"""
    chat_data = get_chat_context()
    chat_context = format_chat_context(chat_data)
    email_summary = summarize_email_history()
    
    # Combine both data sources
    combined_context = f"{chat_context}\n\n{email_summary}"
    return chat_data, combined_context

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

async def get_travel_plan(user_input, context_text):
    """Get travel plan based on user input and combined context (chat + email)"""
    try:
        # Use the exact user input as provided
        if not user_input.strip():
            user_input = "Please help plan a trip based on the conversation and email history"
            
        # Create the combined query with the user's input
        combined_query = f"{user_input}\n\n{context_text}\n\nPlease include:\n"
        combined_query += """1. Accommodation options near Madinat Jumeirah (venue for Token 2049) that match Prakhar's budget and preferences based on his past hotel stays
2. Transportation recommendations considering his typical travel style
3. Crypto/Web3 related side events or meetups
4. Dubai attractions for a tech enthusiast
5. Restaurant recommendations
6. A 5-day itinerary that balances conference attendance and exploration

Format the travel plan with clear day-wise sections using headings and bullet points. Keep the language concise and structured for easy reading on a website."""
        
        # Call the API directly
        result = await call_perplexity_api(combined_query)
        
        return {"success": True, "travel_plan": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.route('/')
def splash():
    """Render the splash page"""
    return render_template('splash.html')

@app.route('/app')
def index():
    """Render the main app page"""
    return render_template('index.html')

@app.route('/api/chat-context')
def api_chat_context():
    """API endpoint to get chat context"""
    chat_data, _ = get_combined_context()
    return jsonify(chat_data)

@app.route('/api/email-context')
def api_email_context():
    """API endpoint to get email context"""
    return jsonify(get_email_history())

@app.route('/api/travel-plan', methods=['POST'])
def api_travel_plan():
    """API endpoint to get travel plan using combined chat and email data"""
    data = request.json
    user_input = data.get('user_input', '')
    
    # Get combined context data
    _, combined_context = get_combined_context()
    
    # Run async function with event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(get_travel_plan(user_input, combined_context))
        return jsonify(result)
    finally:
        loop.close()

@app.route('/api/speech-to-text', methods=['POST'])
def speech_to_text():
    """API endpoint for speech-to-text conversion using Sarvam ASR"""
    if 'audio' not in request.files:
        return jsonify({'success': False, 'error': 'No audio file provided'})
    
    audio_file = request.files['audio']
    
    # Prepare request to Sarvam API
    sarvam_url = "https://api.sarvam.ai/speech-to-text"
    headers = {
        "api-subscription-key": SARVAM_API_KEY
    }
    
    # Set up parameters for English language
    files = {
        'file': (audio_file.filename, audio_file.read(), audio_file.content_type)
    }
    data = {
        'language_code': 'en-IN',  # English language
        'model': 'saarika:v2',     # Using the latest model
        'with_timestamps': False    # No need for timestamps
    }
    
    try:
        # Make request to Sarvam API
        response = requests.post(sarvam_url, headers=headers, files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'success': True,
                'transcript': result.get('transcript', '')
            })
        else:
            return jsonify({
                'success': False,
                'error': f'API Error: {response.status_code}',
                'details': response.text
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error processing speech: {str(e)}'
        })

if __name__ == '__main__':
    print("Starting Side Trip - Planning Your Next Side Trip...")
    print("Open http://127.0.0.1:5002 in your browser")
    app.run(debug=True, port=5002)
