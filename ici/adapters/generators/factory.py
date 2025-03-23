"""
Factory for creating Generator implementations.

This module provides a factory function to create the appropriate
Generator implementation based on configuration.
"""

from typing import Optional, Dict, Any

from ici.core.interfaces.generator import Generator
from ici.adapters.generators.openai_generator import OpenAIGenerator
from ici.adapters.generators.langchain_generator import LangchainGenerator
from ici.utils.config import get_component_config


def create_generator(config_type: Optional[str] = None, logger_name: str = "generator") -> Generator:
    """
    Creates a Generator implementation based on configuration.
    
    Args:
        config_type: Optional override for the generator type from config
        logger_name: Name to use for the logger
        
    Returns:
        Generator: An instance of a Generator implementation
        
    Raises:
        ValueError: If the specified generator type is invalid
    """
    # Get generator configuration
    generator_config = get_component_config("generator")
    
    # Determine generator type from config or parameter
    generator_type = config_type or generator_config.get("type", "openai")
    
    # Create appropriate generator
    if generator_type == "openai":
        return OpenAIGenerator(logger_name=logger_name)
    elif generator_type == "langchain":
        return LangchainGenerator(logger_name=logger_name)
    else:
        raise ValueError(f"Invalid generator type: {generator_type}") 