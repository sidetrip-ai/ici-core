#!/usr/bin/env python3
"""
Example script demonstrating how to use the configuration utilities.

This script shows how to:
1. Load the full configuration from a file
2. Get configuration for a specific component
3. Handle different error cases
"""

import os
import sys
import json

from ici.utils.config import load_config, get_component_config
from ici.core.exceptions import ConfigurationError
from ici.adapters.loggers import StructuredLogger


# Setup logging
logger = StructuredLogger(name="example.config")


def pretty_print_json(data, title=None):
    """Print data as formatted JSON with optional title."""
    if title:
        print(f"\n{title}")
        print("=" * len(title))
    print(json.dumps(data, indent=2))
    print()


def main():
    """Demonstrate the configuration utilities."""
    print("Configuration Utilities Example")
    print("-------------------------------")
    
    # Ensure we have a config file to work with
    if not os.path.exists("config.yaml"):
        print("Creating sample config.yaml file...")
        with open("config.yaml", "w") as f:
            f.write("""# ICI Framework Configuration

# Telegram Ingestor Configuration
telegram:
  api_id: "YOUR_API_ID_HERE"
  api_hash: "YOUR_API_HASH_HERE"
  phone_number: "+12345678901"
  session_file: "telegram_session"
  request_delay: 1.0

# Vector Store Configuration
vector_store:
  type: "chroma"
  collection_name: "example_collection"
  persist_directory: "./data/chroma_db"

# Embedder Configuration
embedder:
  model_name: "sentence-transformers/all-MiniLM-L6-v2"
  device: "cpu"
  batch_size: 32
""")
        print("Sample config.yaml file created.")
    
    try:
        # Example 1: Load the entire configuration
        print("\nExample 1: Loading the entire configuration")
        full_config = load_config()
        print(f"Successfully loaded configuration with {len(full_config)} sections:")
        for section in full_config.keys():
            print(f"  - {section}")
        
        # Example 2: Get configuration for a specific component
        print("\nExample 2: Getting configuration for the vector store component")
        try:
            vector_store_config = get_component_config("vector_store")
            pretty_print_json(vector_store_config, "Vector Store Configuration")
        except ConfigurationError as e:
            print(f"Error: {e}")
        
        # Example 3: Get configuration for a non-existent component
        print("\nExample 3: Getting configuration for a non-existent component")
        try:
            nonexistent_config = get_component_config("nonexistent_component")
            pretty_print_json(nonexistent_config, "Non-existent Component Configuration")
            print("Note: Returns an empty dictionary for non-existent components")
        except ConfigurationError as e:
            print(f"Error: {e}")
        
        # Example 4: Load configuration from a custom path
        print("\nExample 4: Loading configuration from a custom path")
        custom_config_path = "custom_config.yaml"
        try:
            # Create a custom config for demonstration
            with open(custom_config_path, "w") as f:
                f.write("""
custom_component:
  setting1: "value1"
  setting2: 42
""")
            
            # Load the custom configuration
            custom_config = load_config(custom_config_path)
            pretty_print_json(custom_config, "Custom Configuration")
            
            # Clean up the temporary file
            os.remove(custom_config_path)
            
        except ConfigurationError as e:
            print(f"Error: {e}")
        
        # Example 5: Error handling for missing file
        print("\nExample 5: Error handling for missing file")
        try:
            missing_config = load_config("nonexistent_file.yaml")
            pretty_print_json(missing_config, "Missing File Configuration")
        except ConfigurationError as e:
            print(f"Error correctly handled: {e}")
        
        print("\nExample completed successfully!")
        return 0
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 