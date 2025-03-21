from setuptools import setup, find_packages

setup(
    name="ici-core",
    version="0.1.0",
    description="Intelligent Consciousness Interface - Core Framework",
    author="ICI Team",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        # Core dependencies - keep minimal
        "pyyaml>=6.0",        # For configuration files
        "sentence-transformers>=3.4.1",  # For text embeddings
        "torch>=2.6.0",  # Required for sentence-transformers
        "faiss-cpu>=1.7.0",  # For vector similarity search
        "chromadb>=0.6.3",  # For ChromaDB vector database
        "numpy>=2.2.2",     # Required for vector operations
        "telethon>=1.39.0",  # For Telegram API access
        "logtail-python>=0.3.3",
        "openai>=1.68.0",
        "langchain>=0.3.21",  # For LangChain integration
        "langchain-openai>=0.1.0",  # For OpenAI with LangChain
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",   # For testing
            "pytest-cov>=4.0.0", # For test coverage
            "black>=23.0.0",   # For code formatting
        ],
        "extra_llms": [
            "langchain-anthropic>=0.1.0",  # For Claude models
            "langchain-community>=0.0.13",  # For additional providers
        ]
    },
)
