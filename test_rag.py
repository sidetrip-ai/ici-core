from ici.core.rag_engine import RAGEngine
from ici.core.vector_store import VectorStore
import chromadb

def test_rag():
    # Initialize vector store
    vector_store = VectorStore()
    
    # Initialize RAG engine
    rag_engine = RAGEngine(vector_store)
    
    # Add a test document
    test_doc = "This is a test document. It contains some sample text about AI. " \
               "AI stands for Artificial Intelligence. It's a fascinating field of study."
    
    vector_store.add_document(test_doc, {"source": "test.txt"})
    
    # Test question
    question = "What does AI stand for?"
    print(f"\nQuestion: {question}")
    
    # Get answer
    result = rag_engine.get_answer(question)
    print("\nAnswer:", result["answer"])
    print("\nSources:", result["sources"])

if __name__ == "__main__":
    test_rag() 