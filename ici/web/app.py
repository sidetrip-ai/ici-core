from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import uvicorn
from pathlib import Path
import shutil
import os
from typing import List

from ici.utils.text_processor import TextPreprocessor
from ici.core.vector_store import VectorStore
from ici.core.rag_engine import RAGEngine
from ici.core.document_processor import DocumentProcessor
from ici.core.interfaces import Orchestrator, Generator, PromptBuilder

# Initialize components outside the lifespan
text_processor = TextPreprocessor()
vector_store = VectorStore()
document_processor = DocumentProcessor(text_processor, vector_store)
rag_engine = RAGEngine(vector_store)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize components
    try:
        await vector_store.initialize()
        print("Successfully initialized vector store")
    except Exception as e:
        print(f"Error initializing vector store: {e}")
        
    yield
    
    # Shutdown: cleanup
    try:
        # Clear all documents from the vector store
        vector_store.clear()
        print("Successfully cleared vector store on shutdown")
    except Exception as e:
        print(f"Error clearing vector store on shutdown: {e}")

app = FastAPI(title="ICI Document Upload", lifespan=lifespan)

# Create directories if they don't exist
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR = Path(__file__).parent / "templates"
TEMPLATES_DIR.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Setup templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render the home page."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Handle file uploads and process them for RAG."""
    results = []
    
    for file in files:
        # Save file temporarily
        file_path = UPLOAD_DIR / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            # Process the document using DocumentProcessor
            if document_processor.process_document(str(file_path)):
                results.append({
                    "filename": file.filename,
                    "status": "success",
                    "message": "File processed and added to knowledge base"
                })
            else:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "message": "Failed to process document"
                })
                
        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "error",
                "message": str(e)
            })
        
        # Clean up
        os.remove(file_path)
    
    return {"results": results}

@app.post("/search")
async def search(query: str = Form(...), search_type: str = Form("content")):
    """Search through processed documents."""
    try:
        results = vector_store.search(query, top_k=5, search_type=search_type)
        return {"results": results}
    except Exception as e:
        return {"error": str(e)}

@app.get("/document-names")
async def get_document_names():
    """Get list of all document names."""
    try:
        names = vector_store.get_document_names()
        return {"names": names}
    except Exception as e:
        return {"error": str(e)}

@app.post("/ask")
async def ask_question(question: str = Form(...)):
    """Answer questions using RAG."""
    try:
        response = rag_engine.get_answer(question)
        return {
            "answer": response["answer"],
            "sources": response["sources"],
            "relevant_docs": response["relevant_docs"]
        }
    except Exception as e:
        return {
            "error": str(e)
        }

def run():
    """Run the web application."""
    uvicorn.run(
        "ici.web.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

if __name__ == "__main__":
    run() 