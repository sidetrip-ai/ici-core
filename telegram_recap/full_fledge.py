# import os
# import json
# import yaml
# from datetime import datetime
# import requests
# from collections import Counter
# from wordcloud import WordCloud
# import matplotlib.pyplot as plt
# import pandas as pd
# import base64
# from PIL import Image
# import io
# import time

# # Load config
# with open("config.yaml", "r") as f:
#     config = yaml.safe_load(f)

# def load_sample_data():
#     """Load sample Telegram data or your actual data"""
#     sample_data = {
#         "chats": {
#             "list": [
#                 {
#                     "name": "Family Group",
#                     "messages": [
#                         {
#                             "date": str(datetime.now()),
#                             "from": "Mom",
#                             "text": "How are you doing?"
#                         },
#                         {
#                             "date": str(datetime.now()),
#                             "from": "You",
#                             "text": "I'm good, working on a new project!"
#                         }
#                     ]
#                 },
#                 {
#                     "name": "Work Chat",
#                     "messages": [
#                         {
#                             "date": str(datetime.now()),
#                             "from": "Colleague",
#                             "text": "Did you see the latest requirements?"
#                         }
#                     ]
#                 }
#             ]
#         }
#     }
    
#     # Save sample data
#     os.makedirs("data", exist_ok=True)
#     with open("data/telegram_dump.json", "w") as f:
#         json.dump(sample_data, f)
    
#     return sample_data

# def analyze_data(data):
#     """Perform analytics on the Telegram data"""
#     messages = []
#     for chat in data.get("chats", {}).get("list", []):
#         for msg in chat.get("messages", []):
#             if isinstance(msg.get("text"), str) and msg.get("text").strip():
#                 messages.append({
#                     "timestamp": msg["date"],
#                     "sender": msg.get("from", "Unknown"),
#                     "content": msg["text"]
#                 })
    
#     # Basic analytics
#     senders = [msg["sender"] for msg in messages]
#     top_contacts = Counter(senders).most_common(5)
    
#     # Word cloud
#     all_text = " ".join([msg["content"] for msg in messages if msg["content"]])
#     wordcloud = WordCloud(width=800, height=400, background_color="white").generate(all_text)
    
#     os.makedirs("visuals", exist_ok=True)
#     plt.figure(figsize=(10, 5))
#     plt.imshow(wordcloud, interpolation='bilinear')
#     plt.axis("off")
#     plt.savefig("visuals/wordcloud.png")
#     plt.close()
    
#     # Prepare recap data
#     recap_data = {
#         "top_contacts": {contact: count for contact, count in top_contacts},
#         "total_messages": len(messages),
#         "top_words": [word for word, _ in wordcloud.words_.items()][:5]
#     }
    
#     return recap_data


# def generate_recap(recap_data):
#     """Use OpenAI to generate a natural language recap"""
#     # Get API key from config or environment
#     api_key = config.get("openai", {}).get("api_key") or os.getenv("OPENAI_API_KEY") or "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"

#     if not api_key:
#         print("Error: OPENAI_API_KEY not found in environment variables or config")
#         return
    
#     prompt = f"""
#     Analyze this Telegram chat data and provide a concise, friendly recap:
    
#     {json.dumps(recap_data, indent=2)}
    
#     Include:
#     - Who the user talked to most
#     - Any interesting patterns
#     - A general sentiment analysis
#     - Key topics discussed
#     """
    
#     try:
#         response = requests.post(
#             "https://api.openai.com/v1/chat/completions",
#             headers={
#                 "Authorization": f"Bearer {api_key}",
#                 "Content-Type": "application/json"
#             },
#             json={
#                 "model": config["generator"]["model"],
#                 "messages": [{
#                     "role": "system",
#                     "content": "You are a helpful data analyst that provides clear insights from chat data."
#                 }, {
#                     "role": "user",
#                     "content": prompt
#                 }],
#                 "temperature": config["generator"]["default_options"]["temperature"],
#                 "max_tokens": config["generator"]["default_options"]["max_tokens"]
#             }
#         )
        
#         if response.status_code == 200:
#             return response.json()["choices"][0]["message"]["content"]
#         else:
#             print(f"API Error: {response.status_code} - {response.text}")
#             return None
#     except Exception as e:
#         print(f"Error calling OpenAI API: {str(e)}")
#         return None

# def generate_infographic_with_gpt4(recap_text, recap_data):
#     """Generate an infographic using GPT-4 image generation"""
#     # Get API key from config or environment
#     api_key = "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"

#     if not api_key:
#         print("Error: OPENAI_API_KEY not found in environment variables or config")
#         return None
    
#     # Create a prompt for the image generation
#     image_prompt = f"""
#     Create a visually appealing infographic visualizing Telegram chat data with the following information:
    
#     Total Messages: {recap_data['total_messages']}
    
#     Top Contacts:
#     {', '.join([f"{contact} ({count} messages)" for contact, count in recap_data['top_contacts'].items()][:3])}
    
#     Top Words Used:
#     {', '.join(recap_data['top_words'][:5])}
    
#     Key Insights:
#     {recap_text[:500] if recap_text else "No insights available"}
    
#     Style: Modern, clean design with Telegram-themed color palette (blue and white), data visualizations 
#     including bar charts for top contacts, and a visual word cloud. Include the Telegram logo.
#     """
    
#     try:
#         print("\nGenerating infographic with GPT-4...")
#         response = requests.post(
#             "https://api.openai.com/v1/images/generations",
#             headers={
#                 "Authorization": f"Bearer {api_key}",
#                 "Content-Type": "application/json"
#             },
#             json={
#                 "model": "dall-e-3",  # Using DALL-E 3 model for image generation
#                 "prompt": image_prompt,
#                 "n": 1,
#                 "size": "1024x1024",
#                 "response_format": "b64_json"
#             }
#         )
        
#         if response.status_code == 200:
#             print("Infographic generated successfully with GPT-4!")
#             image_data = response.json()["data"][0]["b64_json"]
            
#             # Save the image
#             image_bytes = base64.b64decode(image_data)
#             image = Image.open(io.BytesIO(image_bytes))
            
#             os.makedirs("visuals", exist_ok=True)
#             image_path = "visuals/telegram_infographic.png"
#             image.save(image_path)
            
#             return image_path
#         else:
#             print(f"GPT-4 Image API Error: {response.status_code} - {response.text}")
#             return None
#     except Exception as e:
#         print(f"Error calling GPT-4 Image API: {str(e)}")
#         return None

# def generate_infographic_with_gemini(recap_text, recap_data):
#     """Generate an infographic using Google's Gemini (fallback)"""
#     # Get API key from config or environment
#     api_key = "AIzaSyBR757nka3dmzBcH4FMze7IstXGWna6y0M"
    
#     if not api_key:
#         print("Error: GEMINI_API_KEY not found in environment variables or config")
#         return None
    
#     # Create a prompt for the image generation
#     image_prompt = f"""
#     Create a visually appealing infographic visualizing Telegram chat data with the following information:
    
#     Total Messages: {recap_data['total_messages']}
    
#     Top Contacts:
#     {', '.join([f"{contact} ({count} messages)" for contact, count in recap_data['top_contacts'].items()][:3])}
    
#     Top Words Used:
#     {', '.join(recap_data['top_words'][:5])}
    
#     Key Insights:
#     {recap_text[:500] if recap_text else "No insights available"}
    
#     Style: Modern, clean design with Telegram-themed color palette (blue and white), data visualizations 
#     including bar charts for top contacts, and a visual word cloud. Include the Telegram logo.
#     """
    
#     try:
#         print("\nFalling back to Gemini Flash for infographic generation...")
#         response = requests.post(
#             f"https://generativelanguage.googleapis.com/v1/models/gemini-pro-vision:generateContent?key={api_key}",
#             headers={"Content-Type": "application/json"},
#             json={
#                 "contents": [{
#                     "role": "user",
#                     "parts": [{
#                         "text": image_prompt
#                     }]
#                 }],
#                 "generationConfig": {
#                     "temperature": 0.7,
#                     "topK": 32,
#                     "topP": 1,
#                     "maxOutputTokens": 2048,
#                 }
#             }
#         )
        
#         if response.status_code == 200:
#             print("Infographic generated successfully with Gemini!")
            
#             # For Gemini we'd need to parse the response differently
#             # This is a simplified example - Gemini might return image data in a different format
#             image_data = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("inlineData", {}).get("data")
            
#             if image_data:
#                 # Save the image
#                 image_bytes = base64.b64decode(image_data)
#                 image = Image.open(io.BytesIO(image_bytes))
                
#                 os.makedirs("visuals", exist_ok=True)
#                 image_path = "visuals/telegram_infographic_gemini.png"
#                 image.save(image_path)
                
#                 return image_path
#             else:
#                 print("No image data found in Gemini response")
#                 return None
#         else:
#             print(f"Gemini API Error: {response.status_code} - {response.text}")
#             return None
#     except Exception as e:
#         print(f"Error calling Gemini API: {str(e)}")
#         return None

# def generate_infographic(recap_text, recap_data):
#     """Generate an infographic with GPT-4, falling back to Gemini if needed"""
#     # Try GPT-4 first
#     infographic_path = generate_infographic_with_gpt4(recap_text, recap_data)
    
#     # If GPT-4 fails, try Gemini
#     if not infographic_path:
#         print("GPT-4 image generation failed, trying Gemini instead...")
#         infographic_path = generate_infographic_with_gemini(recap_text, recap_data)
    
#     return infographic_path

# def main():
#     print("=== Telegram Chat Recap CLI ===")
    
#     # Load or generate sample data
#     try:
#         with open("data/telegram_dump.json", "r") as f:
#             data = json.load(f)
#     except FileNotFoundError:
#         print("No data file found. Using sample data...")
#         data = load_sample_data()
    
#     # Analyze data
#     print("\nAnalyzing chat data...")
#     recap_data = analyze_data(data)
    
#     print("\nBasic Stats:")
#     print(f"Total messages: {recap_data['total_messages']}")
#     print("Top contacts:")
#     for contact, count in recap_data["top_contacts"].items():
#         print(f"- {contact}: {count} messages")
    
#     # Generate AI recap
#     print("\nGenerating AI-powered recap...")
#     ai_recap = generate_recap(recap_data)
    
#     if ai_recap:
#         print("\n=== AI Recap ===")
#         print(ai_recap)
        
#         # Generate infographic
#         print("\nGenerating visual infographic...")
#         infographic_path = generate_infographic(ai_recap, recap_data)
        
#         if infographic_path:
#             print(f"\nInfograpic saved to: {infographic_path}")
#         else:
#             print("\nFailed to generate infographic")
            
#         # Save word cloud path
#         print(f"\nWord cloud saved to: visuals/wordcloud.png")
#     else:
#         print("Failed to generate AI recap")

# if __name__ == "__main__":
#     main()



import os
import json
import yaml
from datetime import datetime
import requests
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import pandas as pd
import base64
from PIL import Image
import io
import time
from fpdf import FPDF
from gtts import gTTS
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

# Load config
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

def load_sample_data():
    """Load sample Telegram data or your actual data"""
    sample_data = {
        "chats": {
            "list": [
                {
                    "name": "Family Group",
                    "messages": [
                        {
                            "date": str(datetime.now()),
                            "from": "Mom",
                            "text": "How are you doing?"
                        },
                        {
                            "date": str(datetime.now()),
                            "from": "You",
                            "text": "I'm good, working on a new project!"
                        }
                    ]
                },
                {
                    "name": "Work Chat",
                    "messages": [
                        {
                            "date": str(datetime.now()),
                            "from": "Colleague",
                            "text": "Did you see the latest requirements?"
                        }
                    ]
                }
            ]
        }
    }
    
    # Save sample data
    os.makedirs("data", exist_ok=True)
    with open("data/telegram_dump.json", "w") as f:
        json.dump(sample_data, f)
    
    return sample_data

def analyze_data(data):
    """Perform analytics on the Telegram data"""
    messages = []
    for chat in data.get("chats", {}).get("list", []):
        for msg in chat.get("messages", []):
            if isinstance(msg.get("text"), str) and msg.get("text").strip():
                messages.append({
                    "timestamp": msg["date"],
                    "sender": msg.get("from", "Unknown"),
                    "content": msg["text"]
                })
    
    # Basic analytics
    senders = [msg["sender"] for msg in messages]
    top_contacts = Counter(senders).most_common(5)
    
    # Word cloud
    all_text = " ".join([msg["content"] for msg in messages if msg["content"]])
    wordcloud = WordCloud(width=800, height=400, background_color="white").generate(all_text)
    
    os.makedirs("visuals", exist_ok=True)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    plt.savefig("visuals/wordcloud.png")
    plt.close()
    
    # Prepare recap data
    recap_data = {
        "top_contacts": {contact: count for contact, count in top_contacts},
        "total_messages": len(messages),
        "top_words": [word for word, _ in wordcloud.words_.items()][:5]
    }
    
    return recap_data


def generate_recap(recap_data):
    """Use OpenAI to generate a natural language recap"""
    # Get API key from config or environment
    api_key = "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"

    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables or config")
        return
    
    prompt = f"""
    Analyze this Telegram chat data and provide a concise, friendly recap:
    
    {json.dumps(recap_data, indent=2)}
    
    Include:
    - Who the user talked to most
    - Any interesting patterns
    - A general sentiment analysis
    - Key topics discussed
    """
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": config["generator"]["model"],
                "messages": [{
                    "role": "system",
                    "content": "You are a helpful data analyst that provides clear insights from chat data."
                }, {
                    "role": "user",
                    "content": prompt
                }],
                "temperature": config["generator"]["default_options"]["temperature"],
                "max_tokens": config["generator"]["default_options"]["max_tokens"]
            }
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error calling OpenAI API: {str(e)}")
        return None

def generate_infographic_with_gpt4(recap_text, recap_data):
    """Generate an infographic using GPT-4 image generation"""
    # Get API key from config or environment
    api_key =  "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"

    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables or config")
        return None
    
    # Create a prompt for the image generation
    image_prompt = f"""
    Create a visually appealing infographic visualizing Telegram chat data with the following information:
    
    Total Messages: {recap_data['total_messages']}
    
    Top Contacts:
    {', '.join([f"{contact} ({count} messages)" for contact, count in recap_data['top_contacts'].items()][:3])}
    
    Top Words Used:
    {', '.join(recap_data['top_words'][:5])}
    
    Key Insights:
    {recap_text[:500] if recap_text else "No insights available"}
    
    Style: Modern, clean design with Telegram-themed color palette (blue and white), data visualizations 
    including bar charts for top contacts, and a visual word cloud. Include the Telegram logo.
    """
    
    try:
        print("\nGenerating infographic with GPT-4...")
        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "dall-e-3",  # Using DALL-E 3 model for image generation
                "prompt": image_prompt,
                "n": 1,
                "size": "1024x1024",
                "response_format": "b64_json"
            }
        )
        
        if response.status_code == 200:
            print("Infographic generated successfully with GPT-4!")
            image_data = response.json()["data"][0]["b64_json"]
            
            # Save the image
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            os.makedirs("visuals", exist_ok=True)
            image_path = "visuals/telegram_infographic.png"
            image.save(image_path)
            
            return image_path
        else:
            print(f"GPT-4 Image API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error calling GPT-4 Image API: {str(e)}")
        return None

def generate_infographic_with_gemini(recap_text, recap_data):
    """Generate an infographic using Google's Gemini (fallback)"""
    # Get API key from config or environment
    api_key = config.get("gemini", {}).get("api_key") or os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables or config")
        return None
    
    # Create a prompt for the image generation
    image_prompt = f"""
    Create a visually appealing infographic visualizing Telegram chat data with the following information:
    
    Total Messages: {recap_data['total_messages']}
    
    Top Contacts:
    {', '.join([f"{contact} ({count} messages)" for contact, count in recap_data['top_contacts'].items()][:3])}
    
    Top Words Used:
    {', '.join(recap_data['top_words'][:5])}
    
    Key Insights:
    {recap_text[:500] if recap_text else "No insights available"}
    
    Style: Modern, clean design with Telegram-themed color palette (blue and white), data visualizations 
    including bar charts for top contacts, and a visual word cloud. Include the Telegram logo.
    """
    
    try:
        print("\nFalling back to Gemini Flash for infographic generation...")
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1/models/gemini-pro-vision:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{
                    "role": "user",
                    "parts": [{
                        "text": image_prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 32,
                    "topP": 1,
                    "maxOutputTokens": 2048,
                }
            }
        )
        
        if response.status_code == 200:
            print("Infographic generated successfully with Gemini!")
            
            # For Gemini we'd need to parse the response differently
            # This is a simplified example - Gemini might return image data in a different format
            image_data = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("inlineData", {}).get("data")
            
            if image_data:
                # Save the image
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
                
                os.makedirs("visuals", exist_ok=True)
                image_path = "visuals/telegram_infographic_gemini.png"
                image.save(image_path)
                
                return image_path
            else:
                print("No image data found in Gemini response")
                return None
        else:
            print(f"Gemini API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error calling Gemini API: {str(e)}")
        return None

def generate_infographic(recap_text, recap_data):
    """Generate an infographic with GPT-4, falling back to Gemini if needed"""
    # Try GPT-4 first
    infographic_path = generate_infographic_with_gpt4(recap_text, recap_data)
    
    # If GPT-4 fails, try Gemini
    if not infographic_path:
        print("GPT-4 image generation failed, trying Gemini instead...")
        infographic_path = generate_infographic_with_gemini(recap_text, recap_data)
    
    return infographic_path

def generate_pdf_report(recap_text, recap_data, infographic_path, wordcloud_path):
    """Generate a comprehensive PDF report of the Telegram chat analysis"""
    print("\nGenerating PDF report...")
    
    try:
        # Create PDF object
        pdf = FPDF()
        pdf.add_page()
        
        # Set font
        pdf.set_font("Arial", "B", 16)
        
        # Title
        pdf.cell(0, 10, "Telegram Chat Analysis Report", 0, 1, "C")
        pdf.ln(10)
        
        # Add timestamp
        pdf.set_font("Arial", "I", 10)
        pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, "R")
        pdf.ln(5)
        
        # Add basic stats
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Basic Statistics", 0, 1, "L")
        pdf.ln(5)
        
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"Total Messages: {recap_data['total_messages']}", 0, 1, "L")
        
        # Top contacts section
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Top Contacts:", 0, 1, "L")
        pdf.set_font("Arial", "", 12)
        
        for contact, count in recap_data["top_contacts"].items():
            pdf.cell(0, 10, f"- {contact}: {count} messages", 0, 1, "L")
        
        pdf.ln(5)
        
        # Top words section
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Top Words:", 0, 1, "L")
        pdf.set_font("Arial", "", 12)
        
        top_words_text = ", ".join(recap_data["top_words"][:5])
        pdf.multi_cell(0, 10, top_words_text)
        pdf.ln(5)
        
        # AI Recap section
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "AI-Generated Insights", 0, 1, "L")
        pdf.ln(5)
        
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 10, recap_text)
        pdf.ln(10)
        
        # Add wordcloud visualization if available
        if os.path.exists(wordcloud_path):
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Word Cloud Visualization", 0, 1, "L")
            pdf.ln(5)
            
            # Add wordcloud image - this needs to fit within the page
            pdf.image(wordcloud_path, x=10, y=None, w=190)
            pdf.ln(10)
        
        # Add infographic if available
        if infographic_path and os.path.exists(infographic_path):
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Generated Infographic", 0, 1, "L")
            pdf.ln(5)
            
            # Add infographic image
            pdf.image(infographic_path, x=10, y=None, w=190)
        
        # Save PDF
        pdf_path = "visuals/telegram_chat_report.pdf"
        pdf.output(pdf_path)
        
        return pdf_path
    
    except Exception as e:
        print(f"Error generating PDF report: {str(e)}")
        return None

def generate_audio_summary(recap_text, recap_data):
    """Generate an audio summary of the chat data"""
    print("\nGenerating audio summary...")
    
    try:
        # Create a slightly condensed version of the recap for audio
        audio_text = f"Telegram Chat Summary. This account has {recap_data['total_messages']} total messages. "
        
        # Add top contacts info
        if recap_data['top_contacts']:
            top_contact_name, top_contact_count = list(recap_data['top_contacts'].items())[0]
            audio_text += f"The most frequent contact is {top_contact_name} with {top_contact_count} messages. "
        
        # Add top words
        if recap_data['top_words']:
            audio_text += f"The most commonly used words include {', '.join(recap_data['top_words'][:3])}. "
        
        # Add the AI generated recap
        audio_text += f"Here's an analysis of your chat data: {recap_text}"
        
        # Generate audio file using gTTS
        tts = gTTS(text=audio_text, lang='en', slow=False)
        
        # Save the audio file
        os.makedirs("audio", exist_ok=True)
        audio_path = "audio/telegram_chat_summary.mp3"
        tts.save(audio_path)
        
        return audio_path
    
    except Exception as e:
        print(f"Error generating audio summary: {str(e)}")
        return None

def main():
    print("=== Telegram Chat Recap CLI ===")
    
    # Load or generate sample data
    try:
        with open("data/telegram_dump.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("No data file found. Using sample data...")
        data = load_sample_data()
    
    # Analyze data
    print("\nAnalyzing chat data...")
    recap_data = analyze_data(data)
    
    print("\nBasic Stats:")
    print(f"Total messages: {recap_data['total_messages']}")
    print("Top contacts:")
    for contact, count in recap_data["top_contacts"].items():
        print(f"- {contact}: {count} messages")
    
    # Generate AI recap
    print("\nGenerating AI-powered recap...")
    ai_recap = generate_recap(recap_data)
    
    if ai_recap:
        print("\n=== AI Recap ===")
        print(ai_recap)
        
        # Word cloud path
        wordcloud_path = "visuals/wordcloud.png"
        print(f"\nWord cloud saved to: {wordcloud_path}")
        
        # Generate infographic
        print("\nGenerating visual infographic...")
        infographic_path = generate_infographic(ai_recap, recap_data)
        
        if infographic_path:
            print(f"\nInfographic saved to: {infographic_path}")
        else:
            print("\nFailed to generate infographic")
            
        # Generate PDF report
        pdf_path = generate_pdf_report(ai_recap, recap_data, infographic_path, wordcloud_path)
        if pdf_path:
            print(f"\nComprehensive PDF report saved to: {pdf_path}")
        else:
            print("\nFailed to generate PDF report")
        
        # Generate audio summary
        audio_path = generate_audio_summary(ai_recap, recap_data)
        if audio_path:
            print(f"\nAudio summary saved to: {audio_path}")
        else:
            print("\nFailed to generate audio summary")
    else:
        print("Failed to generate AI recap")

if __name__ == "__main__":
    main()