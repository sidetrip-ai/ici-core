"""
Example implementation of ChatHistoryManager using JSON files for storage.
This is a reference implementation to demonstrate the concept.
"""

import os
import json
import uuid
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
import logging
import shutil

class ChatHistoryManager(ABC):
    """
    Abstract base class defining the interface for chat history management.
    """
    @abstractmethod
    def create_chat(self, user_id: str) -> str:
        """Creates a new empty chat session for a user and returns its unique chat_id."""
        pass

    @abstractmethod
    def add_message(self, chat_id: str, content: str, role: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Adds a message to the specified chat and returns its unique message_id.
        Role should be 'user' or 'assistant'. Metadata can include timestamps, sources, etc.
        """
        pass

    @abstractmethod
    def get_messages(self, chat_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieves messages from a chat, ordered chronologically (oldest first).
        If limit is provided, returns the 'limit' most recent messages.
        """
        pass

    @abstractmethod
    def list_chats(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Returns a list of chat sessions for the user, typically including chat_id, title,
        created_at, updated_at. Sorted by updated_at descending (most recent first).
        """
        pass

    @abstractmethod
    def generate_title(self, chat_id: str) -> Optional[str]:
        """
        Generates or updates a concise title for the chat based on its content.
        Can be triggered automatically after a few messages. Returns the new title or None if unable.
        """
        pass

    @abstractmethod
    def rename_chat(self, chat_id: str, new_title: str) -> bool:
        """Manually renames a chat session. Returns True on success, False otherwise."""
        pass

    @abstractmethod
    def delete_chat(self, chat_id: str) -> bool:
        """Deletes a chat session and all associated messages. Returns True on success."""
        pass

    @abstractmethod
    def export_chat(self, chat_id: str, format: str = "json") -> Any:
        """Exports the chat history in a specified format (e.g., JSON, text)."""
        pass


class JSONChatHistoryManager(ChatHistoryManager):
    """
    Implementation of ChatHistoryManager using JSON files for storage.
    
    Storage structure:
    ./base_path/
        user_id_1/
            chat_id_1.json
            chat_id_2.json
        user_id_2/
            chat_id_3.json
            ...
    """
    
    def __init__(self, base_path: str = "./chats", use_subdirectories: bool = True):
        """
        Initialize with the base directory for chat storage.
        
        Args:
            base_path: Directory where chat files will be stored
            use_subdirectories: Whether to use user_id subdirectories for better organization
        """
        self.base_path = base_path
        self.use_subdirectories = use_subdirectories
        self.logger = logging.getLogger("JSONChatHistoryManager")
        
        # Create base directory if it doesn't exist
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)
            self.logger.info(f"Created base chat directory at {self.base_path}")
    
    def _get_chat_path(self, user_id: str, chat_id: str) -> str:
        """Get the file path for a specific chat."""
        if self.use_subdirectories:
            user_dir = os.path.join(self.base_path, user_id)
            if not os.path.exists(user_dir):
                os.makedirs(user_dir)
            return os.path.join(user_dir, f"{chat_id}.json")
        else:
            return os.path.join(self.base_path, f"{user_id}_{chat_id}.json")
    
    def _get_user_dir(self, user_id: str) -> str:
        """Get the directory for a user's chats."""
        if self.use_subdirectories:
            return os.path.join(self.base_path, user_id)
        return self.base_path
    
    def _load_chat(self, chat_path: str) -> Dict[str, Any]:
        """Load a chat from file."""
        try:
            with open(chat_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            self.logger.error(f"Error loading chat from {chat_path}: {e}")
            raise ValueError(f"Could not load chat: {e}")
    
    def _save_chat(self, chat_data: Dict[str, Any], chat_path: str) -> None:
        """Save a chat to file."""
        try:
            with open(chat_path, 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            self.logger.error(f"Error saving chat to {chat_path}: {e}")
            raise ValueError(f"Could not save chat: {e}")
    
    def create_chat(self, user_id: str) -> str:
        """Creates a new chat for the user."""
        chat_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        chat_data = {
            "chat_id": chat_id,
            "user_id": user_id,
            "title": "New Chat",  # Default title
            "created_at": now,
            "updated_at": now,
            "message_count": 0,
            "is_pinned": False,
            "last_message_preview": "",
            "messages": []
        }
        
        chat_path = self._get_chat_path(user_id, chat_id)
        self._save_chat(chat_data, chat_path)
        
        self.logger.info(f"Created new chat {chat_id} for user {user_id}")
        return chat_id
    
    def add_message(self, chat_id: str, content: str, role: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Adds a message to a chat."""
        if role not in ["user", "assistant", "system"]:
            raise ValueError(f"Invalid role: {role}. Must be 'user', 'assistant', or 'system'.")
        
        # Find the chat file
        chat_path = None
        for root, dirs, files in os.walk(self.base_path):
            for file in files:
                if file == f"{chat_id}.json" or file.endswith(f"_{chat_id}.json"):
                    chat_path = os.path.join(root, file)
                    break
            if chat_path:
                break
        
        if not chat_path:
            raise ValueError(f"Chat {chat_id} not found")
        
        # Load the chat
        chat_data = self._load_chat(chat_path)
        
        # Create new message
        message_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        message = {
            "message_id": message_id,
            "role": role,
            "content": content,
            "created_at": now,
            "metadata": metadata or {}
        }
        
        # Add message to chat
        chat_data["messages"].append(message)
        chat_data["message_count"] += 1
        chat_data["updated_at"] = now
        chat_data["last_message_preview"] = content[:50] + ("..." if len(content) > 50 else "")
        
        # Save updated chat
        self._save_chat(chat_data, chat_path)
        
        self.logger.info(f"Added {role} message {message_id} to chat {chat_id}")
        return message_id
    
    def get_messages(self, chat_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieves messages from a chat."""
        # Find the chat file
        chat_path = None
        for root, dirs, files in os.walk(self.base_path):
            for file in files:
                if file == f"{chat_id}.json" or file.endswith(f"_{chat_id}.json"):
                    chat_path = os.path.join(root, file)
                    break
            if chat_path:
                break
        
        if not chat_path:
            raise ValueError(f"Chat {chat_id} not found")
        
        # Load the chat
        chat_data = self._load_chat(chat_path)
        
        # Get messages (newest last)
        messages = chat_data["messages"]
        
        # Apply limit if provided
        if limit and limit > 0:
            messages = messages[-limit:]
        
        return messages
    
    def list_chats(self, user_id: str) -> List[Dict[str, Any]]:
        """Lists all chats for a user."""
        user_dir = self._get_user_dir(user_id)
        if not os.path.exists(user_dir):
            return []
        
        chats = []
        
        # Find all chat files for this user
        if self.use_subdirectories:
            # Look in user-specific directory
            for file in os.listdir(user_dir):
                if file.endswith(".json"):
                    chat_path = os.path.join(user_dir, file)
                    try:
                        chat_data = self._load_chat(chat_path)
                        # Extract only the metadata, not the messages
                        chat_info = {k: v for k, v in chat_data.items() if k != "messages"}
                        chats.append(chat_info)
                    except Exception as e:
                        self.logger.warning(f"Error loading chat {file}: {e}")
        else:
            # Look for files with user_id prefix
            for file in os.listdir(user_dir):
                if file.startswith(f"{user_id}_") and file.endswith(".json"):
                    chat_path = os.path.join(user_dir, file)
                    try:
                        chat_data = self._load_chat(chat_path)
                        # Extract only the metadata, not the messages
                        chat_info = {k: v for k, v in chat_data.items() if k != "messages"}
                        chats.append(chat_info)
                    except Exception as e:
                        self.logger.warning(f"Error loading chat {file}: {e}")
        
        # Sort by updated_at descending (newest first)
        chats.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        return chats
    
    def generate_title(self, chat_id: str) -> Optional[str]:
        """Generates a title for the chat based on content."""
        # Find the chat file
        chat_path = None
        for root, dirs, files in os.walk(self.base_path):
            for file in files:
                if file == f"{chat_id}.json" or file.endswith(f"_{chat_id}.json"):
                    chat_path = os.path.join(root, file)
                    break
            if chat_path:
                break
        
        if not chat_path:
            raise ValueError(f"Chat {chat_id} not found")
        
        # Load the chat
        chat_data = self._load_chat(chat_path)
        
        # Simple title generation based on first user message
        # In a real implementation, we might use a language model for better titles
        messages = chat_data["messages"]
        if not messages:
            return None
        
        # Find first user message
        for msg in messages:
            if msg["role"] == "user":
                # Use first 50 characters of content as title
                title = msg["content"][:50]
                if len(msg["content"]) > 50:
                    title += "..."
                
                # Update chat data
                chat_data["title"] = title
                self._save_chat(chat_data, chat_path)
                
                self.logger.info(f"Generated title for chat {chat_id}: {title}")
                return title
        
        return None
    
    def rename_chat(self, chat_id: str, new_title: str) -> bool:
        """Renames a chat."""
        # Find the chat file
        chat_path = None
        for root, dirs, files in os.walk(self.base_path):
            for file in files:
                if file == f"{chat_id}.json" or file.endswith(f"_{chat_id}.json"):
                    chat_path = os.path.join(root, file)
                    break
            if chat_path:
                break
        
        if not chat_path:
            return False
        
        try:
            # Load the chat
            chat_data = self._load_chat(chat_path)
            
            # Update title
            chat_data["title"] = new_title
            
            # Save updated chat
            self._save_chat(chat_data, chat_path)
            
            self.logger.info(f"Renamed chat {chat_id} to '{new_title}'")
            return True
        except Exception as e:
            self.logger.error(f"Error renaming chat {chat_id}: {e}")
            return False
    
    def delete_chat(self, chat_id: str) -> bool:
        """Deletes a chat."""
        # Find the chat file
        chat_path = None
        for root, dirs, files in os.walk(self.base_path):
            for file in files:
                if file == f"{chat_id}.json" or file.endswith(f"_{chat_id}.json"):
                    chat_path = os.path.join(root, file)
                    break
            if chat_path:
                break
        
        if not chat_path:
            return False
        
        try:
            # Delete the file
            os.remove(chat_path)
            self.logger.info(f"Deleted chat {chat_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting chat {chat_id}: {e}")
            return False
    
    def export_chat(self, chat_id: str, format: str = "json") -> Any:
        """Exports a chat in the specified format."""
        # Find the chat file
        chat_path = None
        for root, dirs, files in os.walk(self.base_path):
            for file in files:
                if file == f"{chat_id}.json" or file.endswith(f"_{chat_id}.json"):
                    chat_path = os.path.join(root, file)
                    break
            if chat_path:
                break
        
        if not chat_path:
            raise ValueError(f"Chat {chat_id} not found")
        
        # Load the chat
        chat_data = self._load_chat(chat_path)
        
        if format == "json":
            return chat_data
        elif format == "text":
            # Create text representation
            text = f"Title: {chat_data['title']}\n"
            text += f"Created: {chat_data['created_at']}\n"
            text += f"Updated: {chat_data['updated_at']}\n\n"
            
            for msg in chat_data["messages"]:
                text += f"{msg['role'].capitalize()}: {msg['content']}\n\n"
            
            return text
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Create an instance with temp directory
    import tempfile
    temp_dir = tempfile.mkdtemp()
    chat_manager = JSONChatHistoryManager(base_path=temp_dir)
    
    try:
        # Create a chat for a user
        user_id = "user123"
        chat_id = chat_manager.create_chat(user_id)
        print(f"Created chat {chat_id}")
        
        # Add messages
        chat_manager.add_message(chat_id, "Hello, I have a question about Python.", "user")
        chat_manager.add_message(chat_id, "I'd be happy to help with Python. What would you like to know?", "assistant")
        chat_manager.add_message(chat_id, "How do I handle exceptions properly?", "user")
        chat_manager.add_message(chat_id, "To handle exceptions in Python, you should use try/except blocks...", "assistant")
        
        # Generate a title
        title = chat_manager.generate_title(chat_id)
        print(f"Generated title: {title}")
        
        # List all chats for the user
        chats = chat_manager.list_chats(user_id)
        print(f"User has {len(chats)} chats")
        
        # Get messages from the chat
        messages = chat_manager.get_messages(chat_id)
        print(f"Chat has {len(messages)} messages")
        
        # Export the chat
        exported = chat_manager.export_chat(chat_id, format="text")
        print("\nExported chat:")
        print(exported)
        
        # Rename the chat
        chat_manager.rename_chat(chat_id, "Python Exception Handling")
        
        # Create a second chat
        chat_id2 = chat_manager.create_chat(user_id)
        chat_manager.add_message(chat_id2, "I need help with JavaScript.", "user")
        
        # List chats again
        chats = chat_manager.list_chats(user_id)
        print(f"\nUser now has {len(chats)} chats:")
        for chat in chats:
            print(f"- {chat['chat_id']}: {chat['title']} ({chat['message_count']} messages)")
        
        # Delete a chat
        chat_manager.delete_chat(chat_id2)
        chats = chat_manager.list_chats(user_id)
        print(f"\nAfter deletion, user has {len(chats)} chats")
        
    finally:
        # Clean up temp directory
        shutil.rmtree(temp_dir) 