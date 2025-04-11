# Generator Component Guide

## Overview

A Generator is the component responsible for crafting natural language responses to user queries. The Generator receives a prompt (prepared by the orchestrator) and generates a coherent, contextually appropriate answer. The Generator does not handle document retrieval or context preparation - these tasks are handled by the orchestrator component.

Like the Vector Store, the Generator is primarily an infrastructure component - you only need to implement a custom Generator if you want to change the answer generation strategy or use a different language model. If you're simply connecting a new data source, you don't need to focus on implementing a Generator component at all.

## Interface

All generators must implement the `Generator` interface defined in `ici/core/interfaces/generator.py`:

```python
class Generator(ABC):
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the generator with configuration parameters."""
        pass
        
    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        user_id: str = "default", 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a response using the provided prompt.
        
        Args:
            prompt: The formatted prompt including query and context
            user_id: The user identifier for personalization
            **kwargs: Additional parameters for generation
            
        Returns:
            Dict[str, Any]: Response containing the answer and metadata
        """
        pass
```

## Expected Input and Output

### Generate

**Input:**
- `prompt`: The complete prompt including the user's query and any necessary context
- `user_id`: Identifier for the user (for tracking/personalization)
- `**kwargs`: Additional parameters (generation settings, etc.)

```python
prompt = """
You are a helpful assistant that answers questions based on the provided information.
Use ONLY the context below to answer the question. If you don't know the answer based
on the context, say "I don't have enough information to answer this question."

Context information:
[energy_report]: Renewable energy sources like solar and wind power...
[clean_energy_guide]: The main advantages of renewable energy include reduced emissions...

Question: What are the benefits of renewable energy?

Answer:
"""

user_id = "user_123"

# Optional kwargs
kwargs = {
    "generation_params": {
        "temperature": 0.7,
        "max_tokens": 500
    }
}
```

**Output:**
- Dictionary containing the generated answer and relevant metadata

```python
{
    "answer": "Based on the information provided, the benefits of renewable energy include: reduced greenhouse gas emissions, decreasing dependence on fossil fuels, lower long-term operational costs, and creation of new jobs in the green energy sector...",
    "metadata": {  # Optional: additional metadata
        "generation_time": 0.82,  # seconds
        "model": "gpt-4"
    }
}
```

## Implementing a Custom Generator

Here's a step-by-step guide to implementing a custom generator:

### 1. Create a new class

Create a new file in `ici/adapters/generators/` for your custom generator:

```python
"""
Custom LLM generator implementation.
"""

import os
import time
from typing import Dict, Any, List, Optional

from ici.core.interfaces.generator import Generator
from ici.core.exceptions import GeneratorError
from ici.adapters.loggers import StructuredLogger
from ici.utils.config import get_component_config

class CustomLLMGenerator(Generator):
    """
    Generator implementation using a custom language model.
    
    This generator produces responses using a custom LLM based on provided prompts.
    
    Configuration options:
    - model_name: Name of the model to use
    - temperature: Temperature for generation (creativity vs accuracy)
    - max_tokens: Maximum tokens in the response
    """
    
    def __init__(self, logger_name: str = "custom_llm_generator"):
        """
        Initialize the custom LLM generator.
        
        Args:
            logger_name: Name for the logger instance
        """
        self.logger = StructuredLogger(name=logger_name)
        self._is_initialized = False
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        
        # Default configuration
        self._model_name = "your-model-name"
        self._temperature = 0.7
        self._max_tokens = 500
        self._llm_client = None
```

### 2. Implement the initialize method

Load your configuration from config.yaml and initialize the LLM client:

```python
async def initialize(self) -> None:
    """
    Initialize the generator with configuration parameters.
    
    Loads configuration from config.yaml and establishes a connection
    to the language model.
    
    Returns:
        None
        
    Raises:
        GeneratorError: If initialization fails
    """
    try:
        self.logger.info({
            "action": "GENERATOR_INIT_START",
            "message": "Initializing custom LLM generator"
        })
        
        # Load generator configuration
        try:
            generator_config = get_component_config("generators.custom_llm", self._config_path)
            
            # Extract configuration with defaults
            if generator_config:
                self._model_name = generator_config.get("model_name", self._model_name)
                self._temperature = float(generator_config.get("temperature", self._temperature))
                self._max_tokens = int(generator_config.get("max_tokens", self._max_tokens))
                
                # Additional configuration options can be extracted here
                
                self.logger.info({
                    "action": "GENERATOR_CONFIG_LOADED",
                    "message": "Loaded generator configuration",
                    "data": {
                        "model_name": self._model_name,
                        "temperature": self._temperature,
                        "max_tokens": self._max_tokens
                    }
                })
            
        except Exception as e:
            # Use defaults if configuration loading fails
            self.logger.warning({
                "action": "GENERATOR_CONFIG_WARNING",
                "message": f"Failed to load configuration: {str(e)}. Using defaults.",
                "data": {"error": str(e)}
            })
        
        # Initialize the LLM client
        try:
            # Here you would initialize your LLM client
            # For example:
            # from your_llm_client import LLMClient
            # self._llm_client = LLMClient(api_key="your-api-key")
            
            # Placeholder for LLM client
            self._llm_client = self._initialize_llm_client()
            
            self.logger.info({
                "action": "GENERATOR_LLM_INITIALIZED",
                "message": f"Initialized LLM client with model {self._model_name}"
            })
            
        except Exception as e:
            self.logger.error({
                "action": "GENERATOR_LLM_ERROR",
                "message": f"Failed to initialize LLM client: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise GeneratorError(f"Failed to initialize LLM client: {str(e)}") from e
        
        self._is_initialized = True
        
        self.logger.info({
            "action": "GENERATOR_INIT_SUCCESS",
            "message": "Custom LLM generator initialized successfully"
        })
        
    except Exception as e:
        self.logger.error({
            "action": "GENERATOR_INIT_ERROR",
            "message": f"Failed to initialize generator: {str(e)}",
            "data": {"error": str(e), "error_type": type(e).__name__}
        })
        raise GeneratorError(f"Generator initialization failed: {str(e)}") from e

def _initialize_llm_client(self):
    """
    Initialize the LLM client.
    
    This is a placeholder method - implement with your specific LLM client.
    
    Returns:
        The initialized LLM client
    """
    # Replace with actual client initialization
    # Example:
    # from your_llm_client import LLMClient
    # return LLMClient(
    #     api_key=os.environ.get("LLM_API_KEY"),
    #     model_name=self._model_name
    # )
    
    # Return a placeholder for now
    return "llm_client_placeholder"
```

### 3. Implement the generate method

Implement the core logic to generate responses using your language model:

```python
async def generate(
    self, 
    prompt: str, 
    user_id: str = "default", 
    **kwargs
) -> Dict[str, Any]:
    """
    Generate a response using the provided prompt.
    
    Args:
        prompt: The formatted prompt including query and context
        user_id: The user identifier for personalization
        **kwargs: Additional parameters for generation
            - generation_params: Optional generation parameters
            
    Returns:
        Dict[str, Any]: Response containing the answer and metadata
        
    Raises:
        GeneratorError: If generation fails
    """
    if not self._is_initialized:
        raise GeneratorError("Generator not initialized. Call initialize() first.")
    
    try:
        start_time = time.time()
        
        # Extract additional parameters
        generation_params = kwargs.get("generation_params", {})
        
        # Override default parameters with provided ones
        temperature = generation_params.get("temperature", self._temperature)
        max_tokens = generation_params.get("max_tokens", self._max_tokens)
        
        # Generate response using the LLM
        response = await self._generate_with_llm(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            user_id=user_id
        )
        
        # Process the response
        processed_response = self._process_llm_response(response)
        
        # Calculate generation time
        generation_time = time.time() - start_time
        
        # Prepare the final response
        result = {
            "answer": processed_response,
            "metadata": {
                "generation_time": round(generation_time, 2),
                "model": self._model_name
            }
        }
        
        self.logger.info({
            "action": "GENERATOR_RESPONSE_CREATED",
            "message": "Successfully generated response",
            "data": {
                "user_id": user_id,
                "generation_time": generation_time
            }
        })
        
        return result
        
    except Exception as e:
        self.logger.error({
            "action": "GENERATOR_ERROR",
            "message": f"Failed to generate response: {str(e)}",
            "data": {
                "user_id": user_id,
                "error": str(e),
                "error_type": type(e).__name__
            }
        })
        raise GeneratorError(f"Failed to generate response: {str(e)}") from e

async def _generate_with_llm(
    self,
    prompt: str,
    temperature: float,
    max_tokens: int,
    user_id: str
) -> str:
    """
    Generate a response using the LLM.
    
    This is a placeholder method - implement with your specific LLM client.
    
    Args:
        prompt: The formatted prompt
        temperature: The temperature parameter
        max_tokens: Maximum tokens in the response
        user_id: The user identifier
        
    Returns:
        str: The LLM response
    """
    # In a real implementation, you would call your LLM API
    # Example:
    # response = await self._llm_client.generate(
    #     prompt=prompt,
    #     temperature=temperature,
    #     max_tokens=max_tokens,
    #     user_id=user_id
    # )
    # return response.text
    
    # Return a placeholder response for demonstration
    return f"This is a placeholder response for the query. In a real implementation, this would be generated by the LLM based on the provided prompt. The response would be coherent and relevant to the query."

def _process_llm_response(self, response: str) -> str:
    """
    Process the raw LLM response.
    
    Args:
        response: The raw response from the LLM
        
    Returns:
        str: The processed response
    """
    # In a real implementation, you might extract the answer,
    # remove artifacts, filter out unwanted content, etc.
    
    # For this placeholder, we simply return the response
    return response.strip()
```

## Configuration Setup

In your `config.yaml` file, add a section for your generator:

```yaml
generators:
  custom_llm:
    model_name: "gpt-4"
    temperature: 0.7
    max_tokens: 500
    # Additional configuration options specific to your generator
    system_prompt: "You are a helpful assistant that provides accurate information."
    use_streaming: true
```

## Best Practices

1. **Focus on Response Generation**: Remember that the Generator's only job is to generate responses from the provided prompt - all context preparation is handled by the orchestrator.

2. **Prompt Handling**: Process the prompt as provided without attempting to modify its structure.

3. **Error Handling**: Gracefully handle LLM errors and timeouts.

4. **Token Management**: Be mindful of token limits when processing prompts.

5. **Response Processing**: Implement post-processing to clean up responses if needed.

6. **Performance Optimization**: Implement efficient generation and use appropriate model parameters.

7. **Feedback Loop**: Incorporate user feedback to improve generation quality over time.

8. **Output Formatting**: Ensure consistent output format for integration with other components.

## Example Implementations

Explore existing generators for reference:
- `ici/adapters/generators/openai_generator.py` - Uses OpenAI models
- `ici/adapters/generators/huggingface_generator.py` - Uses Hugging Face models (if available in the codebase)

## Conclusion

The Generator component is responsible solely for producing natural language responses based on the provided prompt. It does not handle document retrieval, context preparation, or prompt construction - these tasks are handled by the orchestrator. 

While you typically don't need to implement a custom Generator when simply connecting a new data source, understanding how it works helps you better utilize the system.

If you do need to customize the generation process, this guide provides a foundation for implementing your own Generator with your preferred language model.
