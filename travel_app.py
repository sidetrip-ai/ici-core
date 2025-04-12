#!/usr/bin/env python3
"""
Streamlit web app for Perplexity API Travel Planning with Chat Context
"""

import os
import asyncio
import json
import yaml
import streamlit as st
from datetime import datetime
from ici.adapters.external_services.perplexity_api import PerplexityAPI
from ici.adapters.loggers import StructuredLogger

# Configure page 
st.set_page_config(
    page_title="CryptoTravel AI",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Apply custom CSS for a tech-savvy, minimalist look
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
        color: #ffffff;
    }
    .stTextInput > div > div > input {
        background-color: #262730;
        color: #ffffff;
        border-radius: 5px;
        border: 1px solid #4a4a4a;
        padding: 12px;
    }
    .stButton > button {
        background-color: #3d85c6;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 10px 24px;
        font-weight: bold;
    }
    .response-container {
        background-color: #1e2130;
        border-radius: 8px;
        padding: 20px;
        margin-top: 20px;
        border: 1px solid #3d4456;
    }
    h1, h2, h3 {
        color: #3d85c6;
    }
    .crypto-accent {
        color: #3d85c6;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Function to get chat context
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
    
    # Convert fake chat to readable context
    context = "\nTelegram Chat History:\n\n"
    for message in fake_chat:
        context += f"[{message['timestamp']}] {message['sender']}: {message['message']}\n"
    
    return context

# Function to call Perplexity API asynchronously
async def get_travel_plan(user_input, chat_context):
    """Get travel plan from Perplexity API"""
    logger = StructuredLogger("streamlit_app")
    
    # Initialize API
    perplexity_api = PerplexityAPI()
    await perplexity_api.initialize()
    
    try:
        # Create the combined query
        combined_query = f"{user_input}\n\n{chat_context}\n\nPlease include:\n"
        combined_query += """1. Accommodation options near Madinat Jumeirah (venue for Token 2049)
2. Transportation recommendations
3. Crypto/Web3 related side events or meetups
4. Dubai attractions for a tech enthusiast
5. Restaurant recommendations
6. A 5-day itinerary that balances conference attendance and exploration"""
        
        # Call the API with chat context
        result = await perplexity_api.plan_travel(chat_context, combined_query)
        
        # Clean up
        await perplexity_api.close()
        
        return result
    except Exception as e:
        await perplexity_api.close()
        return f"Error: {str(e)}"

# Function to run async code in Streamlit
def run_async(func):
    """Run an async function to completion in Streamlit"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(func)
    finally:
        loop.close()

# App header
st.title("✈️ CryptoTravel AI")
st.markdown("<p style='font-size: 18px;'>Smart travel planning for crypto conferences & events</p>", unsafe_allow_html=True)

# App interface
st.markdown("### 📱 Telegram Context")
with st.expander("View Telegram Chat Context"):
    chat_context = get_chat_context()
    for line in chat_context.split('\n'):
        if 'Prakhar:' in line:
            st.markdown(f"<div style='text-align: right; margin-bottom: 8px;'><span style='background-color: #3d85c6; padding: 6px 12px; border-radius: 15px;'>{line}</span></div>", unsafe_allow_html=True)
        elif 'Friend:' in line:
            st.markdown(f"<div style='text-align: left; margin-bottom: 8px;'><span style='background-color: #333333; padding: 6px 12px; border-radius: 15px;'>{line}</span></div>", unsafe_allow_html=True)
        else:
            st.text(line)

# Input area
st.markdown("### 🔍 Create Travel Plan")
user_input = st.text_area("Enter your travel planning request:", 
                         value="Based on my conversation with Prakhar, create a detailed travel plan for his Token 2049 conference in Dubai", 
                         height=100,
                         key="user_input")

if st.button("Generate Travel Plan", key="generate_button"):
    with st.spinner("Getting real-time travel information..."):
        # Show typing indicator
        progress_bar = st.progress(0)
        for i in range(100):
            # Update progress bar
            progress_bar.progress(i + 1)
            # Add a slight delay for effect
            import time
            time.sleep(0.02)
            
        # Get the travel plan
        travel_plan = run_async(lambda: get_travel_plan(user_input, chat_context))
        
        # Display result in a nice formatted container
        st.markdown("<div class='response-container'>", unsafe_allow_html=True)
        st.markdown("### 🌟 Travel Plan")
        st.markdown(travel_plan)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Add a "Copy to Clipboard" button
        st.button("Copy to Clipboard", key="copy_button")

# Footer
st.markdown("---")
st.markdown("<p style='text-align: center; color: #666666;'>Powered by Perplexity API | CryptoTravel AI</p>", unsafe_allow_html=True)
