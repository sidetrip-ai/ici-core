import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
from collections import defaultdict

# Load environment variables
load_dotenv()

def analyze_message_mood(text):
    """Simple mood analysis of message text"""
    # Keywords for different moods
    positive_words = {'good', 'great', 'awesome', 'nice', 'thanks', 'thank', 'happy', 'excited', 'love', '😊', '👍', '❤️'}
    negative_words = {'bad', 'poor', 'issue', 'problem', 'error', 'fail', 'bug', 'sorry', 'sad', '😞', '😢', '❌'}
    professional_words = {'meeting', 'project', 'deadline', 'client', 'work', 'task', 'status', 'update', 'report'}
    
    text_lower = text.lower()
    
    # Count occurrences
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    professional_count = sum(1 for word in professional_words if word in text_lower)
    
    # Determine mood
    if positive_count > negative_count:
        return "Positive"
    elif negative_count > positive_count:
        return "Negative"
    elif professional_count > 0:
        return "Professional"
    else:
        return "Neutral"

def categorize_message(text):
    """Categorize message as work or casual"""
    work_keywords = {
        'meeting', 'project', 'deadline', 'client', 'work', 'task', 'status',
        'update', 'report', 'code', 'bug', 'issue', 'api', 'test', 'dev',
        'development', 'production', 'deploy', 'release', 'review'
    }
    
    text_lower = text.lower()
    
    # Check for work-related keywords
    if any(keyword in text_lower for keyword in work_keywords):
        return "Work"
    else:
        return "Casual"

async def test_telegram_api():
    """Test Telegram API connection and basic functionality"""
    client = None
    try:
        print("Testing Telegram API...")
        
        # Get credentials from environment
        api_id = os.getenv('TELEGRAM_API_ID')
        api_hash = os.getenv('TELEGRAM_API_HASH')
        session_string = os.getenv('TELEGRAM_SESSION_STRING')
        
        if not all([api_id, api_hash, session_string]):
            print("❌ Missing required environment variables:")
            if not api_id:
                print("  - TELEGRAM_API_ID")
            if not api_hash:
                print("  - TELEGRAM_API_HASH")
            if not session_string:
                print("  - TELEGRAM_SESSION_STRING")
            return False
        
        print("Initializing Telegram client...")
        client = TelegramClient(
            StringSession(session_string),
            int(api_id),
            api_hash,
            device_model="Test Script",
            system_version="Windows",
            app_version="1.0",
            timeout=30
        )
        
        print("Connecting to Telegram...")
        await client.connect()
        
        if not await client.is_user_authorized():
            print("❌ Telegram API test failed: Not authorized")
            return False
        
        # Test getting self info
        me = await client.get_me()
        print(f"✅ Connected as: {me.first_name} (@{me.username})")
        
        # Get dialog list first
        print("\nGetting dialogs...")
        dialogs = await client.get_dialogs()
        print(f"Found {len(dialogs)} dialogs")
        
        # Analysis containers
        mood_stats = defaultdict(int)
        category_stats = defaultdict(int)
        messages_by_category = defaultdict(list)
        
        # Get messages from the first dialog (usually self)
        if dialogs:
            dialog = dialogs[0]
            print(f"\nRetrieving messages from {dialog.name}...")
            
            messages = await client.get_messages(dialog, limit=100)
            print(f"Retrieved {len(messages)} messages")
            
            if messages:
                print("\nAnalyzing messages...")
                print("-" * 50)
                
                for msg in messages:
                    if msg.message:  # Only analyze messages with text content
                        date = msg.date.strftime("%Y-%m-%d %H:%M:%S")
                        text = msg.message
                        
                        # Analyze mood and category
                        mood = analyze_message_mood(text)
                        category = categorize_message(text)
                        
                        # Update statistics
                        mood_stats[mood] += 1
                        category_stats[category] += 1
                        
                        # Store message in category
                        preview = text[:50] + "..." if len(text) > 50 else text
                        messages_by_category[category].append(f"[{date}] {preview}")
                
                # Print analysis results
                print("\nMood Analysis:")
                print("-" * 50)
                total_messages = sum(mood_stats.values())
                for mood, count in mood_stats.items():
                    percentage = (count / total_messages) * 100
                    print(f"{mood}: {count} messages ({percentage:.1f}%)")
                
                print("\nCategory Analysis:")
                print("-" * 50)
                for category, count in category_stats.items():
                    percentage = (count / total_messages) * 100
                    print(f"{category}: {count} messages ({percentage:.1f}%)")
                
                # Print sample messages from each category
                print("\nSample Messages by Category:")
                print("-" * 50)
                for category, msgs in messages_by_category.items():
                    print(f"\n{category} Messages (showing up to 5):")
                    for msg in msgs[:5]:
                        print(msg)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    finally:
        if client:
            print("\nDisconnecting...")
            await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_telegram_api()) 