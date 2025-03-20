.PHONY: setup test lint format clean

# Set up development environment
setup:
	pip install -e ".[dev]"

# Run tests
test:
	pytest

# Run tests with coverage
test-cov:
	pytest --cov=ici tests/

# Lint the code
lint:
	black --check ici tests examples

# Format the code
format:
	black ici tests examples

# Clean up build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name ".coverage" -delete
	find . -name "htmlcov" -type d -exec rm -rf {} +

# Help command
help:
	@echo "Available commands:"
	@echo "  make setup    - Install development dependencies"
	@echo "  make test     - Run tests"
	@echo "  make test-cov - Run tests with coverage"
	@echo "  make lint     - Check code formatting"
	@echo "  make format   - Format code with black"
	@echo "  make clean    - Clean up build artifacts" 