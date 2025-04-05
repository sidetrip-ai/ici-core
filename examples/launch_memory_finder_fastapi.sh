#!/bin/bash

# Install required dependencies
pip install -r ./examples/memory_finder_fastapi_requirements.txt

# Copy the environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from .env.memory-finder"
    cp .env.memory-finder .env
fi

# Launch the FastAPI app with uvicorn
uvicorn examples.memory_finder_fastapi_app:app --reload