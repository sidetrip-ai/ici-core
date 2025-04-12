"""
Tests for DefaultOrchestrator.

This module contains tests for the DefaultOrchestrator implementation.
"""

import os
import time
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any, List

from ici.adapters.orchestrators.default_orchestrator import DefaultOrchestrator
from ici.core.exceptions import OrchestratorError, ValidationError


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = {
        "orchestrator": {
            "num_results": 3,
            "similarity_threshold": 0.7,
            "rules_source": "config",
            "validation_rules": {
                "default": [],
                "user123": [{"type": "some_rule"}]
            },
            "error_messages": {
                "validation_failed": "Custom validation error"
            },
            "user_context": {
                "user123": {"permission_level": "admin"}
            }
        }
    }
    return config


@pytest.fixture
async def orchestrator():
    """
    Create an orchestrator instance with mocked components.
    """
    # Create orchestrator
    orchestrator = DefaultOrchestrator()
    
    # Patch the get_component_config function
    with patch("ici.utils.config.get_component_config", return_value={
        "num_results": 3,
        "similarity_threshold": 0.7,
        "validation_rules": {"default": []}
    }):
        # Mock all components
        with patch.object(orchestrator, "_initialize_components", new_callable=AsyncMock):
            # Initialize the orchestrator
            await orchestrator.initialize()
            
            # Manually set up mocked components
            orchestrator._validator = AsyncMock()
            orchestrator._validator.validate = AsyncMock(return_value=True)
            orchestrator._validator.healthcheck = AsyncMock(return_value={"healthy": True})
            
            orchestrator._vector_store = AsyncMock()
            orchestrator._vector_store.search = AsyncMock(return_value=[
                {"text": "Document 1", "metadata": {"id": "1"}},
                {"text": "Document 2", "metadata": {"id": "2"}}
            ])
            orchestrator._vector_store.healthcheck = AsyncMock(return_value={"healthy": True})
            
            orchestrator._prompt_builder = AsyncMock()
            orchestrator._prompt_builder.build_prompt = AsyncMock(return_value="Test prompt")
            orchestrator._prompt_builder.healthcheck = AsyncMock(return_value={"healthy": True})
            
            orchestrator._generator = AsyncMock()
            orchestrator._generator.generate = AsyncMock(return_value="Test response")
            orchestrator._generator.healthcheck = AsyncMock(return_value={"healthy": True})
            
    return orchestrator


@pytest.mark.asyncio
async def test_initialization():
    """Test orchestrator initialization."""
    # Setup
    orchestrator = DefaultOrchestrator()
    
    # Mock components and config
    with patch("ici.utils.config.get_component_config", return_value={
        "num_results": 5,
        "similarity_threshold": 0.8
    }):
        with patch.object(orchestrator, "_initialize_components", new_callable=AsyncMock):
            # Initialize
            await orchestrator.initialize()
            
            # Verify configuration loaded
            assert orchestrator._is_initialized is True
            assert orchestrator._num_results == 5
            assert orchestrator._similarity_threshold == 0.8
            
            # Verify components initialized
            orchestrator._initialize_components.assert_called_once()


@pytest.mark.asyncio
async def test_process_query(orchestrator):
    """Test query processing end-to-end."""
    # Setup
    source = "COMMAND_LINE"
    user_id = "test_user"
    query = "What is the meaning of life?"
    additional_info = {"session_id": "12345"}
    
    # Process the query
    response = await orchestrator.process_query(source, user_id, query, additional_info)
    
    # Verify all steps were called
    orchestrator._validator.validate.assert_called_once()
    orchestrator._vector_store.search.assert_called_once()
    orchestrator._prompt_builder.build_prompt.assert_called_once()
    orchestrator._generator.generate.assert_called_once()
    
    # Verify response
    assert response == "Test response"


@pytest.mark.asyncio
async def test_validation_failure(orchestrator):
    """Test handling of validation failure."""
    # Setup - make validator return False
    orchestrator._validator.validate = AsyncMock(return_value=False)
    orchestrator._error_messages["validation_failed"] = "Validation failed message"
    
    # Process query
    response = await orchestrator.process_query("COMMAND_LINE", "test_user", "Bad query", {})
    
    # Verify validation called but not other components
    orchestrator._validator.validate.assert_called_once()
    orchestrator._vector_store.search.assert_not_called()
    orchestrator._prompt_builder.build_prompt.assert_not_called()
    orchestrator._generator.generate.assert_not_called()
    
    # Verify error message
    assert response == "Validation failed message"


@pytest.mark.asyncio
async def test_search_failure(orchestrator):
    """Test handling of search failure."""
    # Setup - make search raise exception
    orchestrator._vector_store.search = AsyncMock(side_effect=Exception("Search failed"))
    
    # Process query
    response = await orchestrator.process_query("COMMAND_LINE", "test_user", "Test query", {})
    
    # Verify fallback behavior
    orchestrator._validator.validate.assert_called_once()
    orchestrator._vector_store.search.assert_called_once()
    
    # Should still try to build prompt and generate response with empty docs
    orchestrator._prompt_builder.build_prompt.assert_called_once()
    orchestrator._generator.generate.assert_called_once()
    
    # Response should be successful
    assert response == "Test response"


@pytest.mark.asyncio
async def test_get_rules():
    """Test retrieving rules for a user."""
    # Setup
    orchestrator = DefaultOrchestrator()
    orchestrator._config = {
        "validation_rules": {
            "default": [{"type": "default_rule"}],
            "user123": [{"type": "user_specific_rule"}]
        }
    }
    orchestrator._rules_source = "config"
    orchestrator._is_initialized = True
    
    # Get rules for specific user
    rules = orchestrator.get_rules("user123")
    assert len(rules) == 1
    assert rules[0]["type"] == "user_specific_rule"
    
    # Get rules for non-existent user (should get default)
    rules = orchestrator.get_rules("unknown_user")
    assert len(rules) == 1
    assert rules[0]["type"] == "default_rule"


@pytest.mark.asyncio
async def test_build_context():
    """Test building context for a user."""
    # Setup
    orchestrator = DefaultOrchestrator()
    orchestrator._config = {
        "user_context": {
            "user123": {"permission_level": "admin"}
        }
    }
    orchestrator._is_initialized = True
    
    # Build context for specific user
    context = await orchestrator.build_context("user123")
    assert context["user_id"] == "user123"
    assert "timestamp" in context
    assert context["permission_level"] == "admin"
    
    # Build context for non-existent user
    context = await orchestrator.build_context("unknown_user")
    assert context["user_id"] == "unknown_user"
    assert "timestamp" in context
    assert "permission_level" not in context


@pytest.mark.asyncio
async def test_configure(orchestrator):
    """Test configuration update."""
    # Setup initial config
    orchestrator._num_results = 3
    orchestrator._similarity_threshold = 0.7
    
    # Update configuration
    new_config = {
        "num_results": 5,
        "similarity_threshold": 0.9,
        "rules_source": "database",
        "error_messages": {
            "validation_failed": "New validation error"
        }
    }
    await orchestrator.configure(new_config)
    
    # Verify updated
    assert orchestrator._num_results == 5
    assert orchestrator._similarity_threshold == 0.9
    assert orchestrator._rules_source == "database"
    assert orchestrator._error_messages["validation_failed"] == "New validation error"


@pytest.mark.asyncio
async def test_healthcheck(orchestrator):
    """Test health check functionality."""
    # Setup mocked component healths
    orchestrator._validator.healthcheck = AsyncMock(return_value={"healthy": True})
    orchestrator._vector_store.healthcheck = AsyncMock(return_value={"healthy": True})
    orchestrator._prompt_builder.healthcheck = AsyncMock(return_value={"healthy": True})
    orchestrator._generator.healthcheck = AsyncMock(return_value={"healthy": True})
    
    # Run healthcheck
    health = await orchestrator.healthcheck()
    
    # Verify components were checked
    orchestrator._validator.healthcheck.assert_called_once()
    orchestrator._vector_store.healthcheck.assert_called_once()
    orchestrator._prompt_builder.healthcheck.assert_called_once()
    orchestrator._generator.healthcheck.assert_called_once()
    
    # Verify health result
    assert health["healthy"] is True
    assert "message" in health
    assert "components" in health
    assert len(health["components"]) == 4 