from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from pathlib import Path
import shutil
import os
from typing import List

from ici.utils.text_processor import TextPreprocessor
from ici.core.vector_store import VectorStore
from ici.core.rag_engine import RAGEngine

app = FastAPI(title="ICI Document Upload")

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

# Initialize components
text_processor = TextPreprocessor()
vector_store = VectorStore()
rag_engine = RAGEngine(vector_store)

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
            # Process the document
            processed_text = text_processor.process_file(str(file_path))
            
            if processed_text:
                # Add to vector store
                vector_store.add_document(
                    text=processed_text,
                    metadata={"source": file.filename}
                )
                results.append({
                    "filename": file.filename,
                    "status": "success",
                    "message": "File processed and added to knowledge base"
                })
            else:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "message": "No text content could be extracted"
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
async def search(query: str = Form(...)):
    """Search through processed documents."""
    results = vector_store.search(query, top_k=5)
    return {"results": results}

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