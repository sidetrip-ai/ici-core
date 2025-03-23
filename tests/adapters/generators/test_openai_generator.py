"""
Tests for OpenAIGenerator.

This module contains tests for the OpenAIGenerator implementation.
"""

import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any

from openai.types.chat import ChatCompletion, ChatCompletionMessage, Choice
from ici.adapters.generators.openai_generator import OpenAIGenerator
from ici.core.exceptions import GenerationError


# Create mock response for OpenAI API
def create_mock_completion(content: str = "This is a test response"):
    """Create a mock ChatCompletion object."""
    message = ChatCompletionMessage(role="assistant", content=content, function_call=None, tool_calls=None)
    choice = Choice(index=0, message=message, finish_reason="stop")
    return ChatCompletion(id="test-id", choices=[choice], created=1234567890, model="gpt-4o", object="chat.completion")


@pytest.fixture
def mock_env():
    """Set up environment variables for testing."""
    old_env = os.environ.copy()
    os.environ["OPENAI_API_KEY"] = "test-api-key"
    yield
    os.environ.clear()
    os.environ.update(old_env)


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = {
        "generator": {
            "model": "gpt-4o",
            "default_options": {
                "temperature": 0.5,
                "max_tokens": 500
            },
            "max_retries": 2
        }
    }
    return config


@pytest.fixture
async def generator(mock_env):
    """Create a generator for testing."""
    generator = OpenAIGenerator()
    with patch("ici.utils.config.get_component_config", return_value={
        "model": "gpt-4o",
        "default_options": {"temperature": 0.5, "max_tokens": 500}
    }):
        await generator.initialize()
    return generator


@pytest.mark.asyncio
async def test_initialization(mock_env):
    """Test generator initialization."""
    # Setup
    generator = OpenAIGenerator()
    
    # Mock config
    with patch("ici.utils.config.get_component_config", return_value={
        "model": "gpt-4o",
        "default_options": {"temperature": 0.5, "max_tokens": 500}
    }):
        await generator.initialize()
    
    # Verify
    assert generator._is_initialized
    assert generator._model == "gpt-4o"
    assert generator._default_options["temperature"] == 0.5
    assert generator._default_options["max_tokens"] == 500
    assert generator._client is not None


@pytest.mark.asyncio
async def test_generate(generator):
    """Test text generation."""
    # Setup
    prompt = "Tell me about AI"
    expected_response = "AI is artificial intelligence"
    
    # Mock the API call
    with patch.object(generator._client.chat.completions, "create", 
                     new_callable=AsyncMock,
                     return_value=create_mock_completion(expected_response)):
        
        # Generate text
        response = await generator.generate(prompt)
        
        # Verify
        assert response == expected_response
        generator._client.chat.completions.create.assert_called_once()
        call_kwargs = generator._client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o"
        assert call_kwargs["messages"][0]["content"] == prompt


@pytest.mark.asyncio
async def test_generate_with_options(generator):
    """Test generation with custom options."""
    # Setup
    prompt = "Tell me about AI"
    custom_options = {
        "temperature": 0.2,
        "max_tokens": 200
    }
    
    # Mock the API call
    with patch.object(generator._client.chat.completions, "create", 
                     new_callable=AsyncMock,
                     return_value=create_mock_completion()):
        
        # Generate with custom options
        await generator.generate(prompt, custom_options)
        
        # Verify options were used
        call_kwargs = generator._client.chat.completions.create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.2
        assert call_kwargs["max_tokens"] == 200


@pytest.mark.asyncio
async def test_set_model(generator):
    """Test setting a different model."""
    # Setup
    new_model = "gpt-3.5-turbo"
    
    # Change model
    await generator.set_model(new_model)
    
    # Verify
    assert generator._model == new_model
    
    # Generate to verify the model is used
    with patch.object(generator._client.chat.completions, "create", 
                     new_callable=AsyncMock,
                     return_value=create_mock_completion()):
        
        await generator.generate("Test prompt")
        
        # Verify correct model was used
        call_kwargs = generator._client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == new_model


@pytest.mark.asyncio
async def test_set_default_options(generator):
    """Test setting default options."""
    # Setup
    new_options = {
        "temperature": 0.1,
        "max_tokens": 100,
        "frequency_penalty": 0.5
    }
    
    # Set new default options
    await generator.set_default_options(new_options)
    
    # Verify options were updated
    assert generator._default_options["temperature"] == 0.1
    assert generator._default_options["max_tokens"] == 100
    assert generator._default_options["frequency_penalty"] == 0.5
    
    # Generate to verify options are used
    with patch.object(generator._client.chat.completions, "create", 
                     new_callable=AsyncMock,
                     return_value=create_mock_completion()):
        
        await generator.generate("Test prompt")
        
        # Verify correct options were used
        call_kwargs = generator._client.chat.completions.create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.1
        assert call_kwargs["max_tokens"] == 100
        assert call_kwargs["frequency_penalty"] == 0.5


@pytest.mark.asyncio
async def test_retry_on_rate_limit(generator):
    """Test retrying on rate limit errors."""
    # Setup
    from openai import RateLimitError
    
    # Create a side effect that raises RateLimitError first time, then succeeds
    mock_create = AsyncMock(side_effect=[
        RateLimitError("Rate limit exceeded", response=None, body=None),
        create_mock_completion("Success after retry")
    ])
    
    # Mock API call
    with patch.object(generator._client.chat.completions, "create", mock_create):
        with patch("asyncio.sleep", new_callable=AsyncMock):  # Mock sleep to avoid waiting
            
            # Generate text with retries
            response = await generator.generate("Test prompt")
            
            # Verify retry occurred and succeeded
            assert response == "Success after retry"
            assert mock_create.call_count == 2
            assert asyncio.sleep.called


@pytest.mark.asyncio
async def test_healthcheck(generator):
    """Test the healthcheck method."""
    # Mock successful generation
    with patch.object(generator, "generate", 
                     new_callable=AsyncMock,
                     return_value="Yes, I am operational."):
        
        # Run healthcheck
        health_result = await generator.healthcheck()
        
        # Verify
        assert health_result["healthy"] is True
        assert "is healthy" in health_result["message"]


@pytest.mark.asyncio
async def test_healthcheck_failure(generator):
    """Test healthcheck when generation fails."""
    # Mock failed generation
    with patch.object(generator, "generate", 
                     new_callable=AsyncMock,
                     side_effect=GenerationError("Test error")):
        
        # Run healthcheck
        health_result = await generator.healthcheck()
        
        # Verify
        assert health_result["healthy"] is False
        assert "failed" in health_result["message"]
        assert "error" in health_result["details"] 