"""
Configuration utilities for the ICI framework.

This module provides functions for loading and accessing configuration from YAML files.
"""

import os
import re
import yaml
from typing import Dict, Any, Optional, Union

from ici.core.exceptions import ConfigurationError


def _process_env_vars(value: Any) -> Any:
    """
    Process a configuration value to replace environment variable references.
    
    Replaces any string containing $ENV_VAR or ${ENV_VAR} with the corresponding
    environment variable value.
    
    Args:
        value: The configuration value to process
        
    Returns:
        The processed value with environment variables substituted
    """
    if isinstance(value, str):
        # Pattern to match ${VAR} and $VAR formats
        pattern = r"\${([a-zA-Z0-9_]+)}|\$([a-zA-Z0-9_]+)"
        
        def replace_env_var(match):
            env_var = match.group(1) or match.group(2)
            env_value = os.environ.get(env_var)
            if env_value is None:
                return match.group(0)  # Keep original if not found
            return env_value
            
        return re.sub(pattern, replace_env_var, value)
    elif isinstance(value, dict):
        return {k: _process_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_process_env_vars(item) for item in value]
    else:
        return value


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.
    
    Args:
        config_path: Path to the configuration file. If None, uses the environment
                    variable ICI_CONFIG_PATH or defaults to 'config.yaml'
                    
    Returns:
        Dict[str, Any]: The loaded configuration with environment variables processed
        
    Raises:
        ConfigurationError: If the configuration file cannot be loaded
    """
    # Determine the configuration path
    if config_path is None:
        config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
    
    try:
        # Check if the file exists
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        # Load the configuration
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            
        # Ensure config is a dictionary
        if not isinstance(config, dict):
            raise ValueError(f"Invalid configuration format: expected dictionary, got {type(config)}")
        
        # Process environment variables in the configuration
        config = _process_env_vars(config)
            
        return config
        
    except FileNotFoundError as e:
        # Re-raise as ConfigurationError with the original message
        raise ConfigurationError(f"Configuration file error: {str(e)}")
    except yaml.YAMLError as e:
        # YAML parsing error
        raise ConfigurationError(f"YAML parsing error: {str(e)}")
    except Exception as e:
        # Catch any other exceptions
        raise ConfigurationError(f"Failed to load configuration: {str(e)}")


def _map_legacy_path_to_new(component_name: str) -> str:
    """
    Maps legacy component paths to their new locations in the restructured config.
    
    Args:
        component_name: The original component path
        
    Returns:
        str: The new component path in the restructured config
    """
    # Map of old paths to new paths
    path_mapping = {
        # System components
        "loggers": "system.loggers",
        "loggers.structured_logger": "system.loggers.structured_logger",
        "state_manager": "system.state_manager",
        "validator": "system.validator",
        "chat_history_manager": "system.chat_history_manager",
        "user_id_generator": "system.user_id_generator",
        
        # Orchestrator components
        "embedders": "orchestrator.embedder",
        "embedders.sentence_transformer": "orchestrator.embedder.sentence_transformer",
        "generator": "orchestrator.generator",
        "vector_stores": "orchestrator.vector_store",
        "vector_stores.chroma": "orchestrator.vector_store.chroma",
        "prompt_builder": "orchestrator.prompt_builder",
        "orchestrator": "orchestrator",
        
        # Pipeline components
        "pipelines": "orchestrator.pipelines",
        "pipelines.telegram": "orchestrator.pipelines.telegram",
        "pipelines.whatsapp": "orchestrator.pipelines.whatsapp",
        "pipelines.telegram.ingestor.telegram": "orchestrator.pipelines.telegram.ingestor.telegram",
        "pipelines.whatsapp.ingestor.whatsapp": "orchestrator.pipelines.whatsapp.ingestor.whatsapp",
        "ingestors": "orchestrator.pipelines",
        "ingestors.telegram": "orchestrator.pipelines.telegram.ingestor.telegram",
        "ingestors.whatsapp": "orchestrator.pipelines.whatsapp.ingestor.whatsapp",
        "preprocessors": "orchestrator.pipelines",
        "preprocessors.telegram": "orchestrator.pipelines.telegram.preprocessor",
        "preprocessors.whatsapp": "orchestrator.pipelines.whatsapp.preprocessor",
    }
    
    return path_mapping.get(component_name, component_name)


def get_component_config(component_name: str, config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration for a specific component.
    
    Args:
        component_name: Name of the component (e.g., 'telegram', 'vector_store')
        config_path: Optional path to the configuration file
        
    Returns:
        Dict[str, Any]: The component's configuration section
        
    Raises:
        ConfigurationError: If the configuration cannot be loaded or the component
                           section is not found
    """
    try:
        # Load the full configuration
        config = load_config(config_path)

        # Map legacy path to new structure path
        mapped_component_name = _map_legacy_path_to_new(component_name)
        components = mapped_component_name.split(".")

        component_config = config

        # Only print if console output is enabled in logger configuration
        console_output_enabled = config.get("system", {}).get("loggers", {}).get("structured_logger", {}).get("console_output", True)
        logger_level = config.get("system", {}).get("loggers", {}).get("structured_logger", {}).get("level", "INFO")
        if console_output_enabled and logger_level == "DEBUG":
            print({
                "action": "CONFIG_LOADED",
                "message": "Configuration loaded successfully",
                "data": {"config": component_config}
            })

        for component in components:
            component_config = component_config.get(component, {})
        
        # Ensure component_config is a dictionary
        if not isinstance(component_config, dict):
            raise ValueError(
                f"Invalid configuration for component '{component_name}': "
                f"expected dictionary, got {type(component_config)}"
            )
            
        return component_config
        
    except ConfigurationError:
        # Re-raise ConfigurationError from load_config
        raise
    except Exception as e:
        # Catch any other exceptions
        raise ConfigurationError(f"Failed to get configuration for component '{component_name}': {str(e)}") 