import os
from dotenv import load_dotenv
import openai
from telethon import TelegramClient
import chromadb
import asyncio
import sys
from telethon.sessions import StringSession

# Load environment variables
load_dotenv()

def test_openrouter_api():
    """Test OpenRouter API"""
    try:
        client = openai.OpenAI(
            api_key=os.getenv('GENERATOR_API_KEY'),
            base_url="https://openrouter.ai/api/v1"
        )
        response = client.chat.completions.create(
            model="deepseek/deepseek-chat-v3-0324:free",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        print("✅ OpenRouter API test successful")
        return True
    except Exception as e:
        print(f"❌ OpenRouter API test failed: {str(e)}")
        return False

async def test_telegram_api():
    """Test Telegram API"""
    try:
        print("Testing Telegram API...")
        print("Using existing session string from .env")
        
        client = TelegramClient(
            StringSession(os.getenv('TELEGRAM_SESSION_STRING')),
            int(os.getenv('TELEGRAM_API_ID')),
            os.getenv('TELEGRAM_API_HASH')
        )
        
        print("Connecting to Telegram...")
        try:
            # Add timeout for connection
            await asyncio.wait_for(client.connect(), timeout=30)
        except asyncio.TimeoutError:
            print("❌ Telegram API test failed: Connection timeout")
            return False
        
        if not await client.is_user_authorized():
            print("❌ Telegram API test failed: Not authorized")
            return False
            
        # Test getting self info
        me = await client.get_me()
        print(f"✅ Telegram API test successful")
        print(f"Connected as: {me.first_name} (@{me.username})")
        await client.disconnect()
        return True
    except Exception as e:
        print(f"❌ Telegram API test failed: {str(e)}")
        return False
    finally:
        try:
            await client.disconnect()
        except:
            pass

def test_chromadb():
    """Test ChromaDB"""
    try:
        client = chromadb.Client()
        collection = client.create_collection("test_collection")
        collection.add(
            documents=["This is a test document"],
            ids=["test1"]
        )
        results = collection.query(
            query_texts=["test"],
            n_results=1
        )
        print("✅ ChromaDB test successful")
        return True
    except Exception as e:
        print(f"❌ ChromaDB test failed: {str(e)}")
        return False

async def main():
    print("Starting API tests...\n")
    
    # Run all tests
    openrouter_success = test_openrouter_api()
    try:
        telegram_success = await asyncio.wait_for(test_telegram_api(), timeout=60)
    except asyncio.TimeoutError:
        print("❌ Telegram API test failed: Overall timeout")
        telegram_success = False
    chromadb_success = test_chromadb()
    
    # Print summary
    print("\nTest Summary:")
    print(f"OpenRouter API: {'✅' if openrouter_success else '❌'}")
    print(f"Telegram API: {'✅' if telegram_success else '❌'}")
    print(f"ChromaDB: {'✅' if chromadb_success else '❌'}")
    
    # Exit with appropriate code
    if all([openrouter_success, telegram_success, chromadb_success]):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 