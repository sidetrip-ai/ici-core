"""
Schema definition for Telegram conversation JSON storage.
This defines the structure for storing Telegram conversations according to the PRD.
"""

from typing import Dict, Any

# Definition of the JSON schema for Telegram conversations
TELEGRAM_SCHEMA = {
    "type": "object",
    "required": ["metadata", "messages"],
    "properties": {
        "metadata": {
            "type": "object",
            "required": ["id", "chat_type", "last_message", "last_updated"],
            "properties": {
                "id": {"type": ["string", "integer"]},
                "name": {"type": "string"},
                "username": {"type": ["string", "null"]},
                "is_group": {"type": "boolean"},
                "chat_type": {"type": "string"},
                "last_message": {
                    "type": "object",
                    "properties": {
                        "id": {"type": ["string", "integer"]},
                        "text": {"type": ["string", "null"]},
                        "date": {"type": ["string", "null"], "format": "date-time"}
                    }
                },
                "last_updated": {"type": ["string", "null"], "format": "date-time"},
                "unread_count": {"type": ["integer", "null"]},
                "source": {"type": "string"},
                "chatId": {"type": ["string", "integer"]},
                "isGroup": {"type": "boolean"},
                "conversation_types": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "participants": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["id"],
                        "properties": {
                            "id": {"type": ["string", "integer"]},
                            "username": {"type": ["string", "null"]},
                            "first_name": {"type": ["string", "null"]},
                            "last_name": {"type": ["string", "null"]}
                        }
                    }
                }
            }
        },
        "messages": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["sender_id", "date", "text"],
                "properties": {
                    "sender_id": {"type": ["string", "integer", "null"]},
                    "sender_name": {"type": ["string", "null"]},
                    "text": {"type": "string"},
                    "date": {"type": "string", "format": "date-time"},
                    "is_outgoing": {"type": "boolean"},
                    "reply_to_id": {"type": ["string", "integer", "null"]},
                    "media_type": {"type": ["string", "null"]},
                    "media_path": {"type": ["string", "null"]},
                    "entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "offset": {"type": "integer"},
                                "length": {"type": "integer"},
                                "url": {"type": ["string", "null"]}
                            }
                        }
                    },
                    "reactions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "emoji": {"type": "string"},
                                "count": {"type": "integer"},
                                "user_ids": {
                                    "type": "array",
                                    "items": {"type": ["string", "integer"]}
                                }
                            }
                        }
                    },
                    "forwarded_from": {"type": ["string", "integer", "null"]},
                    "raw_data": {"type": "object"}
                }
            }
        }
    }
}

# Sample conversation structure for documentation and testing
SAMPLE_CONVERSATION: Dict[str, Any] = {
    "metadata": {
        "conversation_id": "12345",
        "name": "John Doe",
        "username": "johndoe",
        "is_group": False,
        "chat_type": "private",
        "last_message_date": "2023-11-15T12:30:45Z",
        "last_update": "2023-11-15T12:30:45Z",
        "participants": [
            {
                "id": "user123",
                "username": "johndoe",
                "first_name": "John",
                "last_name": "Doe"
            },
            {
                "id": "user456",
                "username": "icibot",
                "first_name": "ICI",
                "last_name": "Bot"
            }
        ]
    },
    "messages": {
        "msg_1": {
            "sender_id": "user123",
            "sender_name": "John Doe",
            "text": "Hello, how are you?",
            "date": "2023-11-15T12:30:00Z",
            "is_outgoing": True,
            "reply_to_id": None,
            "media_type": None,
            "media_path": None,
            "entities": [],
            "reactions": [],
            "forwarded_from": None,
            "raw_data": {}
        },
        "msg_2": {
            "sender_id": "user456",
            "sender_name": "ICI Bot",
            "text": "I'm doing well, thank you!",
            "date": "2023-11-15T12:30:45Z",
            "is_outgoing": False,
            "reply_to_id": "msg_1",
            "media_type": None,
            "media_path": None,
            "entities": [],
            "reactions": [
                {
                    "emoji": "👍",
                    "count": 1,
                    "user_ids": ["user123"]
                }
            ],
            "forwarded_from": None,
            "raw_data": {}
        }
    }
} 