import os
import json
import yaml
from datetime import datetime
import requests
from collections import Counter
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import pandas as pd

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
    # api_key = os.getenv("OPENAI_API_KEY")
    api_key = "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"

    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables")
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
        
        # Save word cloud path
        print(f"\nWord cloud saved to: visuals/wordcloud.png")
    else:
        print("Failed to generate AI recap")

if __name__ == "__main__":
    main()


# import os
# import json
# import yaml
# from datetime import datetime
# import requests
# from collections import Counter
# from wordcloud import WordCloud, STOPWORDS
# import matplotlib.pyplot as plt
# import pandas as pd
# from textblob import TextBlob  # Simpler alternative to transformers
# import seaborn as sns  # For better visualizations

# # Load config safely
# def load_config():
#     try:
#         with open("config.yaml", "r") as f:
#             return yaml.safe_load(f)
#     except FileNotFoundError:
#         print("Config file not found, using defaults")
#         return {
#             "generator": {
#                 "model": "gpt-4o",
#                 "default_options": {
#                     "temperature": 0.7,
#                     "max_tokens": 1024
#                 }
#             }
#         }

# config = load_config()

# def load_sample_data():
#     """Load enhanced sample Telegram data with realistic timeline"""
#     sample_data = {
#         "chats": {
#             "list": [
#                 {
#                     "name": "Family Group",
#                     "messages": [
#                         {"date": "2025-04-01T10:00:00", "from": "Mom", "text": "Great day today! The weather is wonderful."},
#                         {"date": "2025-04-02T12:00:00", "from": "You", "text": "Yes, loving it! Let's plan a picnic."},
#                         {"date": "2025-04-03T14:00:00", "from": "Mom", "text": "Not feeling great today. Maybe tomorrow?"}
#                     ]
#                 },
#                 {
#                     "name": "Work Chat",
#                     "messages": [
#                         {"date": "2025-04-01T09:00:00", "from": "Colleague", "text": "Busy day ahead with the project deadline!"},
#                         {"date": "2025-04-02T11:00:00", "from": "Colleague", "text": "This is tougher than expected. Need help."},
#                         {"date": "2025-04-03T16:00:00", "from": "You", "text": "We can do it! Let's push through together."}
#                     ]
#                 }
#             ]
#         }
#     }
    
#     os.makedirs("data", exist_ok=True)
#     with open("data/telegram_dump.json", "w") as f:
#         json.dump(sample_data, f)
    
#     return sample_data

# def analyze_sentiment(text):
#     """Simpler sentiment analysis using TextBlob"""
#     analysis = TextBlob(text)
#     return {
#         "label": "POSITIVE" if analysis.sentiment.polarity > 0 else "NEGATIVE",
#         "score": abs(analysis.sentiment.polarity)
#     }

# def analyze_data(data):
#     """Enhanced analytics with better visualizations"""
#     messages = []
#     for chat in data.get("chats", {}).get("list", []):
#         for msg in chat.get("messages", []):
#             if isinstance(msg.get("text"), str) and msg.get("text").strip():
#                 try:
#                     timestamp = datetime.fromisoformat(msg["date"])
#                 except ValueError:
#                     timestamp = datetime.now()
                
#                 sentiment = analyze_sentiment(msg["text"])
                
#                 messages.append({
#                     "timestamp": timestamp,
#                     "date": timestamp.date(),
#                     "sender": msg.get("from", "Unknown"),
#                     "content": msg["text"],
#                     "sentiment_label": sentiment["label"],
#                     "sentiment_score": sentiment["score"],
#                     "chat": chat["name"]
#                 })
    
#     # Convert to DataFrame for easier analysis
#     df = pd.DataFrame(messages)
    
#     # Basic analytics
#     top_contacts = Counter(df['sender']).most_common(5)
    
#     # Sentiment over time analysis
#     df['period'] = df['timestamp'].dt.to_period('D')  # Daily grouping
#     sentiment_trend = df.groupby(['period', 'sentiment_label']).size().unstack(fill_value=0)
    
#     # Enhanced visualizations
#     os.makedirs("visuals", exist_ok=True)
    
#     # 1. Improved Sentiment Timeline
#     plt.figure(figsize=(12, 6))
#     sns.lineplot(
#         data=df,
#         x='period',
#         y='sentiment_score',
#         hue='sentiment_label',
#         style='sentiment_label',
#         markers=True,
#         dashes=False,
#         palette={'POSITIVE': 'green', 'NEGATIVE': 'red'}
#     )
#     plt.title('Daily Sentiment Trend', fontsize=14)
#     plt.xlabel('Date', fontsize=12)
#     plt.ylabel('Sentiment Score', fontsize=12)
#     plt.xticks(rotation=45)
#     plt.grid(True, alpha=0.3)
#     plt.tight_layout()
#     plt.savefig("visuals/sentiment_timeline.png", dpi=300)
#     plt.close()
    
#     # 2. Enhanced Word Cloud
#     all_text = " ".join(df['content'].dropna())
#     stopwords = set(STOPWORDS).union({'will', 'just', 'now', 'oh'})
    
#     wordcloud = WordCloud(
#         width=1200,
#         height=600,
#         background_color='white',
#         stopwords=stopwords,
#         colormap='viridis',
#         max_words=200,
#         contour_width=3,
#         contour_color='steelblue'
#     ).generate(all_text)
    
#     plt.figure(figsize=(14, 7))
#     plt.imshow(wordcloud, interpolation='bilinear')
#     plt.axis("off")
#     plt.title('Most Frequent Words in Chats', fontsize=16, pad=20)
#     plt.savefig("visuals/wordcloud.png", dpi=300, bbox_inches='tight')
#     plt.close()
    
#     # Prepare recap data
#     recap_data = {
#         "top_contacts": dict(top_contacts),
#         "total_messages": len(df),
#         "top_words": [word for word, _ in wordcloud.words_.items()][:10],
#         "sentiment_distribution": {
#             "positive": len(df[df['sentiment_label'] == 'POSITIVE']),
#             "negative": len(df[df['sentiment_label'] == 'NEGATIVE'])
#         },
#         "most_positive_message": df.loc[df['sentiment_score'].idxmax()]['content'],
#         "most_negative_message": df.loc[df[df['sentiment_label'] == 'NEGATIVE']['sentiment_score'].idxmax()]['content']
#     }
    
#     return recap_data

# def generate_recap(recap_data):
#     """Secure API call with error handling"""
#     api_key = os.getenv("GENERATOR_API_KEY")  # Never hardcode API keys
    
#     if not api_key:
#         print("Error: GENERATOR_API_KEY not found in environment variables")
#         return None
    
#     prompt = f"""
#     Analyze this Telegram chat data and provide a concise, friendly recap:
    
#     {json.dumps(recap_data, indent=2)}
    
#     Focus on:
#     1. Communication patterns (who, how often)
#     2. Emotional tone trends
#     3. Key topics from word frequency
#     4. Notable positive/negative messages
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
#                 "messages": [
#                     {
#                         "role": "system",
#                         "content": "You are a helpful data analyst that provides clear, engaging insights from chat data."
#                     },
#                     {
#                         "role": "user",
#                         "content": prompt
#                     }
#                 ],
#                 "temperature": config["generator"]["default_options"]["temperature"],
#                 "max_tokens": config["generator"]["default_options"]["max_tokens"]
#             },
#             timeout=30  # Add timeout
#         )
        
#         response.raise_for_status()  # Raises HTTPError for bad responses
#         return response.json()["choices"][0]["message"]["content"]
    
#     except requests.exceptions.RequestException as e:
#         print(f"API Error: {str(e)}")
#         return None

# def main():
#     print("=== Telegram Chat Recap CLI ===")
    
#     # Data loading with better error handling
#     try:
#         with open("data/telegram_dump.json", "r") as f:
#             data = json.load(f)
#     except (FileNotFoundError, json.JSONDecodeError) as e:
#         print(f"Data loading error: {str(e)}. Using sample data...")
#         data = load_sample_data()
    
#     # Analysis
#     print("\nAnalyzing chat data...")
#     recap_data = analyze_data(data)
    
#     print("\nBasic Stats:")
#     print(f"Total messages: {recap_data['total_messages']}")
#     print(f"Positive messages: {recap_data['sentiment_distribution']['positive']}")
#     print(f"Negative messages: {recap_data['sentiment_distribution']['negative']}")
#     print("\nTop contacts:")
#     for contact, count in recap_data["top_contacts"].items():
#         print(f"- {contact}: {count} messages")
    
#     # AI Recap
#     print("\nGenerating AI-powered recap...")
#     if ai_recap := generate_recap(recap_data):
#         print("\n=== AI Recap ===")
#         print(ai_recap)
#         print("\nVisualizations saved to visuals/ directory")
#     else:
#         print("Failed to generate AI recap")

# if __name__ == "__main__":
#     main()