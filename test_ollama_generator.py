#!/usr/bin/env python
"""
Test script for the LangchainGenerator with Ollama.

This script demonstrates how to use the LangchainGenerator
with Ollama as the provider for generating responses.

NOTE: If you encounter NumPy compatibility issues, downgrade NumPy to 1.x:
    pip install numpy==1.24.3 --force-reinstall
"""

import os
import asyncio
import yaml
from pathlib import Path

from ici.adapters.generators.langchain_generator import LangchainGenerator
from ici.adapters.loggers.structured_logger import StructuredLogger

# Configure logger
logger = StructuredLogger(name="test_ollama")

async def main():
    """Test the LangchainGenerator with Ollama."""
    # Create temporary config file with Ollama settings
    config_path = Path("./test_ollama_config.yaml")
    
    config = {
        "generator": {
            "type": "langchain",
            "provider": "ollama",
            "model": "llama3",  # Change to a model you have installed in Ollama
            "base_url": "http://localhost:11434",
            "default_options": {
                "temperature": 0.7,
                "max_tokens": 1024,
                "top_p": 1.0,
            },
            "chain_type": "simple",
            "memory": {
                "type": "buffer",
                "k": 5
            },
            "max_retries": 2,
            "base_retry_delay": 1
        }
    }
    
    with open(config_path, "w") as f:
        yaml.dump(config, f)
    
    try:
        # Set environment variable to point to our test config
        os.environ["ICI_CONFIG_PATH"] = str(config_path)
        
        # Initialize generator
        print("Initializing LangchainGenerator with Ollama...")
        generator = LangchainGenerator(logger_name="test_ollama")
        await generator.initialize()
        
        # Generate a response
        print("\nGenerating response with Ollama...")
        prompt = "Explain what a vector database is in 3 sentences."
        response = await generator.generate(prompt)
        
        print("\nPrompt:")
        print(f"  {prompt}")
        print("\nResponse:")
        print(f"  {response}")
        
        # Run a health check
        print("\nRunning health check...")
        health = await generator.healthcheck()
        print(f"Health status: {'Healthy' if health['healthy'] else 'Unhealthy'}")
        print(f"Message: {health['message']}")
        
    finally:
        # Clean up temporary config file
        if config_path.exists():
            config_path.unlink()
        
        # Remove environment variable
        if "ICI_CONFIG_PATH" in os.environ:
            del os.environ["ICI_CONFIG_PATH"]

if __name__ == "__main__":
    asyncio.run(main()) 