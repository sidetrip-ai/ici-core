# ICI Generator Implementations

This directory contains implementations of the Generator interface for producing responses using various language models.

## Available Generators

### 1. OpenAIGenerator
Direct integration with OpenAI's API for models like GPT-4o.

### 2. LangchainGenerator
A flexible generator that uses LangChain to support multiple model providers.

## Using LangchainGenerator

The LangchainGenerator supports multiple providers through LangChain's unified interface.

### Configuration

In your `config.yaml` file, configure the generator section like this:

```yaml
generator:
  type: "langchain"
  
  # Provider-specific settings
  
  # Option 1: OpenAI
  provider: "openai"
  model: "gpt-4o"
  api_key: "YOUR_OPENAI_API_KEY"  # Or use OPENAI_API_KEY environment variable
  
  # Option 2: Ollama (local or remote)
  # provider: "ollama"
  # model: "llama3"  # Or any model you have in Ollama
  # base_url: "http://localhost:11434"  # Default Ollama URL
  
  # Common settings
  chain_type: "simple"
  memory:
    type: "buffer"
    k: 5
  default_options:
    temperature: 0.7
    max_tokens: 1024
    top_p: 1.0
  max_retries: 3
  base_retry_delay: 1
```

### Provider-Specific Notes

#### OpenAI
- Requires an API key
- Supports all OpenAI models including GPT-4o
- Parameter mapping is direct (temperature, max_tokens, etc.)

#### Ollama
- Requires Ollama to be running (locally or on a remote server)
- Specify the base_url (default: http://localhost:11434)
- Parameter mapping:
  - temperature → temperature
  - max_tokens → num_predict
  - top_p → top_p

### Memory and Conversation History

The LangchainGenerator supports conversation memory through LangChain's memory components:

```yaml
memory:
  type: "buffer"  # ConversationBufferMemory
  k: 5  # Number of conversation turns to remember
```

## Troubleshooting

### NumPy Compatibility
If you encounter errors about NumPy 1.x vs 2.x compatibility, downgrade NumPy:

```bash
pip install numpy==1.24.3 --force-reinstall
```

### API Connection Issues
- Check your API key or credentials
- For Ollama, ensure the Ollama server is running and accessible
- Check network connectivity to remote services

## Extending

To add support for additional providers:
1. Update the `_get_credentials()` method for the new provider
2. Add provider-specific logic in `initialize()`, `generate()`, `set_model()`, and `set_default_options()`
3. Import the necessary LangChain components
4. Update dependencies in setup.py 