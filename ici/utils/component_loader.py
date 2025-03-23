"""
Component loader utility for dynamic instantiation of components.

This module provides utilities for dynamically loading and initializing
components from configuration based on class paths.
"""

import importlib
from typing import Any, Dict, Optional, Type, TypeVar

from ici.core.exceptions import ComponentLoadError

T = TypeVar('T')

def load_component_class(class_path: str) -> Type[Any]:
    """
    Dynamically load a class from a fully qualified path string.
    
    Args:
        class_path: Fully qualified class path (e.g., 'ici.adapters.ingestors.telegram.TelegramIngestor')
        
    Returns:
        Type[Any]: The loaded class
        
    Raises:
        ComponentLoadError: If the class cannot be loaded
    """
    try:
        # Split into module path and class name
        module_path, class_name = class_path.rsplit('.', 1)
        
        # Import the module
        module = importlib.import_module(module_path)
        
        # Get the class
        component_class = getattr(module, class_name)
        
        return component_class
    
    except ImportError as e:
        raise ComponentLoadError(f"Failed to import module for component {class_path}: {str(e)}")
    except AttributeError as e:
        raise ComponentLoadError(f"Class not found in module: {class_path}: {str(e)}")
    except Exception as e:
        raise ComponentLoadError(f"Failed to load component class {class_path}: {str(e)}")

async def instantiate_component(class_path: str, config: Optional[Dict[str, Any]] = None) -> Any:
    """
    Dynamically instantiate a component from its class path and initialize it.
    
    Args:
        class_path: Fully qualified class path
        config: Configuration for the component
        
    Returns:
        Any: The instantiated and initialized component
        
    Raises:
        ComponentLoadError: If the component cannot be instantiated or initialized
    """
    try:
        # Load the class
        component_class = load_component_class(class_path)
        
        # Create an instance with config if provided
        component = component_class() if config is None else component_class(**config)
        
        # Initialize the component if it has an initialize method
        if hasattr(component, 'initialize') and callable(component.initialize):
            # Check if initialize is a coroutine function
            if hasattr(component.initialize, '__await__'):
                await component.initialize()
            else:
                component.initialize()
        
        return component
    
    except ComponentLoadError:
        # Re-raise ComponentLoadError from load_component_class
        raise
    except Exception as e:
        raise ComponentLoadError(f"Failed to instantiate or initialize component {class_path}: {str(e)}")

def load_component_by_type(component_type: str, component_config: Dict[str, Any], base_class: Type[T]) -> T:
    """
    Load a component by type string and validate it against a base class.
    
    Args:
        component_type: String identifier for the component type
        component_config: Configuration for the component
        base_class: Base class that the component should inherit from
        
    Returns:
        T: The instantiated component
        
    Raises:
        ComponentLoadError: If the component cannot be loaded or is not a subclass of base_class
    """
    try:
        # Load the class
        component_class = load_component_class(component_type)
        
        # Verify it's a subclass of the base class
        if not issubclass(component_class, base_class):
            raise ComponentLoadError(
                f"Component {component_type} is not a subclass of {base_class.__name__}"
            )
        
        # Create an instance with config
        return component_class(**component_config)
    
    except ComponentLoadError:
        # Re-raise ComponentLoadError from other functions
        raise
    except Exception as e:
        raise ComponentLoadError(f"Failed to load component {component_type}: {str(e)}") 