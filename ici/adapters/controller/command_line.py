#!/usr/bin/env python3
"""
Main entry point for the ICI application.

This script initializes and runs the TelegramOrchestrator,
providing a command-line interface for interacting with it.
"""

import asyncio
import signal
import sys
import os
import traceback
from typing import Dict, Any

# Add the current directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Load environment variables from .env file
try:
    from ici.utils.load_env import load_env
    load_env()
    # print("Environment variables loaded successfully")
except ImportError as e:
    print(f"Warning: Could not load environment variables: {e}")

try:
    from ici.adapters.orchestrators.telegram_orchestrator import TelegramOrchestrator
    # print("Successfully imported TelegramOrchestrator")
except ImportError as e:
    print(f"Error importing TelegramOrchestrator: {e}")
    traceback.print_exc()
    sys.exit(1)


async def command_line_controller():
    """
    Initialize the TelegramOrchestrator, fetch messages by username, generate a poem, and exit.
    """
    print("Initializing TelegramOrchestrator...")
    try:
        orchestrator = TelegramOrchestrator()
    except Exception as e:
        print(f"Error creating TelegramOrchestrator: {e}")
        traceback.print_exc()
        return 1
    
    try:
        # Initialize the orchestrator
        print("About to initialize the orchestrator...")
        await orchestrator.initialize()
        print("Orchestrator initialized successfully!")
        
        # Prompt for username first
        print("\nPlease enter the username of whose messages you want to fetch:")
        username = input("Username: ").strip()
        
        if username:
            print(f"\nFetching messages from username: {username}...")
            await orchestrator._fetch_messages_by_username(username, limit=100)
            print(f"Messages from {username} stored successfully")
        else:
            print("No username provided, skipping message fetching...")
        
        # Generate a poem from the messages
        print("\nGenerating a poem from the messages...")
        poem = await orchestrator._generate_poem_from_chats("admin")
        print("\nHere's a poem based on your conversations:\n")
        print(poem)
        
        # Exit immediately after displaying the poem
        print("\nAll done! Shutting down...")
        
    except Exception as e:
        print(f"Error during operation: {str(e)}")
        traceback.print_exc()
        return 1
    
    return 0


async def shutdown(orchestrator: TelegramOrchestrator):
    """
    Handle graceful shutdown of the application.
    """
    print("\nShutting down... Please wait.")
    
    # Perform any cleanup here if needed
    # For now we just exit
    
    print("Shutdown complete.")
    sys.exit(0)


def print_help():
    """
    Print available commands.
    """
    print("\nAvailable commands:")
    print("  help    - Show this help message")
    print("  health  - Check the health of the system")
    print("  exit    - Exit the application")
    print("  quit    - Exit the application")
    print("Any other input will be processed as a query to the system.")
