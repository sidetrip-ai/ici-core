import asyncio
import uvicorn
from ici.adapters.controller.api_controller import APIController

async def main():
    """
    Main function to initialize and start the API server.
    """
    # Create API controller
    api_controller = APIController()
    
    # Initialize the orchestrator
    print("Initializing orchestrator...")
    await api_controller.initialize()
    print("Orchestrator initialized successfully")
    
    # Get the FastAPI app
    app = api_controller.get_app()
    
    # Run the server
    print("Starting API server...")
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main()) 