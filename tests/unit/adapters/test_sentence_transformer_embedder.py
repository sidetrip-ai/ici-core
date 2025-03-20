"""
Unit tests for SentenceTransformerEmbedder adapter.
"""

import unittest
import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import numpy as np
from typing import List, Dict, Any

from ici.adapters.embedders.sentence_transformer import SentenceTransformerEmbedder
from ici.core.exceptions import EmbeddingError


class TestSentenceTransformerEmbedder(unittest.TestCase):
    """Test the SentenceTransformerEmbedder class."""

    @patch('ici.adapters.embedders.sentence_transformer.StructuredLogger')
    def setUp(self, mock_logger_class):
        """Set up the test environment."""
        # Set up mock logger
        self.mock_logger = MagicMock()
        mock_logger_class.return_value = self.mock_logger
        
        # Create embedder with mocked logger
        self.embedder = SentenceTransformerEmbedder(logger_name="test_embedder")
        
        # Set up mock model
        self.mock_model = MagicMock()
        self.mock_model.get_sentence_embedding_dimension.return_value = 384
        self.embedder._model = self.mock_model
        
        # Sample test data
        self.sample_text = "This is a sample text for embedding."
        self.sample_embedding = [0.1] * 384
    
    @pytest.mark.asyncio
    @patch('ici.adapters.embedders.sentence_transformer.get_component_config')
    @patch('ici.adapters.embedders.sentence_transformer.SentenceTransformer')
    async def test_initialize(self, mock_sentence_transformer, mock_get_component_config):
        """Test initializing the embedder."""
        # Configure mocks
        mock_get_component_config.return_value = {
            "model_name": "test-model"
        }
        
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_sentence_transformer.return_value = mock_model
        
        # Initialize the embedder
        await self.embedder.initialize()
        
        # Verify model was loaded with correct configuration
        mock_sentence_transformer.assert_called_once_with("test-model", device=self.embedder._device)
        
        # Check initialized flag
        self.assertTrue(self.embedder._is_initialized)
        self.assertEqual(self.embedder._model_name, "test-model")
    
    @pytest.mark.asyncio
    @patch('ici.adapters.embedders.sentence_transformer.get_component_config')
    @patch('ici.adapters.embedders.sentence_transformer.SentenceTransformer')
    async def test_initialize_default_model(self, mock_sentence_transformer, mock_get_component_config):
        """Test initializing with default model when not specified in config."""
        # Configure mock to return empty config
        mock_get_component_config.return_value = {}
        
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_sentence_transformer.return_value = mock_model
        
        # Initialize the embedder
        await self.embedder.initialize()
        
        # Verify default model was used
        mock_sentence_transformer.assert_called_once_with("all-MiniLM-L6-v2", device=self.embedder._device)
    
    @pytest.mark.asyncio
    async def test_embed_not_initialized(self):
        """Test embedding without initialization."""
        # Reset initialization flag
        self.embedder._is_initialized = False
        
        # Attempt to embed should raise error
        with self.assertRaises(EmbeddingError):
            await self.embedder.embed(self.sample_text)
    
    @pytest.mark.asyncio
    @patch('ici.adapters.embedders.sentence_transformer.get_component_config')
    @patch('ici.adapters.embedders.sentence_transformer.SentenceTransformer')
    async def test_embed(self, mock_sentence_transformer, mock_get_component_config):
        """Test embedding a text."""
        # Setup the embedder
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = np.array(self.sample_embedding)
        mock_sentence_transformer.return_value = mock_model
        
        # Configure mock to return config
        mock_get_component_config.return_value = {"model_name": "test-model"}
        
        # Initialize the embedder
        await self.embedder.initialize()
        
        # Embed sample text
        embedding, metadata = await self.embedder.embed(self.sample_text)
        
        # Verify embedding
        self.assertEqual(len(embedding), 384)
        self.assertEqual(embedding, self.sample_embedding)
        
        # Verify metadata
        self.assertIn("model", metadata)
        self.assertIn("text_length", metadata)
        self.assertEqual(metadata["model"], "test-model")
        self.assertEqual(metadata["text_length"], len(self.sample_text))
    
    @pytest.mark.asyncio
    @patch('ici.adapters.embedders.sentence_transformer.get_component_config')
    @patch('ici.adapters.embedders.sentence_transformer.SentenceTransformer')
    async def test_embed_empty_input(self, mock_sentence_transformer, mock_get_component_config):
        """Test embedding with empty input."""
        # Setup the embedder
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_sentence_transformer.return_value = mock_model
        
        # Configure mock to return config
        mock_get_component_config.return_value = {"model_name": "test-model"}
        
        # Initialize the embedder
        await self.embedder.initialize()
        
        # Embed empty text
        embedding, metadata = await self.embedder.embed("")
        
        # Verify zero embedding
        self.assertEqual(len(embedding), 384)
        self.assertEqual(embedding, [0.0] * 384)
        
        # Verify warning metadata
        self.assertIn("warning", metadata)
    
    @pytest.mark.asyncio
    @patch('ici.adapters.embedders.sentence_transformer.get_component_config')
    @patch('ici.adapters.embedders.sentence_transformer.SentenceTransformer')
    async def test_embed_batch(self, mock_sentence_transformer, mock_get_component_config):
        """Test batch embedding."""
        # Setup the embedder
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = np.array([self.sample_embedding, self.sample_embedding])
        mock_sentence_transformer.return_value = mock_model
        
        # Configure mock to return config
        mock_get_component_config.return_value = {"model_name": "test-model"}
        
        # Initialize the embedder
        await self.embedder.initialize()
        
        # Sample batch
        sample_batch = ["First text", "Second text"]
        
        # Embed batch
        results = await self.embedder.embed_batch(sample_batch)
        
        # Verify results
        self.assertEqual(len(results), 2)
        
        # Each result should be a tuple with (embedding, metadata)
        for embedding, metadata in results:
            self.assertEqual(len(embedding), 384)
            self.assertIn("model", metadata)
            self.assertIn("text_length", metadata)
    
    @pytest.mark.asyncio
    @patch('ici.adapters.embedders.sentence_transformer.get_component_config')
    @patch('ici.adapters.embedders.sentence_transformer.SentenceTransformer')
    async def test_embed_batch_with_invalid_items(self, mock_sentence_transformer, mock_get_component_config):
        """Test batch embedding with invalid items."""
        # Setup the embedder
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = np.array([self.sample_embedding, self.sample_embedding, self.sample_embedding])
        mock_sentence_transformer.return_value = mock_model
        
        # Configure mock to return config
        mock_get_component_config.return_value = {"model_name": "test-model"}
        
        # Initialize the embedder
        await self.embedder.initialize()
        
        # Sample batch with invalid items
        sample_batch = ["Valid text", None, ""]
        
        # Embed batch
        results = await self.embedder.embed_batch(sample_batch)
        
        # Verify results
        self.assertEqual(len(results), 3)
        
        # Check metadata for warning on invalid items
        _, metadata1 = results[0]
        _, metadata2 = results[1]
        _, metadata3 = results[2]
        
        self.assertNotIn("warning", metadata1)
        self.assertIn("warning", metadata2)
        self.assertIn("warning", metadata3)
    
    @pytest.mark.asyncio
    @patch('ici.adapters.embedders.sentence_transformer.get_component_config')
    @patch('ici.adapters.embedders.sentence_transformer.SentenceTransformer')
    async def test_embed_batch_empty(self, mock_sentence_transformer, mock_get_component_config):
        """Test batch embedding with empty batch."""
        # Setup the embedder
        mock_model = MagicMock()
        mock_sentence_transformer.return_value = mock_model
        
        # Configure mock to return config
        mock_get_component_config.return_value = {"model_name": "test-model"}
        
        # Initialize the embedder
        await self.embedder.initialize()
        
        # Embed empty batch
        results = await self.embedder.embed_batch([])
        
        # Verify empty results
        self.assertEqual(results, [])
    
    @patch('ici.adapters.embedders.sentence_transformer.get_component_config')
    @patch('ici.adapters.embedders.sentence_transformer.SentenceTransformer')
    def test_dimensions(self, mock_sentence_transformer, mock_get_component_config):
        """Test getting dimensions property."""
        # Setup mock model with specific dimension
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 768
        mock_sentence_transformer.return_value = mock_model
        
        # Configure embedder
        self.embedder._model = mock_model
        self.embedder._is_initialized = True
        
        # Check dimensions
        self.assertEqual(self.embedder.dimensions, 768)
    
    def test_dimensions_not_initialized(self):
        """Test getting dimensions when not initialized."""
        # Reset initialization flag
        self.embedder._is_initialized = False
        
        # Getting dimensions should raise error
        with self.assertRaises(EmbeddingError):
            _ = self.embedder.dimensions
    
    @patch('ici.adapters.embedders.sentence_transformer.get_component_config')
    @patch('ici.adapters.embedders.sentence_transformer.SentenceTransformer')
    @patch('ici.adapters.embedders.sentence_transformer.asyncio')
    def test_healthcheck(self, mock_asyncio, mock_sentence_transformer, mock_get_component_config):
        """Test healthcheck functionality."""
        # Setup mock event loop
        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = (self.sample_embedding, {})
        mock_asyncio.get_event_loop.return_value = mock_loop
        
        # Setup mock model
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_sentence_transformer.return_value = mock_model
        
        # Configure embedder
        self.embedder._model = mock_model
        self.embedder._is_initialized = True
        self.embedder._model_name = "test-model"
        
        # Get health status
        health = self.embedder.healthcheck()
        
        # Verify health results
        self.assertTrue(health["healthy"])
        self.assertIn("test-model", health["message"])
        self.assertEqual(health["details"]["initialized"], True)
        self.assertEqual(health["details"]["model_name"], "test-model")
    
    def test_healthcheck_not_initialized(self):
        """Test healthcheck when not initialized."""
        # Reset initialization flag
        self.embedder._is_initialized = False
        
        # Get health status
        health = self.embedder.healthcheck()
        
        # Verify not healthy
        self.assertFalse(health["healthy"])
        self.assertEqual(health["message"], "Embedder not initialized")
        self.assertEqual(health["details"]["initialized"], False) 