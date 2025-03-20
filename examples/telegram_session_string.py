#!/usr/bin/env python3
"""
Example script for generating and using Telegram session strings.

This script demonstrates how to:
1. Generate a session string from existing session file or new authentication
2. Connect to Telegram using a session string
3. Use the session string with the TelegramIngestor

Usage:
    1. Run this script with --generate to create a session string
    2. Run this script with --use to demonstrate using a session string

Example:
    python examples/telegram_session_string.py --generate
    python examples/telegram_session_string.py --use "YOUR_SESSION_STRING"
"""

import os
import sys
import json
import argparse
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from telethon.sessions import StringSession
from telethon.sync import TelegramClient

from ici.adapters.ingestors.telegram import TelegramIngestor
from ici.adapters.loggers import StructuredLogger


# Setup CLI arguments
parser = argparse.ArgumentParser(description='Telegram Session String Example')
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--generate', action='store_true', help='Generate a new session string')
group.add_argument('--use', type=str, metavar='SESSION_STRING', help='Use the provided session string')


async def generate_session_string() -> str:
    """
    Generate a session string using the Telethon client.
    
    Returns:
        str: The generated session string.
    """
    # Load Telegram credentials from environment or prompt the user
    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    session_file = os.environ.get("TELEGRAM_SESSION_FILE", "telegram_session")
    
    if not api_id:
        api_id = input("Enter your Telegram API ID: ")
    
    if not api_hash:
        api_hash = input("Enter your Telegram API hash: ")
    
    # Create a new Telegram client
    async with TelegramClient(session_file, api_id, api_hash) as client:
        # Generate the session string
        session_string = StringSession.save(client.session)
        print("\nYour session string has been generated:")
        print("-" * 50)
        print(session_string)
        print("-" * 50)
        print("\nStore this string securely as it provides access to your Telegram account.")
        
        return session_string


async def use_session_string(session_string: str) -> None:
    """
    Demonstrate using a session string with the TelegramIngestor.
    
    Args:
        session_string: The session string to use.
    """
    # Load Telegram credentials from environment or prompt the user
    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    phone = os.environ.get("TELEGRAM_PHONE")
    
    if not api_id:
        api_id = input("Enter your Telegram API ID: ")
    
    if not api_hash:
        api_hash = input("Enter your Telegram API hash: ")
    
    if not phone:
        phone = input("Enter your phone number (with country code, e.g., +12345678901): ")
    
    print("\nInitializing TelegramIngestor with session string...")
    ingestor = TelegramIngestor(logger_name="example.telegram")
    
    # Connect using the session string
    config = {
        "api_id": api_id,
        "api_hash": api_hash,
        "phone_number": phone,
        "session_string": session_string,
        "request_delay": 1.0
    }
    
    await ingestor._connect(config)
    
    # Check health status
    health = ingestor.healthcheck()
    print(f"Health check: {'Healthy' if health['healthy'] else 'Unhealthy'}")
    
    if not health["healthy"]:
        print("Ingestor is not healthy. Cannot proceed.")
        return
    
    # Fetch recent messages as a demonstration
    print("\nFetching messages from the last 3 days...")
    since_date = datetime.now() - timedelta(days=3)
    recent_data = ingestor.fetch_new_data(since=since_date)
    
    print(f"Retrieved {len(recent_data['messages'])} messages from {len(recent_data['conversations'])} conversations")
    
    # Print a sample message
    if recent_data["messages"]:
        sample_message = recent_data["messages"][0]
        print("\nSample message:")
        print(f"From: {sample_message['conversation_name']}")
        print(f"Date: {sample_message['date']}")
        print(f"Message: {sample_message['text'][:100]}...")


async def main_async() -> int:
    """
    Run the example script asynchronously.
    
    Returns:
        int: The exit code.
    """
    args = parser.parse_args()
    
    try:
        if args.generate:
            await generate_session_string()
        elif args.use:
            await use_session_string(args.use)
    
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


def main() -> int:
    """
    Run the async main function.
    
    Returns:
        int: The exit code.
    """
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main()) 