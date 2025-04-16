"""
Unit tests for incremental message fetching utilities.
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import pytz
from typing import Dict, Any

from ici.adapters.ingestors.telegram_storage.incremental_utils import (
    get_latest_message_timestamp,
    update_conversation_metadata,
    should_fetch_incrementally,
    merge_conversations,
    prepare_min_id_for_fetch
)


class TestIncrementalUtils(unittest.TestCase):
    """Tests for incremental message fetching utilities."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Sample conversation with messages at different timestamps
        self.conversation = {
            "metadata": {
                "conversation_id": "123",
                "name": "Test Conversation",
                "is_group": False,
                "chat_type": "private",
                "last_update": "2023-01-01T00:00:00Z"
            },
            "messages": {
                "1": {
                    "id": 1,
                    "sender_id": "user1",
                    "text": "First message",
                    "date": "2023-01-01T12:30:00Z",
                    "timestamp": 1672576200
                },
                "2": {
                    "id": 2,
                    "sender_id": "user2",
                    "text": "Second message",
                    "date": "2023-01-02T12:30:00Z",
                    "timestamp": 1672662600
                },
                "3": {
                    "id": 3,
                    "sender_id": "user1",
                    "text": "Latest message",
                    "date": "2023-01-03T12:30:00Z",
                    "timestamp": 1672749000
                }
            }
        }
        
        # Empty conversation
        self.empty_conversation = {
            "metadata": {
                "conversation_id": "456",
                "name": "Empty Conversation",
                "is_group": False,
                "chat_type": "private",
                "last_update": "2023-01-01T00:00:00Z"
            },
            "messages": {}
        }
        
        # New messages to merge
        self.new_messages = [
            {
                "id": 3,  # Existing message with updates (edit)
                "sender_id": "user1",
                "text": "Latest message (edited)",
                "date": "2023-01-03T12:35:00Z",
                "timestamp": 1672749300
            },
            {
                "id": 4,  # New message
                "sender_id": "user2",
                "text": "New message",
                "date": "2023-01-04T12:30:00Z",
                "timestamp": 1672835400
            }
        ]
    
    def test_get_latest_message_timestamp(self):
        """Test getting the latest message timestamp."""
        # Test with conversation containing messages
        latest_date = get_latest_message_timestamp(self.conversation)
        self.assertIsNotNone(latest_date)
        self.assertEqual(latest_date.isoformat(), "2023-01-03T12:30:00+00:00")
        
        # Test with empty conversation
        latest_date = get_latest_message_timestamp(self.empty_conversation)
        self.assertIsNone(latest_date)
        
        # Test with None
        latest_date = get_latest_message_timestamp(None)
        self.assertIsNone(latest_date)
        
        # Test with invalid conversation structure
        latest_date = get_latest_message_timestamp({"metadata": {}})
        self.assertIsNone(latest_date)
    
    def test_update_conversation_metadata(self):
        """Test updating conversation metadata with latest timestamp."""
        # Make a copy to avoid modifying the original
        conversation = dict(self.conversation)
        
        # Update metadata
        updated = update_conversation_metadata(conversation)
        
        # Check last_message_date was set correctly
        self.assertEqual(updated["metadata"]["last_message_date"], "2023-01-03T12:30:00+00:00")
        
        # Check last_update was updated
        self.assertNotEqual(updated["metadata"]["last_update"], "2023-01-01T00:00:00Z")
        
        # Test with empty conversation
        empty = dict(self.empty_conversation)
        updated_empty = update_conversation_metadata(empty)
        
        # Should not have last_message_date
        self.assertNotIn("last_message_date", updated_empty["metadata"])
        
        # Test with None
        result = update_conversation_metadata(None)
        self.assertIsNone(result)
    
    @patch('ici.adapters.ingestors.telegram_storage.incremental_utils.FileManager')
    def test_should_fetch_incrementally(self, mock_file_manager):
        """Test determining if incremental fetching should be used."""
        # Setup mock file manager
        file_manager_instance = MagicMock()
        mock_file_manager.return_value = file_manager_instance
        
        # Case 1: Existing conversation with messages
        file_manager_instance.load_conversation.return_value = self.conversation
        should_incremental, latest_date = should_fetch_incrementally("123", file_manager_instance)
        
        self.assertTrue(should_incremental)
        self.assertIsNotNone(latest_date)
        self.assertEqual(latest_date.isoformat(), "2023-01-03T12:30:00+00:00")
        
        # Case 2: Existing conversation with no messages
        file_manager_instance.load_conversation.return_value = self.empty_conversation
        should_incremental, latest_date = should_fetch_incrementally("456", file_manager_instance)
        
        self.assertFalse(should_incremental)
        self.assertIsNone(latest_date)
        
        # Case 3: File not found
        file_manager_instance.load_conversation.side_effect = FileNotFoundError()
        should_incremental, latest_date = should_fetch_incrementally("789", file_manager_instance)
        
        self.assertFalse(should_incremental)
        self.assertIsNone(latest_date)
        
        # Case 4: Other error
        file_manager_instance.load_conversation.side_effect = Exception("Unknown error")
        should_incremental, latest_date = should_fetch_incrementally("789", file_manager_instance)
        
        self.assertFalse(should_incremental)
        self.assertIsNone(latest_date)
    
    def test_merge_conversations(self):
        """Test merging new messages into existing conversation."""
        # Make a copy to avoid modifying the original
        conversation = dict(self.conversation)
        deepcopy_conversation = {
            "metadata": dict(conversation["metadata"]),
            "messages": {k: dict(v) for k, v in conversation["messages"].items()}
        }
        
        # Merge new messages
        merged = merge_conversations(deepcopy_conversation, self.new_messages)
        
        # Check message counts
        self.assertEqual(len(merged["messages"]), 4)  # 3 original + 1 new (1 is an edit)
        
        # Check edit was applied
        self.assertEqual(merged["messages"]["3"]["text"], "Latest message (edited)")
        self.assertEqual(merged["messages"]["3"]["timestamp"], 1672749300)
        
        # Check new message was added
        self.assertIn("4", merged["messages"])
        self.assertEqual(merged["messages"]["4"]["text"], "New message")
        
        # Check metadata was updated
        self.assertEqual(merged["metadata"]["last_message_date"], "2023-01-04T12:30:00+00:00")
        
        # Test with empty conversation
        empty = dict(self.empty_conversation)
        merged_empty = merge_conversations(empty, self.new_messages)
        
        # Should now have the new messages
        self.assertEqual(len(merged_empty["messages"]), 2)
        
        # Test with None inputs
        result1 = merge_conversations(None, self.new_messages)
        self.assertIsNone(result1)
        
        result2 = merge_conversations(deepcopy_conversation, None)
        self.assertEqual(result2["messages"], deepcopy_conversation["messages"])
    
    def test_prepare_min_id_for_fetch(self):
        """Test preparing min_id for fetch based on timestamp."""
        # Create a latest date
        latest_date = datetime(2023, 1, 3, 12, 30, 0, tzinfo=timezone.utc)
        
        # Sample messages to search through
        messages = [
            {
                "id": 10,
                "date": "2023-01-03T12:25:00Z",  # Earlier than latest
            },
            {
                "id": 11,
                "date": "2023-01-03T12:30:00Z",  # Same as latest
            },
            {
                "id": 12,
                "date": "2023-01-03T12:35:00Z",  # Later than latest
            }
        ]
        
        # Should find the message at exactly the latest date
        min_id = prepare_min_id_for_fetch(latest_date, messages)
        self.assertEqual(min_id, 11)
        
        # Test with no matching messages (all earlier)
        earlier_messages = [
            {
                "id": 10,
                "date": "2023-01-03T12:25:00Z",  # Earlier than latest
            },
            {
                "id": 9,
                "date": "2023-01-03T12:20:00Z",  # Earlier than latest
            }
        ]
        min_id = prepare_min_id_for_fetch(latest_date, earlier_messages)
        self.assertIsNone(min_id)
        
        # Test with only later messages
        later_messages = [
            {
                "id": 12,
                "date": "2023-01-03T12:35:00Z",  # Later than latest
            },
            {
                "id": 13,
                "date": "2023-01-03T12:40:00Z",  # Later than latest
            }
        ]
        min_id = prepare_min_id_for_fetch(latest_date, later_messages)
        self.assertEqual(min_id, 12)  # Should return the earliest later message
        
        # Test with invalid inputs
        self.assertIsNone(prepare_min_id_for_fetch(None, messages))
        self.assertIsNone(prepare_min_id_for_fetch(latest_date, []))
        self.assertIsNone(prepare_min_id_for_fetch(latest_date, None))


if __name__ == "__main__":
    unittest.main() 