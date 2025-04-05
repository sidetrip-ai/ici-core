from typing import List, Dict, Any
import os
from dotenv import load_dotenv
import requests

class RAGEngine:
    """Engine for RAG-based question answering."""
    
    def __init__(self, vector_store):
        """
        Initialize the RAG engine.
        
        Args:
            vector_store: VectorStore instance for document retrieval
        """
        # Load environment variables
        load_dotenv()
        
        # Ensure API key is set
        self.api_key = os.getenv("GENERATOR_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Generator API key not found. Please set GENERATOR_API_KEY in your .env file."
            )
        
        self.vector_store = vector_store
        
    def get_answer(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        """
        Get an answer to a question using RAG.
        
        Args:
            question: The question to answer
            top_k: Number of most relevant documents to use
            
        Returns:
            Dictionary containing the answer and relevant documents
        """
        try:
            # Retrieve relevant documents
            docs = self.vector_store.search(question, top_k=top_k)
            
            if not docs:
                return {
                    "answer": "I don't have any documents to answer your question. Please upload some documents first.",
                    "sources": [],
                    "relevant_docs": []
                }
            
            # Combine document contents for context
            context = "\n\n".join([
                f"Document: {doc['metadata']['source']}\n{doc['content']}"
                for doc in docs
            ])
            
            # Prepare the prompt
            messages = [
                {"role": "system", "content": """You are a helpful AI assistant that answers questions based on the provided context. 
                Your answers should be:
                1. Accurate and based only on the provided context
                2. Clear and well-structured
                3. Include relevant quotes or references from the context when appropriate
                
                If the context doesn't contain enough information to answer the question, say so."""},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
            ]
            
            # Call the OpenRouter API
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "http://localhost:8000",  # Required for OpenRouter
                    "Content-Type": "application/json"
                },
                json={
                    "model": "mistralai/mistral-7b-instruct",  # Using Mistral model
                    "messages": messages,
                    "max_tokens": 1024,
                    "temperature": 0.7,
                    "top_p": 0.7
                },
                timeout=30  # Add timeout to prevent hanging
            )
            
            response.raise_for_status()  # Raise exception for bad status codes
            
            answer = response.json()["choices"][0]["message"]["content"].strip()
            if not answer:
                answer = "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
            
            return {
                "answer": answer,
                "sources": [doc['metadata']['source'] for doc in docs],
                "relevant_docs": docs
            }
            
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            return {
                "answer": "I encountered an error while processing your question. Please try again later.",
                "sources": [],
                "relevant_docs": []
            }
        except Exception as e:
            print(f"Unexpected error: {e}")
            return {
                "answer": "I encountered an unexpected error. Please try again later.",
                "sources": [],
                "relevant_docs": []
            } 