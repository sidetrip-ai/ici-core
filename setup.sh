#!/bin/bash
# Simple setup script for ICI Core

# Exit on error
set -e

# Check if python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 could not be found. Please install Python 3.8 or newer."
    exit 1
fi

# Print Python version
echo "Using Python:"
python3 --version

# Create a virtual environment if it doesn't exist
if [ ! -d "ici-env" ]; then
    echo "Creating virtual environment..."
    python3 -m venv ici-env
else
    echo "Virtual environment already exists."
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source ici-env/bin/activate

# Install the package in development mode
echo "Installing dependencies..."
pip install -e ".[dev]"

echo ""
echo "Setup complete! You can now use the following commands:"
echo "  pytest                - Run tests"
echo "  pytest --cov=ici tests/ - Run tests with coverage"
echo "  black ici tests examples - Format code with black"
echo ""
echo "To activate the virtual environment in the future, run:"
echo "  source ici-env/bin/activate"

# Keep the environment activated
exec "${SHELL}" 