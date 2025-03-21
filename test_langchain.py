#!/usr/bin/env python
"""
Simple test script for the LangchainGenerator.

This script initializes and tests the LangchainGenerator with a simple prompt.
"""

import os
import sys
import asyncio
from ici.adapters.generators.langchain_generator import LangchainGenerator
from ici.utils.config import load_config

async def main():
    print("Testing LangchainGenerator...")
    
    # Force using the config.yaml in current directory
    os.environ["ICI_CONFIG_PATH"] = "config.yaml"
    
    # Load config to verify it's available
    try:
        config = load_config("config.yaml")
        print(f"✓ Config loaded successfully")
    except Exception as e:
        print(f"✗ Failed to load config: {str(e)}")
        return
    
    # Create and initialize generator
    generator = LangchainGenerator(logger_name="test_script")
    
    try:
        print("Initializing generator...")
        await generator.initialize()
        print(f"✓ Generator initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize generator: {str(e)}")
        return
    
    # Test generation
    try:
        prompt = "Tell me about LangChain in one sentence."
        print(f"\nSending prompt: {prompt}")
        
        response = await generator.generate(prompt)
        
        print(f"\nResponse from LangchainGenerator:")
        print(f"------------------------------")
        print(response)
        print(f"------------------------------")
    except Exception as e:
        print(f"✗ Failed to generate response: {str(e)}")
        return
    
    # Check health
    try:
        print("\nPerforming health check...")
        health = await generator.healthcheck()
        print(f"Health status: {'✓ Healthy' if health['healthy'] else '✗ Unhealthy'}")
        print(f"Message: {health['message']}")
    except Exception as e:
        print(f"✗ Failed to perform health check: {str(e)}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        sys.exit(1) 