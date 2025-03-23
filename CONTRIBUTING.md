# Contributing to ICI Core

Thank you for your interest in contributing to ICI Core! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to uphold our Code of Conduct:

- Be respectful and inclusive of all contributors
- Exercise empathy and kindness in all interactions
- Focus on constructive feedback and collaboration
- Respect differing viewpoints and experiences

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/ici-core.git`
3. Create a branch for your changes: `git checkout -b feature/your-feature-name`
4. Install dependencies using the setup scripts or manual setup as described in the README

## Development Environment

We recommend using a virtual environment for development:

```bash
# Create a virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Project Structure

Please review the [Project Structure](docs/project_structure.md) documentation to understand how the codebase is organized. This will help you place your contributions in the correct locations.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:

1. A clear, descriptive title
2. Detailed steps to reproduce the bug
3. Expected and actual behavior
4. System information (OS, Python version, etc.)
5. Any relevant logs or screenshots

### Suggesting Features

For feature suggestions:

1. Check if the feature has already been suggested or implemented
2. Create an issue with a clear title and detailed description
3. Explain the use case and benefits of the feature
4. If possible, outline a potential implementation approach

### Pull Requests

When submitting a pull request:

1. Update the README.md with details of changes if applicable
2. Update any relevant documentation
3. Include tests that verify your changes
4. Ensure all tests pass locally
5. Link to any related issues
6. Follow the existing code style

## Coding Standards

We follow these coding standards:

1. **PEP 8**: Follow Python's PEP 8 style guide
2. **Type Hints**: Use Python type hints for function parameters and return values
3. **Docstrings**: Include docstrings for all functions, classes, and modules
4. **Comments**: Add comments for complex logic
5. **File Structure**: Follow the project structure guidelines

### Code Style

- We use the `black` formatter for Python code
- Include type hints for function parameters and return values
- Follow our naming conventions:
  - Classes: CamelCase (`MyClass`)
  - Functions/methods: snake_case (`my_function`)
  - Variables: snake_case (`my_variable`)
  - Constants: UPPER_CASE (`MY_CONSTANT`)

### Example Function

```python
from typing import Dict, Any, Optional

def process_data(data: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Process the input data with optional configuration.
    
    Args:
        data: The input data to process
        options: Optional configuration parameters
        
    Returns:
        Processed data as a dictionary
        
    Raises:
        ValueError: If data is empty or invalid
    """
    if not data:
        raise ValueError("Input data cannot be empty")
        
    # Processing logic here
    
    return processed_data
```

## Testing

All contributions should include appropriate tests:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test interactions between components
- **Doctest Examples**: Include examples in docstrings when helpful

Run tests using:

```bash
pytest
```

## Documentation

Please update documentation for any new features or changes:

- Update README.md if introducing new features
- Update/create documentation in the docs folder
- Include examples where appropriate
- Update function/class docstrings

## Commit Messages

Follow these guidelines for commit messages:

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests after the first line

## Pull Request Process

1. Update documentation as needed
2. Include tests for your changes
3. Ensure all tests pass
4. Update the CHANGELOG.md with details of changes
5. Your PR will be reviewed by at least one maintainer
6. Once approved, a maintainer will merge your PR

## License

By contributing to ICI Core, you agree that your contributions will be licensed under the project's MIT License.

## Questions?

If you have any questions or need help, please create an issue with the "question" label or reach out to the project maintainers.

Thank you for contributing to ICI Core! 