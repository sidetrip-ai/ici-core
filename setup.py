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
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",   # For testing
            "pytest-cov>=4.0.0", # For test coverage
            "black>=23.0.0",   # For code formatting
        ],
        "embeddings": [
            "sentence-transformers>=2.2.2",  # For text embeddings
            "torch>=2.0.0",  # Required for sentence-transformers
        ],
        "vector-stores": [
            "faiss-cpu>=1.7.0",  # For vector similarity search
            "chromadb>=0.4.22",  # For ChromaDB vector database
            "numpy>=1.22.0",     # Required for vector operations
        ],
        "telegram": [
            "telethon>=1.39.0",  # For Telegram API access
        ],
        "logging": [
            "logtail-python>=0.3.3"
        ]
    },
)
