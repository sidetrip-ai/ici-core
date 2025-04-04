#!/usr/bin/env python3
"""
Chat system example for the ICI framework.

This script demonstrates how to use the DefaultOrchestrator for
multi-turn conversations with chat history.
"""

import os
import sys
import asyncio
import time
from typing import Dict, Any, List
import json

# Set up path to find ICI modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import the orchestrator
try:
    from ici.adapters import DefaultOrchestrator
except ImportError as e:
    print(f"Error importing ICI: {e}")
    sys.exit(1)

async def main():
    """
    Main chat example function.
    
    This demonstrates multi-turn conversation capabilities
    using the DefaultOrchestrator to manage chat state and context.
    """
    print("Initializing orchestrator...")
    
    # Initialize orchestrator
    orchestrator = DefaultOrchestrator(logger_name="chat_example")
    await orchestrator.initialize()
    
    print("Orchestrator initialized successfully.")
    
    # User ID and source
    user_id = "example_user_1"
    source = "example"
    
    # Welcome the user
    print("\nWelcome to the ICI Chat Example!")
    print("This demonstrates a multi-turn conversation with history.")
    print("Type 'exit' or 'quit' to end the conversation.")
    print("Type '/new' to start a new conversation.")
    print("Type '/help' for help.\n")
    
    while True:
        # Get user input
        user_input = input("You: ").strip()
        
        # Check for exit command
        if user_input.lower() in ("exit", "quit"):
            break
        
        # Process the query
        try:
            response = await orchestrator.process_query(
                source=source,
                user_id=user_id,
                query=user_input,
                additional_info={}
            )
            
            # Print response
            print(f"\nAssistant: {response}\n")
            
        except Exception as e:
            print(f"Error processing query: {e}")
    
    print("Chat example completed.")

if __name__ == "__main__":
    # Set config path environment variable if needed
    if len(sys.argv) > 1:
        os.environ["ICI_CONFIG_PATH"] = sys.argv[1]
    
    # Run the example
    asyncio.run(main()) 