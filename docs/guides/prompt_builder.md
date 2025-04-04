# Prompt Builder Component Guide

## Overview

A Prompt Builder creates the prompt that is sent to a language model for generating responses. It formats queries and retrieved documents into a structured prompt template.

The Prompt Builder is an optional component - you don't need to implement a custom Prompt Builder when simply connecting a new data source.

## Interface

All prompt builders must implement the `PromptBuilder` interface:

```python
class PromptBuilder(ABC):
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the prompt builder with configuration parameters."""
        pass
        
    @abstractmethod
    async def build_prompt(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Build a prompt from a query and relevant documents.
        
        Args:
            query: The user's query
            documents: Relevant documents retrieved for the query
            **kwargs: Additional parameters for prompt building
            
        Returns:
            Dict[str, Any]: The built prompt with all necessary components
        """
        pass
```

## Basic Implementation

A simple prompt builder might combine query and documents:

```python
async def build_prompt(
    self, 
    query: str, 
    documents: List[Dict[str, Any]], 
    **kwargs
) -> Dict[str, Any]:
    """Build a basic prompt from query and documents."""
    
    # Format documents for the prompt
    formatted_docs = []
    for i, doc in enumerate(documents):
        doc_text = doc.get("text", "")
        doc_source = doc.get("metadata", {}).get("source", f"Document {i+1}")
        formatted_docs.append(f"Source: {doc_source}\n{doc_text}")
    
    # Combine documents
    context = "\n\n".join(formatted_docs)
    
    # Build the prompt template
    prompt = f"""
    Answer the following question based on the provided context. If the answer cannot be determined from the context, say "I don't have enough information to answer this question."
    
    Context:
    {context}
    
    Question: {query}
    
    Answer:
    """
    
    return {
        "prompt": prompt,
        "template_type": "basic_rag"
    }
```

## Configuration

In your `config.yaml` file:

```yaml
prompt_builders:
  default:
    template_type: basic_rag
```

## Conclusion

The Prompt Builder component formats queries and documents into prompts for language models. For most use cases, the default implementation will be sufficient.

If you are connecting a new data source, you typically won't need to modify this component at all.
