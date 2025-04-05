#!/usr/bin/env python3
"""
Sidetrip Chat UI

A web interface for chatting with Sidetrip and configuring its settings.
"""

import os
import yaml
import asyncio
import json
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager
import time

from ici.adapters.orchestrators.telegram_orchestrator import TelegramOrchestrator
from ici.utils.config import load_config

# Create templates directory if it doesn't exist
templates_dir = Path("examples/templates")
templates_dir.mkdir(exist_ok=True)

# Create static directory if it doesn't exist
static_dir = Path("examples/static")
static_dir.mkdir(exist_ok=True)

# Global variables
orchestrator = None
config = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.
    Handles startup and shutdown events.
    """
    global orchestrator, config
    
    try:
        # Load configuration
        config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        config = load_config(config_path)
        
        # Ensure validator configuration is properly set
        if "validator" not in config:
            config["validator"] = {}
        if "allowed_sources" not in config["validator"]:
            config["validator"]["allowed_sources"] = []
        if "web" not in config["validator"]["allowed_sources"]:
            config["validator"]["allowed_sources"].append("web")
        
        # Initialize orchestrator
        orchestrator = TelegramOrchestrator()
        await orchestrator.initialize()
        
        # Configure orchestrator with updated config
        print("Configuring orchestrator with validation settings...")
        await orchestrator.configure(config)
        
        yield
        
    except Exception as e:
        print(f"Startup error: {str(e)}")
        raise
    finally:
        if orchestrator:
            # Add cleanup code if needed
            pass

# Create the FastAPI app
app = FastAPI(title="Sidetrip Chat UI", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="examples/static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="examples/templates")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get available models
def get_available_models() -> Dict[str, List[str]]:
    """Get list of available models."""
    return {
        "generators": [
            "deepseek/deepseek-chat-v3-0324:free",
            "anthropic/claude-3-sonnet-20240229",
            "meta-llama/llama-2-70b-chat",
            "google/gemini-2.5-pro-exp-03-25"
        ]
    }

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Render the home page with chat interface.
    """
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "config": config,
            "models": get_available_models()
        }
    )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat and configuration updates.
    """
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data["type"] == "message":
                try:
                    # Process chat message
                    response = await orchestrator.process_query(
                        source="web",
                        user_id="web_user",
                        query=message_data["content"],
                        additional_info={
                            "permission_level": "user",
                            "interface": "web",
                            "timestamp": time.time(),
                            "source": "web",
                            "validation_context": {
                                "source": "web",
                                "user_id": "web_user",
                                "permission_level": "user"
                            }
                        }
                    )
                    
                    # Send response back to client
                    await websocket.send_json({
                        "type": "message",
                        "content": response,
                        "timestamp": asyncio.get_event_loop().time()
                    })
                except Exception as e:
                    print(f"Query processing error: {str(e)}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                
            elif message_data["type"] == "config_update":
                # Update configuration
                new_config = message_data["config"]
                
                # Ensure web source remains allowed
                if "validator" in new_config and "allowed_sources" in new_config["validator"]:
                    if "web" not in new_config["validator"]["allowed_sources"]:
                        new_config["validator"]["allowed_sources"].append("web")
                
                # Update orchestrator configuration
                await orchestrator.configure(new_config)
                
                # Save updated config to file
                config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
                with open(config_path, "w") as f:
                    yaml.dump(new_config, f)
                
                # Send success message
                await websocket.send_json({
                    "type": "config_update",
                    "message": "Configuration updated successfully"
                })
    
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
        await websocket.send_json({
            "type": "error",
            "message": f"An error occurred: {str(e)}"
        })

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Start the Sidetrip Chat UI")
    parser.add_argument("--config", type=str, help="Path to config file")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    args = parser.parse_args()
    
    if args.config:
        os.environ["ICI_CONFIG_PATH"] = args.config
    
    uvicorn.run("sidetrip_chat_ui:app", host="0.0.0.0", port=args.port, reload=True) 