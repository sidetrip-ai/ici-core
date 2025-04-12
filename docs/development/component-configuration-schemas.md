# Component Configuration Schemas

This document provides guidelines and specifications for defining JSON schemas for component configurations within the ICI system.

## Overview

The ICI system uses JSON Schema for validating component configurations at runtime. This approach ensures:

1. **Type Safety**: Ensures parameters have the correct types
2. **Required Parameters**: Validates that all required parameters are provided
3. **Constraint Validation**: Enforces value constraints (min/max, patterns, etc.)
4. **Nested Validation**: Recursively validates nested configuration structures
5. **Self-Documentation**: Schemas document the configuration requirements

## Schema Hierarchy

Configuration schemas follow a hierarchical structure:

1. **Base Interface Schemas**: Define minimum requirements for each component type (Ingestor, Preprocessor, etc.)
2. **Implementation Schemas**: Extend base schemas with implementation-specific requirements
3. **Pipeline Schemas**: Define the structure for connecting multiple components

## Base Interface Schemas

Each component interface has a base schema defining minimum required parameters:

```python
BASE_SCHEMAS = {
    "Ingestor": {
        "type": "object",
        "required": ["type"],
        "properties": {
            "type": {"type": "string"},
            "config": {
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Unique identifier for this ingestor"
                    }
                }
            }
        }
    },
    
    "Preprocessor": {
        "type": "object",
        "required": ["type"],
        "properties": {
            "type": {"type": "string"},
            "config": {
                "type": "object",
                "properties": {
                    "chunk_size": {
                        "type": "integer",
                        "description": "Maximum size of text chunks",
                        "default": 512
                    }
                }
            }
        }
    },
    
    # Other interface schemas...
}
```

## Implementation Schema Definition

Component implementations extend the base schema with their specific requirements:

```python
class WhatsAppIngestor(Ingestor, ComponentConfigSchema):
    def get_component_schema(self) -> Dict[str, Any]:
        """
        Returns schema for WhatsApp-specific configuration.
        """
        return {
            "properties": {
                "config": {
                    "type": "object",
                    "required": ["service_url"],
                    "properties": {
                        "service_url": {
                            "type": "string",
                            "description": "URL of the WhatsApp Web service",
                            "pattern": r"^https?://[a-zA-Z0-9.-]+(:[0-9]+)?(/.*)?$"
                        },
                        "session_id": {
                            "type": "string",
                            "default": "default_session"
                        }
                    }
                }
            }
        }
```

## Schema Structure Specification

When defining a component schema, follow these guidelines:

### 1. Root Structure

Component schemas should have this structure:

```python
{
    "properties": {
        "config": {
            "type": "object",
            "required": [...],  # List of required parameters
            "properties": {
                # Parameter definitions
            }
        }
    }
}
```

### 2. Parameter Definitions

Define each parameter with:

```python
"parameter_name": {
    "type": "string|integer|number|boolean|array|object",
    "description": "Human-readable description of the parameter",
    # Additional constraints as needed
}
```

### 3. Common Parameter Constraints

Use these constraints as appropriate:

- **Strings**:
  - `"pattern"`: Regular expression pattern
  - `"minLength"`, `"maxLength"`: Length constraints
  - `"enum"`: List of allowed values

- **Numbers**:
  - `"minimum"`, `"maximum"`: Value range
  - `"exclusiveMinimum"`, `"exclusiveMaximum"`: Exclusive range

- **Arrays**:
  - `"items"`: Schema for array items
  - `"minItems"`, `"maxItems"`: Size constraints
  - `"uniqueItems"`: Whether items must be unique

- **Objects**:
  - `"required"`: Array of required properties
  - `"properties"`: Nested property definitions
  - `"additionalProperties"`: Whether additional properties are allowed

- **All Types**:
  - `"default"`: Default value if not specified

## Examples

### Example 1: Simple Ingestor Schema

```python
def get_component_schema(self) -> Dict[str, Any]:
    return {
        "properties": {
            "config": {
                "type": "object",
                "required": ["api_key"],
                "properties": {
                    "api_key": {
                        "type": "string",
                        "description": "API key for authentication"
                    },
                    "request_timeout": {
                        "type": "integer",
                        "description": "Request timeout in seconds",
                        "minimum": 1,
                        "maximum": 60,
                        "default": 10
                    }
                }
            }
        }
    }
```

### Example 2: Complex Nested Schema

```python
def get_component_schema(self) -> Dict[str, Any]:
    return {
        "properties": {
            "config": {
                "type": "object",
                "required": ["service_url"],
                "properties": {
                    "service_url": {
                        "type": "string",
                        "description": "Service URL"
                    },
                    "auth": {
                        "type": "object",
                        "description": "Authentication configuration",
                        "required": ["type"],
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["api_key", "oauth", "basic"],
                                "description": "Authentication type"
                            },
                            "credentials": {
                                "type": "object",
                                "description": "Authentication credentials"
                            }
                        }
                    },
                    "filters": {
                        "type": "array",
                        "description": "Data filters",
                        "items": {
                            "type": "object",
                            "required": ["field", "operator", "value"],
                            "properties": {
                                "field": {"type": "string"},
                                "operator": {
                                    "type": "string",
                                    "enum": ["eq", "gt", "lt", "contains"]
                                },
                                "value": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    }
```

## Best Practices

1. **Thorough Descriptions**: Always include clear descriptions for all parameters
2. **Sensible Defaults**: Provide default values for optional parameters when possible
3. **Appropriate Constraints**: Set value constraints that prevent invalid configurations
4. **Minimal Requirements**: Only mark parameters as required if they are truly necessary
5. **Forward Compatibility**: Design schemas to accommodate future extensions

## Validation Process

The system validates component configurations in this sequence:

1. **Structure Validation**: Validates the structural format of the configuration
2. **Interface Validation**: Validates against the base interface schema
3. **Implementation Validation**: Validates against the implementation-specific schema
4. **Default Application**: Applies default values for missing optional parameters

## Integration with Dynamic Ingestion Pipeline

The DefaultIngestionPipeline uses these schemas during component loading:

```python
async def _load_component(self, component_config, interface_class):
    # Get component class based on type
    component_class = self._import_component_class(component_config["type"])
    
    # Create instance
    component = component_class()
    
    # Validate configuration against the component's schema
    if isinstance(component, ComponentConfigSchema):
        schema = component.get_config_schema()
        validate(instance=component_config.get("config", {}), schema=schema)
    
    # Initialize the component
    await component.initialize(component_config.get("config", {}))
    
    return component
```

## Conclusion

By following these guidelines, you can create clear, consistent, and robust configuration schemas for ICI components. This approach ensures that configuration errors are caught early with helpful error messages, making the system more reliable and easier to use.

## Implementation Plan (Agreed Upon)

Based on recent discussions, the following plan will be followed to implement schema validation, starting with `Ingestor` and `Preprocessor` components:

1.  **Core Schema Infrastructure (`ici/components/schema.py`):**
    *   Define an Abstract Base Class (ABC) `ComponentConfigSchema` with an abstract method `get_component_schema(self) -> Dict[str, Any]`.
    *   Define base JSON schemas (as Python dicts) for `Ingestor` (`BASE_INGESTOR_SCHEMA`) and `Preprocessor` (`BASE_PREPROCESSOR_SCHEMA`) interfaces, containing minimal required fields.

2.  **Modify Base Component Classes (`ici/components/base.py`):**
    *   Make base `Ingestor` and `Preprocessor` classes inherit from `ComponentConfigSchema`.
    *   Modify their `initialize(self, config: Dict[str, Any])` methods:
        *   Call `schema = self.get_component_schema()` to get the combined schema from the concrete subclass.
        *   Validate the input `config` against `schema` using `jsonschema.validate(instance=config, schema=schema)`.
        *   Wrap validation in `try...except jsonschema.ValidationError as e:`.
        *   On validation error, log details and raise a custom `ConfigurationValidationError`.

3.  **Implement Schemas in Concrete Components:**
    *   For each concrete `Ingestor` and `Preprocessor` subclass:
        *   Implement `get_component_schema(self) -> Dict[str, Any]`.
        *   The returned schema *must* use `allOf` to combine its specific requirements with the appropriate base schema (`BASE_INGESTOR_SCHEMA` or `BASE_PREPROCESSOR_SCHEMA`).

4.  **Add Dependency:**
    *   Add `jsonschema` (latest version) to `requirements.txt` and `setup.py` (`install_requires`).

5.  **Custom Exception:**
    *   Define `ConfigurationValidationError` in a central exceptions module (e.g., `ici/exceptions.py`).

This approach embeds validation within the component's initialization, uses inheritance for schema definition enforcement, and ensures both base and specific configurations are validated. Failed validations will prevent the component from loading. 