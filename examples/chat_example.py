#!/usr/bin/env python3
"""
Chat Example Script

This script demonstrates how to use the TelegramOrchestrator for
multi-turn conversation. It simulates a CLI chat interface where 
the user can have contextual conversations with the ICI system.

Usage:
    python examples/chat_example.py
"""

import os
import sys
import asyncio
import signal
from typing import Dict, Any

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ici.adapters import TelegramOrchestrator


async def main():
    """
    Main example function showing chat orchestration.
    
    Creates a CLI interface for having a multi-turn conversation with the model,
    using the TelegramOrchestrator to manage chat state and context.
    """
    print("Initializing chat orchestrator...")
    
    # Create and initialize the chat orchestrator
    orchestrator = TelegramOrchestrator(logger_name="chat_example")
    await orchestrator.initialize()
    
    # Source is "cli" for this example
    source = "cli"
    # Use a fixed user ID for simplicity
    user_id = "example_user"
    
    print("\n====================================")
    print("Welcome to the ICI Chat Example!")
    print("====================================")
    print("Type your messages and press Enter to chat.")
    print("Special commands:")
    print("  /new - Start a new conversation")
    print("  /help - Show available commands")
    print("  /exit - Exit the chat")
    print("====================================\n")
    
    while True:
        try:
            # Get user input
            user_input = input("> ")
            
            # Handle exit command
            if user_input.strip().lower() == "/exit":
                print("Goodbye!")
                break
            
            print("\nProcessing your message...")
            
            # Process the query through the orchestrator
            response = await orchestrator.process_query(
                source=source,
                user_id=user_id,
                query=user_input,
                additional_info={"interface": "cli"}
            )
            
            # Display the response
            print(f"\n{response}\n")
            
        except KeyboardInterrupt:
            print("\nReceived keyboard interrupt. Exiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again or type /exit to quit.")
    
    # Perform any necessary cleanup
    print("Shutting down...")


if __name__ == "__main__":
    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        print("\nReceived interrupt signal. Shutting down...")
        loop.stop()
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        loop.close() 