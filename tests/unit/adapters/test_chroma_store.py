"""
Unit tests for ChromaDB Vector Store adapter.

This test suite tests the ChromaDBStore class using real components:
- Real ChromaDB client and collections
- Real configuration
- Real logging
"""

import os
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import shutil
import tempfile
import numpy as np
from typing import List, Dict, Any

from ici.adapters.vector_stores.chroma import ChromaDBStore
from ici.core.exceptions import VectorStoreError

# Create example configuration file for testing
SAMPLE_CONFIG = {
    "vector_store": {
        "type": "chroma",
        "collection_name": "test_collection",
        "persist_directory": None  # Will be set during test setup
    }
}

class TestChromaDBStore(unittest.TestCase):
    """Test suite for ChromaDBStore adapter using real components."""
    
    @patch('ici.adapters.vector_stores.chroma.StructuredLogger')
    def setUp(self, mock_logger_class):
        """Set up test environment before each test."""
        # Set up mock logger
        self.mock_logger = MagicMock()
        self.mock_logger.info = MagicMock()
        self.mock_logger.debug = MagicMock()
        self.mock_logger.warning = MagicMock()
        self.mock_logger.error = MagicMock()
        mock_logger_class.return_value = self.mock_logger
        
        # Create a temporary directory for the test ChromaDB
        self.test_dir = tempfile.mkdtemp(prefix="chroma_test_")
        
        # Create persist directory path for ChromaDB
        persist_dir = os.path.join(self.test_dir, "chroma_db")
        
        # Create a temporary config file with proper YAML format
        self.config_path = os.path.join(self.test_dir, "config.yaml")
        with open(self.config_path, "w") as f:
            f.write(f"""
vector_store:
  type: chroma
  collection_name: test_collection
  persist_directory: {persist_dir}
""")
        
        # Set environment variable to point to our test config
        os.environ["ICI_CONFIG_PATH"] = self.config_path
        
        # Create the store with mocked logger
        self.store = ChromaDBStore(logger_name="test_vector_store")
        
        # Create a mock configuration
        self.mock_config = {
            "type": "chroma",
            "collection_name": "test_collection",
            "persist_directory": persist_dir
        }
    
    def generate_test_embedding(self, dimension: int = 384) -> List[float]:
        """Generate a random embedding vector for testing."""
        # Use a fixed seed for reproducibility
        np.random.seed(42)
        return np.random.rand(dimension).tolist()
    
    @patch('ici.adapters.vector_stores.chroma.get_component_config')
    @patch('ici.adapters.vector_stores.chroma.chromadb.PersistentClient')
    async def test_initialize(self, mock_persistent_client, mock_get_component_config):
        """Test the initialization of ChromaDBStore."""
        # Setup mock collection
        mock_collection = MagicMock()
        mock_collection.name = "test_collection"
        
        # Setup client
        mock_client_instance = mock_persistent_client.return_value
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        
        # Mock the configuration retrieval
        mock_get_component_config.return_value = self.mock_config
        
        # Initialize the store
        await self.store.initialize()
        
        # Check if the store is initialized correctly
        self.assertTrue(self.store._is_initialized)
        self.assertIsNotNone(self.store._client)
        self.assertIsNotNone(self.store._collection)
        
        # Verify the client was initialized with correct path
        mock_persistent_client.assert_called_once_with(path=self.mock_config["persist_directory"])
        self.assertEqual(self.store._collection.name, "test_collection")
    
    @patch('ici.adapters.vector_stores.chroma.get_component_config')
    @patch('ici.adapters.vector_stores.chroma.chromadb.Client')
    async def test_initialize_in_memory(self, mock_client, mock_get_component_config):
        """Test initialization with in-memory configuration."""
        # Create in-memory config (no persist_directory)
        in_memory_config = {
            "type": "chroma",
            "collection_name": "test_collection"
        }
        
        # Setup mocks
        mock_collection = MagicMock()
        mock_collection.name = "test_collection"
        mock_client_instance = mock_client.return_value
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        
        # Mock the configuration retrieval
        mock_get_component_config.return_value = in_memory_config
        
        # Initialize the store
        await self.store.initialize()
        
        # Verify client was created correctly
        mock_client.assert_called_once()
        self.assertTrue(self.store._is_initialized)
    
    @patch('ici.adapters.vector_stores.chroma.get_component_config')
    @patch('ici.adapters.vector_stores.chroma.chromadb.PersistentClient')
    async def test_add_documents(self, mock_persistent_client, mock_get_component_config):
        """Test adding documents."""
        # Setup mock collection
        mock_collection = MagicMock()
        mock_collection.name = "test_collection"
        mock_collection.add = MagicMock()
        
        # Setup client
        mock_client_instance = mock_persistent_client.return_value
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        
        # Mock the configuration retrieval
        mock_get_component_config.return_value = self.mock_config
        
        # Initialize the store
        await self.store.initialize()
        
        # Create test documents and vectors
        documents = [
            {
                "text": "This is a test document",
                "metadata": {"source": "test", "category": "testing"}
            }
        ]
        vectors = [self.generate_test_embedding()]
        
        # Add documents
        self.store.add_documents(documents, vectors)
        
        # Check that collection.add was called correctly
        mock_collection.add.assert_called_once()
        
        # Verify the correct arguments were passed
        args, kwargs = mock_collection.add.call_args
        self.assertEqual(kwargs["documents"], ["This is a test document"])
        self.assertEqual(kwargs["metadatas"], [{"source": "test", "category": "testing"}])
        self.assertEqual(len(kwargs["embeddings"]), 1)
    
    def test_add_documents_not_initialized(self):
        """Test adding documents without initialization."""
        # Create test documents and vectors
        documents = [{"text": "Test document"}]
        vectors = [self.generate_test_embedding()]
        
        # Add documents without initialization should raise error
        with self.assertRaises(VectorStoreError):
            self.store.add_documents(documents, vectors)
    
    @patch('ici.adapters.vector_stores.chroma.get_component_config')
    @patch('ici.adapters.vector_stores.chroma.chromadb.PersistentClient')
    async def test_add_documents_mismatch(self, mock_persistent_client, mock_get_component_config):
        """Test adding documents with mismatched counts."""
        # Setup mock collection
        mock_collection = MagicMock()
        mock_collection.name = "test_collection"
        
        # Setup client
        mock_client_instance = mock_persistent_client.return_value
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        
        # Mock the configuration retrieval
        mock_get_component_config.return_value = self.mock_config
        
        # Initialize the store
        await self.store.initialize()
        
        # Create test documents and vectors with mismatched counts
        documents = [{"text": "Test document 1"}, {"text": "Test document 2"}]
        vectors = [self.generate_test_embedding()]
        
        # Add documents with mismatched counts should raise error
        with self.assertRaises(VectorStoreError):
            self.store.add_documents(documents, vectors)
    
    @patch('ici.adapters.vector_stores.chroma.get_component_config')
    @patch('ici.adapters.vector_stores.chroma.chromadb.PersistentClient')
    async def test_search(self, mock_persistent_client, mock_get_component_config):
        """Test searching documents."""
        # Setup mock collection with query method
        mock_collection = MagicMock()
        mock_collection.name = "test_collection"
        
        # Setup query results
        query_results = {
            "ids": [["id1", "id2"]],
            "documents": [["Document 1", "Document 2"]],
            "metadatas": [[{"source": "test1"}, {"source": "test2"}]],
            "distances": [[0.1, 0.2]]
        }
        mock_collection.query.return_value = query_results
        
        # Setup client
        mock_client_instance = mock_persistent_client.return_value
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        
        # Mock the configuration retrieval
        mock_get_component_config.return_value = self.mock_config
        
        # Initialize the store
        await self.store.initialize()
        
        # Create a query vector
        query_vector = self.generate_test_embedding()
        
        # Search
        results = self.store.search(query_vector=query_vector, num_results=2)
        
        # Check results
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["text"], "Document 1")
        self.assertEqual(results[0]["metadata"], {"source": "test1"})
        self.assertEqual(results[0]["score"], 0.1)
        self.assertEqual(results[1]["text"], "Document 2")
        self.assertEqual(results[1]["metadata"], {"source": "test2"})
        self.assertEqual(results[1]["score"], 0.2)
    
    @patch('ici.adapters.vector_stores.chroma.get_component_config')
    @patch('ici.adapters.vector_stores.chroma.chromadb.PersistentClient')
    async def test_count(self, mock_persistent_client, mock_get_component_config):
        """Test counting documents."""
        # Setup mock collection with get method
        mock_collection = MagicMock()
        mock_collection.name = "test_collection"
        
        # Configure get method to return IDs for counting
        mock_collection.get.return_value = {"ids": ["id1", "id2", "id3", "id4", "id5"]}
        
        # Setup client
        mock_client_instance = mock_persistent_client.return_value
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        
        # Mock the configuration retrieval
        mock_get_component_config.return_value = self.mock_config
        
        # Initialize the store
        await self.store.initialize()
        
        # Count all documents
        count = self.store.count()
        self.assertEqual(count, 5)
        mock_collection.get.assert_called_with()
        
        # Reset the mock
        mock_collection.get.reset_mock()
        
        # Configure get method to return different IDs for filtered count
        mock_collection.get.return_value = {"ids": ["id1", "id2"]}
        
        # Count with filter
        filters = {"category": "database"}
        filtered_count = self.store.count(filters=filters)
        self.assertEqual(filtered_count, 2)
        mock_collection.get.assert_called_with(where=filters)
    
    @patch('ici.adapters.vector_stores.chroma.get_component_config')
    @patch('ici.adapters.vector_stores.chroma.chromadb.PersistentClient')
    async def test_delete_by_id(self, mock_persistent_client, mock_get_component_config):
        """Test deleting documents by ID."""
        # Setup mock collection
        mock_collection = MagicMock()
        mock_collection.name = "test_collection"
        mock_collection.delete.return_value = None  # delete doesn't return anything
        
        # Setup get method to return different results for before and after deletion
        mock_collection.get.side_effect = [
            {"ids": ["id1", "id2", "id3", "id4"]},  # Initial count
            {"ids": ["id3", "id4"]}                 # After deletion
        ]
        
        # Setup client
        mock_client_instance = mock_persistent_client.return_value
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        
        # Mock the configuration retrieval
        mock_get_component_config.return_value = self.mock_config
        
        # Initialize the store
        await self.store.initialize()
        
        # Delete by ID
        doc_ids = ["id1", "id2"]
        deleted_count = self.store.delete(document_ids=doc_ids)
        
        # Check deletion
        self.assertEqual(deleted_count, 2)
        mock_collection.delete.assert_called_once_with(ids=doc_ids)
    
    @patch('ici.adapters.vector_stores.chroma.get_component_config')
    @patch('ici.adapters.vector_stores.chroma.chromadb.PersistentClient')
    async def test_delete_by_filter(self, mock_persistent_client, mock_get_component_config):
        """Test deleting documents by filter."""
        # Setup mock collection
        mock_collection = MagicMock()
        mock_collection.name = "test_collection"
        mock_collection.delete.return_value = None  # delete doesn't return anything
        
        # Setup get method to return different results for before and after deletion
        mock_collection.get.side_effect = [
            {"ids": ["id1", "id2", "id3", "id4"]},  # Initial count
            {"ids": ["id3", "id4"]}                 # After deletion
        ]
        
        # Setup client
        mock_client_instance = mock_persistent_client.return_value
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        
        # Mock the configuration retrieval
        mock_get_component_config.return_value = self.mock_config
        
        # Initialize the store
        await self.store.initialize()
        
        # Delete by filter
        filters = {"category": "database"}
        deleted_count = self.store.delete(filters=filters)
        
        # Check deletion
        self.assertEqual(deleted_count, 2)
        mock_collection.delete.assert_called_once_with(where=filters)
    
    def test_healthcheck_not_initialized(self):
        """Test healthcheck when the store is not initialized."""
        health_result = self.store.healthcheck()
        self.assertFalse(health_result["healthy"])
        self.assertEqual(health_result["message"], "Vector store not initialized")
    
    @patch('ici.adapters.vector_stores.chroma.get_component_config')
    @patch('ici.adapters.vector_stores.chroma.chromadb.PersistentClient')
    async def test_healthcheck_healthy(self, mock_persistent_client, mock_get_component_config):
        """Test healthcheck when the store is healthy."""
        # Setup mock collection
        mock_collection = MagicMock()
        mock_collection.name = "test_collection"
        
        # Setup client
        mock_client_instance = mock_persistent_client.return_value
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        
        # Mock the configuration retrieval
        mock_get_component_config.return_value = self.mock_config
        
        # Initialize the store
        await self.store.initialize()
        
        # Check health
        health_result = self.store.healthcheck()
        self.assertTrue(health_result["healthy"])
        self.assertIn("ChromaDB", health_result["message"])
    
    def tearDown(self):
        """Tear down test environment after each test."""
        # Cleanup
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
            
        # Clear environment variable
        if "ICI_CONFIG_PATH" in os.environ:
            del os.environ["ICI_CONFIG_PATH"] 