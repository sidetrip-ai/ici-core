"""
Unit tests for the TelegramIngestor adapter.
"""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from ici.adapters.ingestors.telegram import TelegramIngestor


class TestTelegramIngestor(unittest.TestCase):
    """Test the TelegramIngestor class."""

    @patch('ici.adapters.ingestors.telegram.StructuredLogger')
    def setUp(self, mock_logger_class):
        """Set up the test environment."""
        # Set up mock logger
        self.mock_logger = MagicMock()
        mock_logger_class.return_value = self.mock_logger
        
        # Create ingestor with mocked logger
        self.ingestor = TelegramIngestor(logger_name="test_telegram")
        
        # Mock the internal client
        self.ingestor._client = MagicMock()
        self.ingestor._is_connected = True
        
        # Sample test data
        self.sample_conversation = {
            "id": "12345",
            "name": "Test User",
            "username": "testuser",
            "type": "direct",
            "unread_count": 2,
            "last_message_date": "2023-03-18T12:00:00"
        }
        
        self.sample_message = {
            "id": "1001",
            "conversation_id": "12345",
            "date": "2023-03-18T11:30:00",
            "text": "Hello, this is a test message",
            "outgoing": False,
            "media_type": None,
            "reply_to_msg_id": None,
            "conversation_name": "Test User",
            "conversation_username": "testuser",
            "source": "telegram"
        }

    @patch('ici.adapters.ingestors.telegram.TelegramIngestor._run_sync')
    def test_fetch_full_data(self, mock_run_sync):
        """Test fetching all data."""
        # Set up the mock return value
        mock_data = {
            "conversations": [self.sample_conversation],
            "messages": [self.sample_message]
        }
        mock_run_sync.return_value = mock_data
        
        # Call the method
        result = self.ingestor.fetch_full_data()
        
        # Assertions
        self.assertEqual(result, mock_data)
        mock_run_sync.assert_called_once()

    @patch('ici.adapters.ingestors.telegram.TelegramIngestor._run_sync')
    def test_fetch_new_data(self, mock_run_sync):
        """Test fetching new data since a timestamp."""
        # Set up the mock return value
        mock_data = {
            "conversations": [self.sample_conversation],
            "messages": [self.sample_message]
        }
        mock_run_sync.return_value = mock_data
        
        # Call the method with a specific timestamp
        since_date = datetime.now() - timedelta(days=7)
        result = self.ingestor.fetch_new_data(since=since_date)
        
        # Assertions
        self.assertEqual(result, mock_data)
        mock_run_sync.assert_called_once()

    @patch('ici.adapters.ingestors.telegram.TelegramIngestor._run_sync')
    def test_fetch_data_in_range(self, mock_run_sync):
        """Test fetching data in a specific date range."""
        # Set up the mock return value
        mock_data = {
            "conversations": [self.sample_conversation],
            "messages": [self.sample_message]
        }
        mock_run_sync.return_value = mock_data
        
        # Call the method with a date range
        start_date = datetime.now() - timedelta(days=14)
        end_date = datetime.now() - timedelta(days=7)
        result = self.ingestor.fetch_data_in_range(start=start_date, end=end_date)
        
        # Assertions
        self.assertEqual(result, mock_data)
        mock_run_sync.assert_called_once()

    def test_healthcheck_healthy(self):
        """Test healthcheck when connected."""
        # Mock get_me result
        self.ingestor._run_sync = MagicMock()
        self.ingestor._run_sync.return_value = MagicMock(
            id=12345,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        
        # Call the method
        result = self.ingestor.healthcheck()
        
        # Assertions
        self.assertTrue(result["healthy"])
        self.assertEqual(result["message"], "Connected to Telegram")
        self.assertIn("details", result)
        self.assertEqual(result["details"]["user_id"], 12345)

    def test_healthcheck_not_connected(self):
        """Test healthcheck when not connected."""
        # Set up as not connected
        self.ingestor._is_connected = False
        
        # Call the method
        result = self.ingestor.healthcheck()
        
        # Assertions
        self.assertFalse(result["healthy"])
        self.assertEqual(result["message"], "Not connected to Telegram")

    @patch('ici.adapters.ingestors.telegram.TelegramClient')
    @patch('ici.adapters.ingestors.telegram.os.makedirs')
    async def test_connect(self, mock_makedirs, mock_telegram_client):
        """Test connection to Telegram."""
        # Set up async mock
        mock_client = AsyncMock()
        mock_telegram_client.return_value = mock_client
        
        # Configuration
        config = {
            "api_id": "12345",
            "api_hash": "abcdef123456",
            "phone_number": "+12345678901",
            "session_file": "test_session",
            "request_delay": 1.0
        }
        
        # Call the method
        result = await self.ingestor._connect(config)
        
        # Assertions
        self.assertTrue(result)
        mock_telegram_client.assert_called_once_with(
            "test_session", "12345", "abcdef123456"
        )
        mock_client.start.assert_called_once_with("+12345678901")
        self.assertEqual(self.ingestor._request_delay, 1.0)

    @patch('ici.adapters.ingestors.telegram.TelegramClient')
    @patch('ici.adapters.ingestors.telegram.StringSession')
    @patch('ici.adapters.ingestors.telegram.os.makedirs')
    async def test_connect_with_session_string(self, mock_makedirs, mock_string_session, mock_telegram_client):
        """Test connection to Telegram using a session string."""
        # Set up async mock
        mock_client = AsyncMock()
        mock_telegram_client.return_value = mock_client
        
        # Mock StringSession
        mock_string_session.return_value = "parsed_session_string"
        
        # Configuration with session string
        config = {
            "api_id": "12345",
            "api_hash": "abcdef123456",
            "phone_number": "+12345678901",
            "session_string": "1BQANOTEuMTA4LjU...",
            "request_delay": 1.0
        }
        
        # Call the method
        result = await self.ingestor._connect(config)
        
        # Assertions
        self.assertTrue(result)
        mock_string_session.assert_called_once_with("1BQANOTEuMTA4LjU...")
        mock_telegram_client.assert_called_once_with(
            "parsed_session_string", "12345", "abcdef123456"
        )
        mock_client.start.assert_called_once_with("+12345678901")
        self.assertEqual(self.ingestor._request_delay, 1.0)

    @patch('ici.adapters.ingestors.telegram.TelegramClient')
    async def test_connect_missing_params(self, mock_telegram_client):
        """Test connection with missing parameters."""
        # Configuration with missing api_hash
        config = {
            "api_id": "12345",
            "phone_number": "+12345678901",
        }
        
        # Call the method
        result = await self.ingestor._connect(config)
        
        # Assertions
        self.assertFalse(result)
        mock_telegram_client.assert_not_called()

    async def test_disconnect(self):
        """Test disconnection from Telegram."""
        # Set up mock client
        self.ingestor._client = AsyncMock()
        
        # Call the method
        await self.ingestor._disconnect()
        
        # Assertions
        self.ingestor._client.disconnect.assert_called_once()
        self.assertFalse(self.ingestor._is_connected)

    @patch('ici.adapters.ingestors.telegram.asyncio.sleep')
    async def test_get_conversations(self, mock_sleep):
        """Test retrieving conversations."""
        # Set up mock client response
        mock_dialog = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 12345
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.username = "testuser"
        mock_user.bot = False
        
        mock_dialog.entity = mock_user
        mock_dialog.unread_count = 2
        mock_dialog.date = datetime.now()
        
        mock_result = MagicMock()
        mock_result.dialogs = [mock_dialog]
        mock_result.messages = [MagicMock(date=datetime.now(), id=1001)]
        
        self.ingestor._client = AsyncMock()
        self.ingestor._client.return_value = mock_result
        
        # Call the method
        result = await self.ingestor._get_conversations()
        
        # Assertions
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "12345")
        self.assertEqual(result[0]["name"], "Test User")
        self.assertEqual(result[0]["type"], "direct")

    @patch('ici.adapters.ingestors.telegram.asyncio.sleep')
    async def test_get_messages(self, mock_sleep):
        """Test retrieving messages."""
        # Set up mock client and messages
        mock_message = MagicMock()
        mock_message.id = 1001
        mock_message.date = datetime.now()
        mock_message.text = "Test message"
        mock_message.out = False
        mock_message.reply_to_msg_id = None
        mock_message.photo = None
        mock_message.video = None
        mock_message.audio = None
        mock_message.voice = None
        mock_message.document = None
        mock_message.sticker = None
        mock_message.poll = None
        
        self.ingestor._client = AsyncMock()
        self.ingestor._client.get_entity.return_value = MagicMock()
        self.ingestor._client.get_messages.return_value = [mock_message]
        
        # Call the method
        result = await self.ingestor._get_messages("12345", limit=10)
        
        # Assertions
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "1001")
        self.assertEqual(result[0]["text"], "Test message")
        self.assertEqual(result[0]["outgoing"], False)
        self.assertIsNone(result[0]["media_type"])

    def test_get_media_type(self):
        """Test detection of media types."""
        # Test photo
        mock_message = MagicMock()
        mock_message.photo = True
        mock_message.video = None
        mock_message.audio = None
        mock_message.voice = None
        mock_message.document = None
        mock_message.sticker = None
        mock_message.poll = None
        
        self.assertEqual(self.ingestor._get_media_type(mock_message), "photo")
        
        # Test video
        mock_message.photo = None
        mock_message.video = True
        self.assertEqual(self.ingestor._get_media_type(mock_message), "video")
        
        # Test text only
        mock_message.photo = None
        mock_message.video = None
        self.assertIsNone(self.ingestor._get_media_type(mock_message))


if __name__ == '__main__':
    unittest.main() 