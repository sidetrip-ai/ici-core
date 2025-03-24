#!/usr/bin/env python3
"""
Environment Variable Loader

This script loads environment variables from a .env file and can be imported
or run before other scripts to ensure environment variables are set properly.
"""

import os
import sys
import argparse
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    print("python-dotenv not installed. Installing now...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
    from dotenv import load_dotenv


def load_env(env_file: Optional[str] = None) -> None:
    """
    Load environment variables from a .env file.
    
    Args:
        env_file: Path to the .env file. If None, looks for .env in the current directory.
    """
    # Default to .env in the current directory if not specified
    if env_file is None:
        env_file = ".env"
    
    # Check if the file exists
    if not os.path.exists(env_file):
        print(f"Warning: Environment file {env_file} not found.")
        print(f"Create one by copying .env.example: cp .env.example .env")
        return
    
    # Load the .env file with override=True to override existing environment variables
    load_dotenv(env_file, override=True)
    print(f"Loaded environment variables from {env_file} (with override)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load environment variables from a .env file")
    parser.add_argument("--env-file", type=str, help="Path to the .env file")
    args = parser.parse_args()
    
    # Load environment variables
    load_env(args.env_file)
    
    # Print the loaded environment variables (without values for security)
    print("\nLoaded environment variables (showing names only for security):")
    env_vars = [var for var in os.environ if var in open(args.env_file or ".env").read()]
    for var in sorted(env_vars):
        print(f"  - {var}: ***") 