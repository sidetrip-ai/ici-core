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
    Initialize the TelegramOrchestrator and provide a CLI interface.
    """
    print("Initializing TelegramOrchestrator...")
    try:
        orchestrator = TelegramOrchestrator()
        # print("Created TelegramOrchestrator instance")
    except Exception as e:
        print(f"Error creating TelegramOrchestrator: {e}")
        traceback.print_exc()
        return 1
    
    try:
        # Initialize the orchestrator
        
        # Cross-platform signal handling
        loop = asyncio.get_running_loop()
        
        # Register signal handlers for graceful shutdown on Unix systems
        if sys.platform != "win32":
            # Register signal handlers for UNIX-like systems
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(orchestrator)))
            
            print("Signal handlers registered for graceful shutdown")
        else:
            # On Windows, we'll handle KeyboardInterrupt in the main loop
            print("Running on Windows - keyboard interrupt will be handled in the main loop")
        
        # Command line interface loop
        print("\nWelcome to the ICI Command Line Interface!")
        print("Type 'exit' or 'quit' to exit, 'help' for commands")
        print("Enter your questions to interact with the system")
        print("\nWelcome to the ICI Command Line Interface!")
        print("Please select a character to roleplay as:")
        print("1. Sherlock Holmes - A brilliant detective with sharp wit")
        print("2. Elizabeth Bennet - Intelligent and witty")
        print("3. Gandalf - Wise and powerful wizard")
        print("4. Custom - Enter your own character")
        
        while True:
            print("\nEnter character number (1-4): ", end="")
            sys.stdout.flush()
            choice = await loop.run_in_executor(None, sys.stdin.readline)
            choice = choice.strip()
            
            if choice in ['1', '2', '3', '4']:
                break
            print("Invalid choice. Please enter a number between 1 and 4.")
        
        # Set character based on selection
        if choice == '1':
            character = {
                "name": "Sherlock Holmes",
                "personality": "A brilliant detective with sharp wit and keen observation skills",
                "speaking_style": "Analytical, precise, and often uses deductive reasoning"
            }
        elif choice == '2':
            character = {
                "name": "Elizabeth Bennet",
                "personality": "Intelligent, witty, and independent-minded",
                "speaking_style": "Elegant, sometimes sarcastic, and very articulate"
            }
        elif choice == '3':
            character = {
                "name": "Gandalf",
                "personality": "A wise and powerful wizard with deep knowledge",
                "speaking_style": "Mysterious, profound, and often speaks in riddles"
            }
        else:  # Custom character
            print("\nEnter your character's name: ", end="")
            sys.stdout.flush()
            name = await loop.run_in_executor(None, sys.stdin.readline)
            name = name.strip()
            
            print("Enter your character's personality: ", end="")
            sys.stdout.flush()
            personality = await loop.run_in_executor(None, sys.stdin.readline)
            personality = personality.strip()
            
            print("Enter your character's speaking style: ", end="")
            sys.stdout.flush()
            speaking_style = await loop.run_in_executor(None, sys.stdin.readline)
            speaking_style = speaking_style.strip()
            
            character = {
                "name": name,
                "personality": personality,
                "speaking_style": speaking_style
            }
        
        print(f"\nYou are now roleplaying as {character['name']}!")
        print("Type 'exit' or 'quit' to exit, 'help' for commands")
        print("Enter your questions to interact with the system")

        # Store character in additional_info
        additional_info = {
            "session_id": "cli-session",
            "character": character
        }
        
        print("About to initialize the orchestrator...")
        await orchestrator.initialize()
        print("Orchestrator initialized successfully!")
        
        try:
            # Main command loop
            
            while True:
                print("\n> ", end="")
                sys.stdout.flush()  # Force flush the output
                user_input = await loop.run_in_executor(None, sys.stdin.readline)
                user_input = user_input.strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() in ('exit', 'quit'):
                    print("Exiting...")
                    break
                    
                if user_input.lower() == 'help':
                    print_help()
                    continue
                    
                if user_input.lower() == 'health':
                    # Run healthcheck
                    health = await orchestrator.healthcheck()
                    print("\nHealth Status:")
                    print(f"Overall health: {'Healthy' if health['healthy'] else 'Unhealthy'}")
                    print(f"Message: {health['message']}")
                    print("Component status:")
                    for component, status in health.get('components', {}).items():
                        health_str = 'Healthy' if status.get('healthy', False) else 'Unhealthy'
                        print(f"  - {component}: {health_str}")
                    continue
                    
                # Process the query
                try:
                    print("Processing your query...")
                    # Set source to COMMAND_LINE and user_id to admin
                    additional_info = {"session_id": "cli-session"}
                    response = await orchestrator.process_query(
                        source="cli",
                        user_id="admin",
                        query=user_input + " " + character["name"] + " " + character["personality"] + " " + character["speaking_style"],
                        additional_info=additional_info
                    )
                    
                    # Print the response
                    print("\nResponse:")
                    print(response)
                    
                except Exception as e:
                    print(f"\nError processing query: {str(e)}")
                    traceback.print_exc()
        
        except KeyboardInterrupt:
            # Handle Ctrl+C on Windows
            print("\nReceived keyboard interrupt. Shutting down...")
            await shutdown(orchestrator)
        
    except Exception as e:
        print(f"Error initializing orchestrator: {str(e)}")
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
