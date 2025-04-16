from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
from pydantic import BaseModel
from ici.adapters.orchestrators.query_orchestrator import QueryOrchestrator

app = FastAPI(title="ICI Core API", description="API for ICI Core functionality")

# Add CORS middleware to allow requests from all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

class ContextRequest(BaseModel):
    source: str
    user_id: str
    query: str

class APIController:
    def __init__(self):
        self.orchestrator = QueryOrchestrator()
        self._is_initialized = False
        self._setup_routes()

    async def initialize(self):
        """
        Initialize the orchestrator before enabling API endpoints.
        """
        if not self._is_initialized:
            await self.orchestrator.initialize()
            self._is_initialized = True

    def _setup_routes(self):
        @app.post("/getContext")
        async def get_context(request: ContextRequest) -> Dict[str, Any]:
            """
            Get context using the orchestrator.
            
            Args:
                request: ContextRequest containing source, user_id, and query
                
            Returns:
                Dict[str, Any]: The context data from the orchestrator
                
            Raises:
                HTTPException: If there's an error getting the context
            """
            if not self._is_initialized:
                raise HTTPException(status_code=503, detail="API not initialized. Please wait for initialization to complete.")
            
            try:
                context = await self.orchestrator.get_context(
                    source=request.source,
                    user_id=request.user_id,
                    query=request.query,
                    additional_info={}
                )
                return context
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

    def get_app(self) -> FastAPI:
        """
        Get the FastAPI application instance.
        
        Returns:
            FastAPI: The configured FastAPI application
        """
        return app 