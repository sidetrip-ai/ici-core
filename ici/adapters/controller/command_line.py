#!/usr/bin/env python3
"""
Command-line controller for running the orchestrator.

This script initializes and runs the DefaultOrchestrator,
allowing interaction with the system via command line.
"""

import os
import sys
import asyncio
import argparse
import json
import signal
import logging
from typing import Dict, Any, List, Optional
import readline  # Enable history
import traceback

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("cli_controller.log")
    ]
)
logger = logging.getLogger("cli_controller")

# Try to import the orchestrator
try:
    from ici.adapters.orchestrators.default_orchestrator import DefaultOrchestrator
    # print("Successfully imported DefaultOrchestrator")
except Exception as e:
    logger.error(f"Error importing DefaultOrchestrator: {e}")
    sys.exit(1)

async def main(args: argparse.Namespace) -> None:
    """
    Initialize the DefaultOrchestrator and provide a CLI interface.
    """
    print("Initializing DefaultOrchestrator...")
    try:
        orchestrator = DefaultOrchestrator()
        # print("Created DefaultOrchestrator instance")
    except Exception as e:
        print(f"Error creating DefaultOrchestrator: {e}")
        traceback.print_exc()
        return
    
    try:
        print("Initializing orchestrator components...")
        await orchestrator.initialize()
        print("Orchestrator initialized successfully.")
    except Exception as e:
        print(f"Error initializing orchestrator: {e}")
        traceback.print_exc()
        return
        
    # Register signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig, lambda: asyncio.create_task(shutdown(orchestrator))
        )
    
    # Assign a fixed user ID for CLI sessions
    user_id = "cli_user_1"
    source = "cli"
    
    print("\nWelcome to the ICI CLI interface.")
    print("Type your query and press Enter. Type 'exit' to quit.")
    print("Special commands: /new (start new chat), /help (show help)\n")
    
    try:
        while True:
            try:
                # Get user input with prompt
                query = input("You: ").strip()
                
                # Check for exit command
                if query.lower() in ("exit", "quit", "/exit", "/quit"):
                    break
                
                # Skip empty queries
                if not query:
                    continue
                
                # Process the query
                response = await orchestrator.process_query(
                    source=source,
                    user_id=user_id,
                    query=query,
                    additional_info={}
                )
                
                # Print response with Assistant prefix
                print(f"\nAssistant: {response}\n")
                
            except KeyboardInterrupt:
                # Handle Ctrl+C within the input loop
                print("\nKeyboard interrupt detected. Type 'exit' to quit.")
                continue
                
            except Exception as e:
                print(f"\nError processing query: {e}")
                logger.error(f"Error processing query: {e}", exc_info=True)
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        logger.error(f"Unexpected error: {e}", exc_info=True)
    
    # Ensure clean shutdown
    await shutdown(orchestrator)

async def shutdown(orchestrator: DefaultOrchestrator):
    """
    Perform clean shutdown of the orchestrator.
    """
    print("\nShutting down orchestrator...")
    # If there's a specific cleanup method, call it here
    
    # If we need to exit immediately (in case of signals)
    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Command-line interface for ICI")
    parser.add_argument(
        "--config", 
        help="Path to config file", 
        default=os.environ.get("ICI_CONFIG_PATH", "config.yaml")
    )
    
    args = parser.parse_args()
    
    # Set config path environment variable if provided
    if args.config:
        os.environ["ICI_CONFIG_PATH"] = args.config
    
    asyncio.run(main(args))
