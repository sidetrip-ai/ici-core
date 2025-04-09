# Connector Component Guide

## Overview

A Connector is the interface between users and your knowledge base. It receives queries from users, processes them through the orchestrator, and returns relevant information. Unlike other components in the ICI framework, Connectors don't have a strict interface - you have the flexibility to implement them in a way that best serves your specific application needs.

Connectors typically handle:
- Receiving queries from various sources (chat interfaces, APIs, email, etc.)
- Passing queries to the orchestrator
- Returning responses to users
- Maintaining conversation context
- Managing user sessions

## The Orchestrator: A Brief Introduction

The Orchestrator is the central coordinator of the ICI framework. Think of it as the conductor of an orchestra, ensuring all components work together harmoniously.

The Orchestrator:
- Receives queries from your Connector
- Processes these queries by calling the appropriate components
- Manages the flow of information between components
- Returns relevant responses back to your Connector

You don't need to modify the Orchestrator to connect a new data source - the default Orchestrator already handles the complex task of coordinating the retrieval process.

## Using the Default Orchestrator

The DefaultOrchestrator provides a simple and effective way to process queries against your knowledge base:

```python
from ici.orchestrators.default import DefaultOrchestrator
from ici.adapters.loggers import StructuredLogger

class MyConnector:
    def __init__(self):
        """Initialize the connector with the default orchestrator."""
        self.logger = StructuredLogger(name="my_connector")
        self.orchestrator = None
        
    async def initialize(self):
        """Initialize the orchestrator."""
        try:
            self.orchestrator = DefaultOrchestrator()
            await self.orchestrator.initialize()
            
            self.logger.info({
                "action": "CONNECTOR_INIT_SUCCESS",
                "message": "Connector initialized successfully"
            })
        except Exception as e:
            self.logger.error({
                "action": "CONNECTOR_INIT_ERROR",
                "message": f"Failed to initialize connector: {str(e)}",
                "data": {"error": str(e)}
            })
            raise
            
    async def process_query(self, query: str, user_id: str = "default_user", **kwargs):
        """
        Process a user query through the orchestrator.
        
        Args:
            query: The user's query text
            user_id: Identifier for the user (for session management)
            **kwargs: Additional parameters to pass to the orchestrator
            
        Returns:
            The orchestrator's response
        """
        if not self.orchestrator:
            await self.initialize()
            
        try:
            # Pass the query to the orchestrator
            response = await self.orchestrator.process_query(
                query=query,
                user_id=user_id,
                **kwargs
            )
            
            self.logger.info({
                "action": "QUERY_PROCESSED",
                "message": "Successfully processed query",
                "data": {
                    "user_id": user_id,
                    "query": query
                }
            })
            
            return response
            
        except Exception as e:
            self.logger.error({
                "action": "QUERY_PROCESSING_ERROR",
                "message": f"Failed to process query: {str(e)}",
                "data": {
                    "user_id": user_id,
                    "query": query,
                    "error": str(e)
                }
            })
            
            # Return an error message to the user
            return {
                "error": "Failed to process your query",
                "details": str(e)
            }
```

## Implementing Different Types of Connectors

### REST API Connector

A REST API connector allows external applications to query your knowledge base through HTTP requests:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import asyncio

class QueryRequest(BaseModel):
    query: str
    user_id: str = "default_user"
    
class APIConnector:
    def __init__(self, host="0.0.0.0", port=8000):
        """Initialize the API connector."""
        self.app = FastAPI(title="Knowledge Base API")
        self.host = host
        self.port = port
        self.orchestrator = None
        self.setup_routes()
        
    def setup_routes(self):
        """Set up the API routes."""
        @self.app.post("/query")
        async def query(request: QueryRequest):
            if not self.orchestrator:
                await self.initialize()
                
            try:
                response = await self.orchestrator.process_query(
                    query=request.query,
                    user_id=request.user_id
                )
                return response
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.app.get("/health")
        async def health():
            if not self.orchestrator:
                return {"status": "not_initialized"}
                
            try:
                # You could add more detailed health checks here
                return {"status": "healthy"}
            except Exception:
                return {"status": "unhealthy"}
                
    async def initialize(self):
        """Initialize the orchestrator."""
        from ici.orchestrators.default import DefaultOrchestrator
        
        self.orchestrator = DefaultOrchestrator()
        await self.orchestrator.initialize()
        
    def run(self):
        """Run the API server."""
        uvicorn.run(self.app, host=self.host, port=self.port)
        
# Usage
if __name__ == "__main__":
    connector = APIConnector()
    connector.run()
```

### Chat Interface Connector

A connector for a chat-based interface:

```python
import readline  # For better command-line input handling
import asyncio

class ConsoleChatConnector:
    def __init__(self):
        """Initialize the console chat connector."""
        self.orchestrator = None
        self.user_id = "console_user"
        self.history = []
        
    async def initialize(self):
        """Initialize the orchestrator."""
        from ici.orchestrators.default import DefaultOrchestrator
        
        self.orchestrator = DefaultOrchestrator()
        await self.orchestrator.initialize()
        
    async def chat_loop(self):
        """Run the interactive chat loop."""
        if not self.orchestrator:
            await self.initialize()
            
        print("Knowledge Base Chat (type 'exit' to quit)")
        print("----------------------------------------")
        
        while True:
            try:
                query = input("\nYou: ")
                
                if query.lower() in ["exit", "quit"]:
                    break
                    
                if not query.strip():
                    continue
                    
                # Store in history
                self.history.append({"role": "user", "content": query})
                
                # Process through orchestrator
                response = await self.orchestrator.process_query(
                    query=query,
                    user_id=self.user_id,
                    chat_history=self.history
                )
                
                # Print response
                if isinstance(response, dict) and "answer" in response:
                    print(f"\nAssistant: {response['answer']}")
                    self.history.append({"role": "assistant", "content": response["answer"]})
                else:
                    print(f"\nAssistant: {response}")
                    self.history.append({"role": "assistant", "content": str(response)})
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\nError: {str(e)}")
                
        print("\nGoodbye!")
        
# Usage
if __name__ == "__main__":
    connector = ConsoleChatConnector()
    asyncio.run(connector.chat_loop())
```

### Webhook Connector

A connector for processing webhooks from external services:

```python
from fastapi import FastAPI, Request, HTTPException
import uvicorn
import json

class WebhookConnector:
    def __init__(self, host="0.0.0.0", port=8000):
        """Initialize the webhook connector."""
        self.app = FastAPI(title="Knowledge Base Webhook")
        self.host = host
        self.port = port
        self.orchestrator = None
        self.setup_routes()
        
    def setup_routes(self):
        """Set up the webhook routes."""
        @self.app.post("/webhook/slack")
        async def slack_webhook(request: Request):
            if not self.orchestrator:
                await self.initialize()
                
            try:
                # Parse Slack webhook format
                data = await request.json()
                
                # Extract query from Slack event
                # This is a simplified example - real Slack events have more structure
                if "event" in data and "text" in data["event"]:
                    query = data["event"]["text"]
                    user_id = data["event"].get("user", "slack_user")
                    
                    # Process query
                    response = await self.orchestrator.process_query(
                        query=query,
                        user_id=user_id
                    )
                    
                    # Return response in Slack-friendly format
                    return {
                        "text": response["answer"] if isinstance(response, dict) and "answer" in response else str(response)
                    }
                    
                return {"text": "Could not process webhook payload"}
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
                
    async def initialize(self):
        """Initialize the orchestrator."""
        from ici.orchestrators.default import DefaultOrchestrator
        
        self.orchestrator = DefaultOrchestrator()
        await self.orchestrator.initialize()
        
    def run(self):
        """Run the webhook server."""
        uvicorn.run(self.app, host=self.host, port=self.port)
        
# Usage
if __name__ == "__main__":
    connector = WebhookConnector()
    connector.run()
```

## Advanced Orchestrator Usage

For more advanced use cases, you can customize how you interact with the orchestrator:

### Custom Query Parameters

```python
async def process_complex_query(self, query, user_id="default_user", filters=None):
    """Process a query with custom filters."""
    if not self.orchestrator:
        await self.initialize()
        
    # Apply filters to narrow down the search
    response = await self.orchestrator.process_query(
        query=query,
        user_id=user_id,
        filters=filters,
        max_results=5,
        threshold=0.7  # Minimum similarity score
    )
    
    return response
```

### Multi-collection Queries

```python
async def query_multiple_collections(self, query, collections=None, user_id="default_user"):
    """Query across multiple knowledge collections."""
    if not self.orchestrator:
        await self.initialize()
        
    results = {}
    
    for collection in collections or ["default"]:
        response = await self.orchestrator.process_query(
            query=query,
            user_id=user_id,
            collection_name=collection
        )
        
        results[collection] = response
        
    # Combine or rank results as needed
    return results
```

### Conversation Context

```python
async def process_conversation(self, query, conversation_history, user_id="default_user"):
    """Process a query with conversation history."""
    if not self.orchestrator:
        await self.initialize()
        
    # Format history as expected by the orchestrator
    formatted_history = []
    for message in conversation_history:
        formatted_history.append({
            "role": message["role"],
            "content": message["content"]
        })
        
    response = await self.orchestrator.process_query(
        query=query,
        user_id=user_id,
        chat_history=formatted_history
    )
    
    return response
```

## Configuration Setup

As with other components, configuration for your connector can be managed in the `config.yaml` file:

```yaml
connectors:
  api_connector:
    host: "0.0.0.0"
    port: 8000
    rate_limit: 100  # Requests per minute
    
  chat_connector:
    name: "Knowledge Assistant"
    max_history: 10  # Max conversation turns to remember
```

Load the configuration in your connector:

```python
from ici.utils.config import get_component_config
import os

class ConfigurableConnector:
    def __init__(self):
        """Initialize with configuration."""
        self.config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        self.config = self._load_config()
        self.orchestrator = None
        
    def _load_config(self):
        """Load connector configuration."""
        try:
            connector_config = get_component_config("connectors.api_connector", self.config_path)
            return {
                "host": connector_config.get("host", "0.0.0.0"),
                "port": int(connector_config.get("port", 8000)),
                "rate_limit": int(connector_config.get("rate_limit", 100))
            }
        except Exception:
            # Use defaults if config loading fails
            return {
                "host": "0.0.0.0",
                "port": 8000,
                "rate_limit": 100
            }
```

## Best Practices

1. **Error Handling**: Implement robust error handling to provide helpful feedback to users.

2. **Rate Limiting**: Protect your system with rate limiting to prevent overload.

3. **Validation**: Validate user input before processing to prevent security issues.

4. **Logging**: Log user interactions for debugging and analytics.

5. **Statelessness**: Design your connector to be stateless where possible for better scalability.

6. **Timeouts**: Implement appropriate timeouts for orchestrator calls.

7. **User Sessions**: Track user sessions to maintain conversation context.

8. **Authentication**: Add authentication for sensitive knowledge bases.

9. **Extensibility**: Design your connector to be extensible as requirements evolve.

10. **Testing**: Test your connector with various query types and error conditions.

## Integration Examples

### Web Application

```python
# Example of integrating with a Flask web application
from flask import Flask, request, jsonify
import asyncio

app = Flask(__name__)
connector = None

# Helper to run async code in Flask
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

@app.before_first_request
def initialize():
    """Initialize the connector before first request."""
    global connector
    from my_app.connectors import MyConnector
    connector = MyConnector()
    run_async(connector.initialize())

@app.route("/api/query", methods=["POST"])
def handle_query():
    """Handle query requests."""
    data = request.json
    query = data.get("query", "")
    user_id = data.get("user_id", "web_user")
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
        
    response = run_async(connector.process_query(query, user_id))
    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True)
```

### Discord Bot

```python
# Example of a Discord bot connector
import discord
from discord.ext import commands
import asyncio
import os

# Set up Discord bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Knowledge connector
connector = None

@bot.event
async def on_ready():
    """Initialize when bot is ready."""
    global connector
    from my_app.connectors import MyConnector
    
    print(f"Logged in as {bot.user}")
    
    connector = MyConnector()
    await connector.initialize()
    print("Knowledge connector initialized")

@bot.command(name="ask")
async def ask_command(ctx, *, question):
    """Command to ask the knowledge base a question."""
    if not connector:
        await ctx.send("Still initializing, please try again in a moment.")
        return
        
    # Send typing indicator while processing
    async with ctx.typing():
        user_id = f"discord_{ctx.author.id}"
        
        response = await connector.process_query(
            query=question,
            user_id=user_id
        )
        
        if isinstance(response, dict) and "answer" in response:
            await ctx.send(response["answer"])
        else:
            await ctx.send(str(response))

# Run the bot
if __name__ == "__main__":
    bot.run(os.environ.get("DISCORD_TOKEN"))
```

## Conclusion

Connectors are the bridge between users and your knowledge base. With the flexibility to implement them in various ways, you can create interfaces that perfectly match your application's needs. The default orchestrator handles the complexity of processing queries, allowing you to focus on creating a great user experience.

By following the patterns and best practices in this guide, you can create robust connectors that make your knowledge base accessible and useful in a variety of contexts.
