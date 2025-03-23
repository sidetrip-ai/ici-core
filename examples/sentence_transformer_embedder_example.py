#!/usr/bin/env python3
"""
Example demonstrating the use of the SentenceTransformerEmbedder.

This script initializes the SentenceTransformerEmbedder and uses it to generate
embeddings for sample texts, demonstrating both single and batch embedding.
"""

import os
import asyncio
import yaml
from pathlib import Path

from ici.adapters import SentenceTransformerEmbedder
from ici.adapters.loggers import StructuredLogger


async def main():
    """Run the example script."""
    # Create a logger
    logger = StructuredLogger(
        name="embedder_example",
        log_level="INFO"
    )
    
    # Create configuration directory and file if they don't exist
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    config_path = config_dir / "embedders.yaml"
    
    # Create example config if it doesn't exist
    if not config_path.exists():
        config = {
            "embedders": {
                "sentence_transformer": {
                    "model_name": "all-MiniLM-L6-v2"  # Small, fast model for demonstration
                }
            }
        }
        
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        
        logger.info(f"Created example config at {config_path}")
    
    # Create the embedder
    embedder = SentenceTransformerEmbedder(logger_name="sentence_transformer_example")
    
    # Initialize the embedder
    logger.info("Initializing embedder...")
    await embedder.initialize()
    
    # Display embedder details
    logger.info(f"Embedder initialized with model: {embedder._model_name}")
    logger.info(f"Embedding dimensions: {embedder.dimensions}")
    
    # Check health
    health = embedder.healthcheck()
    logger.info(f"Embedder health: {health['healthy']} - {health['message']}")
    
    # Sample text for embedding
    sample_text = "The quick brown fox jumps over the lazy dog."
    
    # Generate embedding for a single text
    logger.info(f"Generating embedding for: '{sample_text}'")
    embedding, metadata = await embedder.embed(sample_text)
    
    # Display results
    logger.info(f"Embedding generated: {len(embedding)} dimensions")
    logger.info(f"Metadata: {metadata}")
    logger.info(f"First 5 dimensions: {embedding[:5]}")
    
    # Batch embedding example
    batch_texts = [
        "Artificial intelligence is transforming the world.",
        "Machine learning models learn from data.",
        "Natural language processing helps computers understand human language.",
        "",  # Empty text to demonstrate handling
    ]
    
    logger.info(f"Generating embeddings for batch of {len(batch_texts)} texts...")
    batch_results = await embedder.embed_batch(batch_texts)
    
    # Display batch results
    for i, (embedding, metadata) in enumerate(batch_results):
        logger.info(f"Text {i+1} embedding: {len(embedding)} dimensions")
        logger.info(f"Text {i+1} metadata: {metadata}")
    
    logger.info("Example completed successfully.")


if __name__ == "__main__":
    asyncio.run(main()) 