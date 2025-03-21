"""
Tests for BasicPromptBuilder.

This module contains tests for the BasicPromptBuilder implementation.
"""

import pytest
from typing import Dict, Any

from ici.adapters.prompt_builders.basic_prompt_builder import BasicPromptBuilder
from ici.core.exceptions import PromptBuilderError


@pytest.fixture
async def prompt_builder():
    """Create and initialize a BasicPromptBuilder for testing."""
    builder = BasicPromptBuilder()
    await builder.initialize()
    return builder


@pytest.mark.asyncio
async def test_build_prompt_with_documents(prompt_builder):
    """Test building a prompt with documents."""
    # Setup
    input_text = "What is the capital of France?"
    documents = [
        {"text": "Paris is the capital of France."},
        {"text": "France is a country in Western Europe."}
    ]
    
    # Build prompt
    prompt = await prompt_builder.build_prompt(input_text, documents)
    
    # Verify
    assert "Paris is the capital of France" in prompt
    assert "France is a country in Western Europe" in prompt
    assert "What is the capital of France?" in prompt


@pytest.mark.asyncio
async def test_build_prompt_no_documents(prompt_builder):
    """Test building a prompt with no documents."""
    # Setup
    input_text = "What is the capital of France?"
    
    # Build prompt with empty documents list
    prompt = await prompt_builder.build_prompt(input_text, [])
    
    # Verify fallback template is used
    assert "general knowledge" in prompt
    assert "What is the capital of France?" in prompt


@pytest.mark.asyncio
async def test_build_prompt_with_max_length(prompt_builder):
    """Test building a prompt with max_context_length."""
    # Setup
    input_text = "What is AI?"
    documents = [{"text": "Artificial Intelligence (AI) is a broad field of computer science..." * 20}]
    max_length = 100
    
    # Build prompt with length restriction
    prompt = await prompt_builder.build_prompt(input_text, documents, max_length)
    
    # Count context length (excluding template parts and question)
    template = prompt_builder._template
    question_part = template.split("{context}")[1].format(question=input_text)
    context_part = prompt[:prompt.index(question_part)]
    
    # Verify context is truncated
    assert len(context_part) <= max_length + len(template.split("{context}")[0])


@pytest.mark.asyncio
async def test_set_template(prompt_builder):
    """Test setting a custom template."""
    # Setup
    custom_template = "Custom {context}\n\nQuery: {question}"
    
    # Set custom template
    await prompt_builder.set_template(custom_template)
    
    # Build prompt
    input_text = "test question"
    documents = [{"text": "test document"}]
    prompt = await prompt_builder.build_prompt(input_text, documents)
    
    # Verify
    assert prompt.startswith("Custom test document")
    assert "Query: test question" in prompt


@pytest.mark.asyncio 
async def test_set_fallback_template(prompt_builder):
    """Test setting a custom fallback template."""
    # Setup
    custom_fallback = "No information available. Please answer: {question}"
    
    # Set custom fallback template
    prompt_builder.set_fallback_template(custom_fallback)
    
    # Build prompt with no documents
    input_text = "test question"
    prompt = await prompt_builder.build_prompt(input_text, [])
    
    # Verify
    assert prompt == "No information available. Please answer: test question"


@pytest.mark.asyncio
async def test_invalid_template(prompt_builder):
    """Test setting an invalid template."""
    # Setup - missing {question} placeholder
    invalid_template = "Context: {context}"
    
    # Attempt to set invalid template
    with pytest.raises(PromptBuilderError):
        await prompt_builder.set_template(invalid_template)


@pytest.mark.asyncio
async def test_healthcheck(prompt_builder):
    """Test the healthcheck method."""
    # Run healthcheck
    health_result = await prompt_builder.healthcheck()
    
    # Verify
    assert isinstance(health_result, dict)
    assert "healthy" in health_result
    assert health_result["healthy"] is True
    assert "message" in health_result
    assert "details" in health_result 