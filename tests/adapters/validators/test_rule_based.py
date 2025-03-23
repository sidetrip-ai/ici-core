"""
Tests for RuleBasedValidator.

This module contains tests for the RuleBasedValidator implementation.
"""

import pytest
from typing import Dict, Any

from ici.adapters.validators.rule_based import RuleBasedValidator
from ici.core.exceptions import ValidationError


@pytest.fixture
async def validator():
    """Create and initialize a RuleBasedValidator for testing."""
    validator = RuleBasedValidator()
    await validator.initialize()
    return validator


@pytest.mark.asyncio
async def test_validate_command_line_source(validator):
    """Test validation with COMMAND_LINE source."""
    # Setup
    rules = []  # Not used in current implementation
    failure_reasons = []
    
    # Valid source (COMMAND_LINE)
    command_line_context = {"source": "COMMAND_LINE"}
    result = await validator.validate("test input", command_line_context, rules, failure_reasons)
    assert result is True
    assert len(failure_reasons) == 0
    
    # Invalid source (not COMMAND_LINE)
    failure_reasons.clear()
    web_context = {"source": "WEB"}
    result = await validator.validate("test input", web_context, rules, failure_reasons)
    assert result is False
    assert len(failure_reasons) == 1
    assert "not from COMMAND_LINE" in failure_reasons[0]
    
    # Missing source
    failure_reasons.clear()
    empty_context = {}
    result = await validator.validate("test input", empty_context, rules, failure_reasons)
    assert result is False
    assert len(failure_reasons) == 1


@pytest.mark.asyncio
async def test_healthcheck(validator):
    """Test the healthcheck method."""
    # Run healthcheck
    health_result = await validator.healthcheck()
    
    # Verify response structure
    assert isinstance(health_result, dict)
    assert "healthy" in health_result
    assert "message" in health_result
    assert "details" in health_result
    
    # Should be healthy
    assert health_result["healthy"] is True 