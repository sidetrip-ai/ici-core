"""
Unit tests for conversation type detection utilities.
"""

import unittest
from unittest.mock import patch, MagicMock

from ici.adapters.ingestors.telegram.storage.conversation_utils import (
    is_personal_chat, is_bot_chat, is_private_group,
    filter_conversations, get_fetch_mode_from_config,
    add_conversation_type_metadata
)


class TestConversationUtils(unittest.TestCase):
    """Tests for conversation type detection utilities."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Sample personal chat conversation
        self.personal_chat = {
            "metadata": {
                "conversation_id": "123",
                "is_group": False,
                "chat_type": "private",
                "name": "John Doe",
                "username": "johndoe"
            },
            "messages": {}
        }
        
        # Sample bot chat conversation
        self.bot_chat = {
            "metadata": {
                "conversation_id": "456",
                "is_group": False,
                "chat_type": "private",
                "name": "Telegram Bot",
                "username": "telegram_bot"
            },
            "messages": {}
        }
        
        # Sample private group conversation
        self.private_group = {
            "metadata": {
                "conversation_id": "789",
                "is_group": True,
                "is_channel": False,
                "chat_type": "group",
                "name": "Private Group"
            },
            "messages": {}
        }
        
        # Sample channel conversation
        self.channel = {
            "metadata": {
                "conversation_id": "101112",
                "is_group": True,
                "is_channel": True,
                "chat_type": "channel",
                "name": "Public Channel"
            },
            "messages": {}
        }
        
        # Dictionary of all conversations
        self.all_conversations = {
            "123": self.personal_chat,
            "456": self.bot_chat,
            "789": self.private_group,
            "101112": self.channel
        }
    
    def test_is_personal_chat(self):
        """Test personal chat detection."""
        self.assertTrue(is_personal_chat(self.personal_chat))
        self.assertTrue(is_personal_chat(self.bot_chat))  # Bot chats are also personal chats
        self.assertFalse(is_personal_chat(self.private_group))
        self.assertFalse(is_personal_chat(self.channel))
        self.assertFalse(is_personal_chat({}))  # Empty dict
        self.assertFalse(is_personal_chat(None))  # None
    
    def test_is_bot_chat(self):
        """Test bot chat detection."""
        self.assertFalse(is_bot_chat(self.personal_chat))
        self.assertTrue(is_bot_chat(self.bot_chat))
        self.assertFalse(is_bot_chat(self.private_group))
        self.assertFalse(is_bot_chat(self.channel))
        self.assertFalse(is_bot_chat({}))  # Empty dict
        self.assertFalse(is_bot_chat(None))  # None
        
        # Edge case: username is None
        no_username = {
            "metadata": {
                "conversation_id": "123",
                "is_group": False,
                "chat_type": "private",
                "name": "No Username",
                "username": None
            }
        }
        self.assertFalse(is_bot_chat(no_username))
        
        # Edge case: uppercase BOT
        uppercase_bot = {
            "metadata": {
                "conversation_id": "123",
                "is_group": False,
                "chat_type": "private",
                "name": "Uppercase Bot",
                "username": "uppercaseBOT"
            }
        }
        self.assertTrue(is_bot_chat(uppercase_bot))
    
    def test_is_private_group(self):
        """Test private group detection."""
        self.assertFalse(is_private_group(self.personal_chat))
        self.assertFalse(is_private_group(self.bot_chat))
        self.assertTrue(is_private_group(self.private_group))
        self.assertFalse(is_private_group(self.channel))
        self.assertFalse(is_private_group({}))  # Empty dict
        self.assertFalse(is_private_group(None))  # None
    
    def test_filter_conversations_initial_mode(self):
        """Test filtering conversations in initial mode."""
        filtered = filter_conversations(self.all_conversations, "initial")
        
        # Should include personal chats, bot chats, and private groups
        self.assertIn("123", filtered)  # Personal chat
        self.assertIn("456", filtered)  # Bot chat
        self.assertIn("789", filtered)  # Private group
        self.assertNotIn("101112", filtered)  # Channel should be filtered out
        
        # Check that conversation types metadata is added
        self.assertIn("conversation_types", filtered["123"]["metadata"])
        self.assertIn("personal_chat", filtered["123"]["metadata"]["conversation_types"])
        
        self.assertIn("conversation_types", filtered["456"]["metadata"])
        self.assertIn("bot_chat", filtered["456"]["metadata"]["conversation_types"])
        self.assertIn("personal_chat", filtered["456"]["metadata"]["conversation_types"])
        
        self.assertIn("conversation_types", filtered["789"]["metadata"])
        self.assertIn("private_group", filtered["789"]["metadata"]["conversation_types"])
    
    def test_filter_conversations_all_mode(self):
        """Test filtering conversations in all mode."""
        filtered = filter_conversations(self.all_conversations, "all")
        
        # Should include all conversations
        self.assertEqual(len(filtered), 4)
        self.assertIn("123", filtered)
        self.assertIn("456", filtered)
        self.assertIn("789", filtered)
        self.assertIn("101112", filtered)
    
    def test_filter_conversations_unknown_mode(self):
        """Test filtering conversations with unknown mode."""
        filtered = filter_conversations(self.all_conversations, "unknown")
        
        # Should return all conversations for unknown mode
        self.assertEqual(self.all_conversations, filtered)
    
    @patch("ici.adapters.ingestors.telegram.storage.conversation_utils.get_component_config")
    def test_get_fetch_mode_from_config(self, mock_get_config):
        """Test getting fetch mode from config."""
        # Test normal case
        mock_get_config.return_value = {"fetch_mode": "all"}
        self.assertEqual(get_fetch_mode_from_config(), "all")
        
        # Test default value
        mock_get_config.return_value = {}
        self.assertEqual(get_fetch_mode_from_config(), "initial")
        
        # Test invalid value
        mock_get_config.return_value = {"fetch_mode": "invalid"}
        self.assertEqual(get_fetch_mode_from_config(), "initial")
        
        # Test exception
        mock_get_config.side_effect = Exception("Config error")
        self.assertEqual(get_fetch_mode_from_config(), "initial")
    
    def test_add_conversation_type_metadata(self):
        """Test adding conversation type metadata."""
        result = add_conversation_type_metadata(self.all_conversations)
        
        # Check personal chat
        personal_chat = result["123"]
        self.assertIn("conversation_types", personal_chat["metadata"])
        self.assertIn("personal_chat", personal_chat["metadata"]["conversation_types"])
        self.assertNotIn("bot_chat", personal_chat["metadata"]["conversation_types"])
        self.assertNotIn("private_group", personal_chat["metadata"]["conversation_types"])
        
        # Check bot chat (should be both personal and bot)
        bot_chat = result["456"]
        self.assertIn("conversation_types", bot_chat["metadata"])
        self.assertIn("personal_chat", bot_chat["metadata"]["conversation_types"])
        self.assertIn("bot_chat", bot_chat["metadata"]["conversation_types"])
        self.assertNotIn("private_group", bot_chat["metadata"]["conversation_types"])
        
        # Check private group
        private_group = result["789"]
        self.assertIn("conversation_types", private_group["metadata"])
        self.assertNotIn("personal_chat", private_group["metadata"]["conversation_types"])
        self.assertNotIn("bot_chat", private_group["metadata"]["conversation_types"])
        self.assertIn("private_group", private_group["metadata"]["conversation_types"])
        
        # Check channel (should have empty conversation_types)
        channel = result["101112"]
        self.assertIn("conversation_types", channel["metadata"])
        self.assertEqual(len(channel["metadata"]["conversation_types"]), 0)


if __name__ == "__main__":
    unittest.main() 