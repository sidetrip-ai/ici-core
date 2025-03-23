"""
Tests for the LangchainGenerator implementation.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

import asyncio
from ici.adapters.generators.langchain_generator import LangchainGenerator
from ici.core.exceptions import GenerationError


@pytest.fixture
def mock_config():
    """Fixture for generator config mock"""
    return {
        "provider": "openai",
        "model": "gpt-4o",
        "api_key": "test-key-123",
        "chain_type": "simple",
        "default_options": {
            "temperature": 0.5,
            "max_tokens": 500,
            "top_p": 0.9,
        },
        "memory": {
            "type": "buffer",
            "k": 3
        },
        "max_retries": 2,
        "base_retry_delay": 0.1
    }


@pytest.fixture
def generator():
    """Fixture to create a LangchainGenerator instance"""
    return LangchainGenerator(logger_name="test_logger")


@pytest.mark.asyncio
async def test_initialization(generator, mock_config):
    """Test the generator initialization with mocked configuration"""
    with patch('ici.adapters.generators.langchain_generator.get_component_config', return_value=mock_config):
        with patch('ici.adapters.generators.langchain_generator.ChatOpenAI'):
            with patch('ici.adapters.generators.langchain_generator.LLMChain'):
                with patch('ici.adapters.generators.langchain_generator.ConversationBufferMemory'):
                    await generator.initialize()
                    
                    assert generator._is_initialized
                    assert generator._provider == "openai"
                    assert generator._model == "gpt-4o"
                    assert generator._chain_type == "simple"
                    assert generator._default_options["temperature"] == 0.5
                    assert generator._default_options["max_tokens"] == 500
                    assert generator._max_retries == 2


@pytest.mark.asyncio
async def test_generate(generator, mock_config):
    """Test the generate method with a mocked LangChain response"""
    # Mock response from LangChain
    mock_response = "Yes, I am operational."
    
    with patch('ici.adapters.generators.langchain_generator.get_component_config', return_value=mock_config):
        with patch('ici.adapters.generators.langchain_generator.ChatOpenAI'):
            with patch('ici.adapters.generators.langchain_generator.LLMChain'):
                with patch('ici.adapters.generators.langchain_generator.ConversationBufferMemory'):
                    # Initialize generator
                    await generator.initialize()
                    
                    # Override async to_thread call to return our mock response
                    with patch('asyncio.to_thread', return_value=mock_response):
                        # Call generate
                        result = await generator.generate("Hello, are you working?")
                        
                        # Verify result
                        assert result == mock_response


@pytest.mark.asyncio
async def test_generate_with_options(generator, mock_config):
    """Test the generate method with custom options"""
    # Mock response from LangChain
    mock_response = "Custom response with different temperature."
    
    with patch('ici.adapters.generators.langchain_generator.get_component_config', return_value=mock_config):
        with patch('ici.adapters.generators.langchain_generator.ChatOpenAI'):
            with patch('ici.adapters.generators.langchain_generator.LLMChain'):
                with patch('ici.adapters.generators.langchain_generator.ConversationBufferMemory'):
                    # Initialize generator
                    await generator.initialize()
                    
                    # Override async to_thread call to return our mock response
                    with patch('asyncio.to_thread', return_value=mock_response):
                        # Call generate with custom options
                        result = await generator.generate(
                            "Test prompt",
                            {"temperature": 0.2, "max_tokens": 200}
                        )
                        
                        # Verify result
                        assert result == mock_response


@pytest.mark.asyncio
async def test_healthcheck(generator, mock_config):
    """Test the healthcheck method"""
    # Mock successful generate response
    mock_response = "Yes, I am operational."
    
    with patch('ici.adapters.generators.langchain_generator.get_component_config', return_value=mock_config):
        with patch('ici.adapters.generators.langchain_generator.ChatOpenAI'):
            with patch('ici.adapters.generators.langchain_generator.LLMChain'):
                with patch('ici.adapters.generators.langchain_generator.ConversationBufferMemory'):
                    # Initialize generator
                    await generator.initialize()
                    
                    # Mock the generate method
                    with patch.object(generator, 'generate', return_value=mock_response):
                        health_result = await generator.healthcheck()
                        
                        assert health_result["healthy"] is True
                        assert "Generator is healthy" in health_result["message"]


@pytest.mark.asyncio
async def test_initialization_error(generator):
    """Test error handling during initialization"""
    with patch('ici.adapters.generators.langchain_generator.get_component_config', side_effect=Exception("Config error")):
        with pytest.raises(GenerationError) as excinfo:
            await generator.initialize()
        
        assert "Generator initialization failed" in str(excinfo.value)


@pytest.mark.asyncio
async def test_set_model(generator, mock_config):
    """Test the set_model method"""
    with patch('ici.adapters.generators.langchain_generator.get_component_config', return_value=mock_config):
        with patch('ici.adapters.generators.langchain_generator.ChatOpenAI') as mock_chat_openai:
            with patch('ici.adapters.generators.langchain_generator.LLMChain'):
                with patch('ici.adapters.generators.langchain_generator.ConversationBufferMemory'):
                    # Initialize generator
                    await generator.initialize()
                    
                    # Change model
                    await generator.set_model("gpt-3.5-turbo")
                    
                    assert generator._model == "gpt-3.5-turbo"
                    # Verify that a new ChatOpenAI instance was created
                    assert mock_chat_openai.call_count >= 2 