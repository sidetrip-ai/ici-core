#!/usr/bin/env python3
"""
Example script demonstrating how to use the Telegram ingestor.

This script shows how to:
1. Initialize a TelegramIngestor using config.yaml
2. Fetch all direct message history
3. Fetch messages from a specific date range
4. Check ingestor health status

Usage:
    1. Create a Telegram API application at https://my.telegram.org/apps
    2. Get your API ID and API hash
    3. Create a config.yaml file with your credentials
    4. Run the script

Example config.yaml:
```yaml
telegram:
  api_id: "your_api_id"
  api_hash: "your_api_hash"
  phone_number: "+12345678901"
  session_file: "examples/data/telegram_session"
  request_delay: 1.0
```
"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime, timedelta

from ici.adapters.ingestors.telegram import TelegramIngestor
from ici.adapters.loggers import StructuredLogger


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = StructuredLogger(name="example")


def pretty_print_json(data, title=None):
    """Print data as formatted JSON with optional title."""
    if title:
        print(f"\n{title}")
        print("=" * len(title))
    print(json.dumps(data, indent=2))
    print()


async def main_async():
    """Run the Telegram ingestor example asynchronously."""
    print("Telegram Ingestor Example")
    print("-----------------------")
    
    try:
        # Create a sample config.yaml file if it doesn't exist
        if not os.path.exists("config.yaml"):
            create_sample_config()
            print("Created sample config.yaml file. Please edit it with your Telegram credentials.")
            return 1
            
        # Initialize using config.yaml
        print("Initializing ingestor from config.yaml...")
        ingestor = TelegramIngestor(logger_name="example.telegram")
        
        # Call the initialize method
        await ingestor.initialize()
        
        # Check health status
        health = ingestor.healthcheck()
        pretty_print_json(health, "Health Check")
        
        if not health["healthy"]:
            print("Ingestor is not healthy. Cannot proceed.")
            return 1
        
        # Example 1: Fetch recent data (last 7 days)
        print("\nFetching messages from the last 7 days...")
        since_date = datetime.now() - timedelta(days=7)
        recent_data = ingestor.fetch_new_data(since=since_date)
        
        print(f"Retrieved {len(recent_data['messages'])} messages from {len(recent_data['conversations'])} conversations")
        
        # Example 2: Fetch data for a specific date range
        print("\nFetching messages for a specific date range...")
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now() - timedelta(days=15)
        
        print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        range_data = ingestor.fetch_data_in_range(start=start_date, end=end_date)
        
        print(f"Retrieved {len(range_data['messages'])} messages from {len(range_data['conversations'])} conversations")
        
        # Print sample message (if available)
        if recent_data["messages"]:
            sample_message = recent_data["messages"][0]
            pretty_print_json(sample_message, "Sample Message")
        
        # Save data to JSON file
        output_dir = "examples/data"
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = os.path.join(output_dir, "telegram_messages.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(recent_data, f, indent=2, ensure_ascii=False)
            
        print(f"\nSaved messages to {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


def create_sample_config():
    """Create a sample config.yaml file."""
    config_content = """# ICI Framework Configuration

# Telegram Ingestor Configuration
telegram:
  # Get these values from https://my.telegram.org/apps
  api_id: "YOUR_API_ID_HERE"
  api_hash: "YOUR_API_HASH_HERE"
  phone_number: "+12345678901"  # Your phone number with country code
  
  # Authentication options - use either session_file OR session_string
  session_file: "examples/data/telegram_session"  # Option 1: Session file path
  # session_string: "1BQANOTEuMTA4LjU..."  # Option 2: Session string
  
  request_delay: 1.0  # Seconds between API requests to avoid rate limiting
"""
    with open("config.yaml", "w") as f:
        f.write(config_content)


def main():
    """Run the async main function."""
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main()) 