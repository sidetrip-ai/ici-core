"""
Chat history management implementation using JSON files.
"""

import os
import json
import uuid
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from ici.core.interfaces import ChatHistoryManager
from ici.core.exceptions import ChatHistoryError, ChatIDError, ChatStorageError, UserIDError
from ici.adapters.loggers import StructuredLogger


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
    
    def __init__(self):
        """Initialize the JSONChatHistoryManager."""
        self.logger = StructuredLogger(name="chat_history_manager")
        self.base_path = "./chats"
        self.use_subdirectories = True
        self.file_permissions = 0o600
        self.default_message_limit = 20
        self.max_messages_per_chat = 1000
        self.initialized = False
        self.lock = asyncio.Lock()  # Lock for thread safety
    
    async def initialize(self) -> None:
        """
        Initialize the chat history manager with configuration parameters.
        
        Raises:
            ChatHistoryError: If initialization fails.
        """
        try:
            # In a real implementation, load config from YAML
            # For now, we use hardcoded defaults
            os.makedirs(self.base_path, exist_ok=True)
            self.logger.info(f"Initialized JSONChatHistoryManager with base path: {self.base_path}")
            self.initialized = True
        except Exception as e:
            self.logger.error(f"Failed to initialize JSONChatHistoryManager: {e}")
            raise ChatHistoryError(f"Initialization failed: {e}")
    
    def _check_initialized(self) -> None:
        """Check if the manager is initialized."""
        if not self.initialized:
            raise ChatHistoryError("ChatHistoryManager not initialized. Call initialize() first.")
    
    def _get_chat_path(self, user_id: str, chat_id: str) -> str:
        """
        Get the file path for a specific chat.
        
        Args:
            user_id: The user ID
            chat_id: The chat ID
            
        Returns:
            str: The path to the chat file
        """
        if not user_id or not isinstance(user_id, str):
            raise UserIDError(f"Invalid user_id: {user_id}")
        if not chat_id or not isinstance(chat_id, str):
            raise ChatIDError(f"Invalid chat_id: {chat_id}")
            
        if self.use_subdirectories:
            user_dir = os.path.join(self.base_path, user_id)
            os.makedirs(user_dir, exist_ok=True)
            return os.path.join(user_dir, f"{chat_id}.json")
        else:
            return os.path.join(self.base_path, f"{user_id}_{chat_id}.json")
    
    def _get_user_dir(self, user_id: str) -> str:
        """
        Get the directory for a user's chats.
        
        Args:
            user_id: The user ID
            
        Returns:
            str: The path to the user's directory
        """
        if not user_id or not isinstance(user_id, str):
            raise UserIDError(f"Invalid user_id: {user_id}")
            
        if self.use_subdirectories:
            user_dir = os.path.join(self.base_path, user_id)
            os.makedirs(user_dir, exist_ok=True)
            return user_dir
        return self.base_path
    
    async def _load_chat(self, chat_path: str) -> Dict[str, Any]:
        """
        Load a chat from file.
        
        Args:
            chat_path: Path to the chat file
            
        Returns:
            Dict[str, Any]: The chat data
            
        Raises:
            ChatStorageError: If the chat cannot be loaded
        """
        try:
            async with self.lock:
                if not os.path.exists(chat_path):
                    raise ChatIDError(f"Chat file not found: {chat_path}")
                    
                with open(chat_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except json.JSONDecodeError as e:
            raise ChatStorageError(f"Invalid JSON in chat file {chat_path}: {e}")
        except Exception as e:
            raise ChatStorageError(f"Failed to load chat from {chat_path}: {e}")
    
    async def _save_chat(self, chat_data: Dict[str, Any], chat_path: str) -> None:
        """
        Save a chat to file.
        
        Args:
            chat_data: The chat data to save
            chat_path: Path to the chat file
            
        Raises:
            ChatStorageError: If the chat cannot be saved
        """
        try:
            async with self.lock:
                # Ensure the directory exists
                os.makedirs(os.path.dirname(chat_path), exist_ok=True)
                
                # Write to a temporary file first, then rename for atomicity
                temp_path = f"{chat_path}.tmp"
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(chat_data, f, indent=2, ensure_ascii=False)
                
                # Set permissions before renaming
                os.chmod(temp_path, self.file_permissions)
                
                # Rename (atomic operation on most filesystems)
                os.replace(temp_path, chat_path)
        except Exception as e:
            raise ChatStorageError(f"Failed to save chat to {chat_path}: {e}")
    
    async def _find_chat_file_by_id(self, chat_id: str) -> str:
        """
        Find a chat file by its ID.
        
        Args:
            chat_id: The chat ID to find
            
        Returns:
            str: The path to the chat file
            
        Raises:
            ChatIDError: If the chat file cannot be found
        """
        # This could be optimized in a real implementation with indexing
        # For now, search through all files (inefficient but simple)
        for root, dirs, files in os.walk(self.base_path):
            for file in files:
                if file == f"{chat_id}.json" or file.endswith(f"_{chat_id}.json"):
                    return os.path.join(root, file)
        
        raise ChatIDError(f"Chat ID not found: {chat_id}")
    
    async def create_chat(self, user_id: str) -> str:
        """
        Creates a new empty chat session for a user.
        
        Args:
            user_id: The unique identifier for the user
            
        Returns:
            str: The unique chat_id of the newly created chat
            
        Raises:
            ChatHistoryError: If the chat cannot be created
            UserIDError: If the user_id is invalid
        """
        self._check_initialized()
        
        try:
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
            await self._save_chat(chat_data, chat_path)
            
            self.logger.info(f"Created new chat {chat_id} for user {user_id}")
            return chat_id
        except UserIDError as e:
            # Re-raise user ID errors
            raise
        except Exception as e:
            raise ChatHistoryError(f"Failed to create chat for user {user_id}: {e}")
    
    async def add_message(
        self, chat_id: str, content: str, role: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Adds a message to the specified chat.
        
        Args:
            chat_id: The unique identifier for the chat
            content: The message content
            role: The role of the message sender ('user' or 'assistant')
            metadata: Optional additional data to store with the message
            
        Returns:
            str: The unique message_id of the added message
            
        Raises:
            ChatHistoryError: If the message cannot be added
            ChatIDError: If the chat_id is invalid or not found
        """
        self._check_initialized()
        
        if role not in ["user", "assistant", "system"]:
            raise ChatHistoryError(f"Invalid role: {role}. Must be 'user', 'assistant', or 'system'.")
        
        try:
            # Find the chat file
            chat_path = await self._find_chat_file_by_id(chat_id)
            
            # Load the chat
            chat_data = await self._load_chat(chat_path)
            
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
            
            # Apply maximum message limit if configured
            if self.max_messages_per_chat > 0 and len(chat_data["messages"]) > self.max_messages_per_chat:
                # Remove oldest messages to stay within limit
                excess = len(chat_data["messages"]) - self.max_messages_per_chat
                chat_data["messages"] = chat_data["messages"][excess:]
                chat_data["message_count"] = len(chat_data["messages"])
            
            # Save updated chat
            await self._save_chat(chat_data, chat_path)
            
            self.logger.info(f"Added {role} message {message_id} to chat {chat_id}")
            return message_id
        except ChatIDError:
            # Re-raise chat ID errors
            raise
        except Exception as e:
            raise ChatHistoryError(f"Failed to add message to chat {chat_id}: {e}")
    
    async def get_messages(
        self, chat_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves messages from a chat, ordered chronologically (oldest first).
        
        Args:
            chat_id: The unique identifier for the chat
            limit: Optional maximum number of messages to retrieve (most recent if limited)
            
        Returns:
            List[Dict[str, Any]]: List of message objects with their metadata
            
        Raises:
            ChatHistoryError: If the messages cannot be retrieved
            ChatIDError: If the chat_id is invalid or not found
        """
        self._check_initialized()
        
        try:
            # Find the chat file
            chat_path = await self._find_chat_file_by_id(chat_id)
            
            # Load the chat
            chat_data = await self._load_chat(chat_path)
            
            # Get messages (newest last)
            messages = chat_data["messages"]
            
            # Apply limit if provided, otherwise use default
            actual_limit = limit or self.default_message_limit
            if actual_limit > 0 and len(messages) > actual_limit:
                messages = messages[-actual_limit:]
            
            return messages
        except ChatIDError:
            # Re-raise chat ID errors
            raise
        except Exception as e:
            raise ChatHistoryError(f"Failed to get messages from chat {chat_id}: {e}")
    
    async def list_chats(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Returns a list of chat sessions for the user.
        
        Args:
            user_id: The unique identifier for the user
            
        Returns:
            List[Dict[str, Any]]: List of chat metadata objects, sorted by most recent first
            
        Raises:
            ChatHistoryError: If the chat list cannot be retrieved
            UserIDError: If the user_id is invalid
        """
        self._check_initialized()
        
        try:
            user_dir = self._get_user_dir(user_id)
            chats = []
            
            # Find all chat files for this user
            if self.use_subdirectories:
                # Look in user-specific directory
                if not os.path.exists(user_dir):
                    # No chats for this user yet
                    return []
                    
                for file in os.listdir(user_dir):
                    if file.endswith(".json") and not file.endswith(".tmp"):
                        chat_path = os.path.join(user_dir, file)
                        try:
                            chat_data = await self._load_chat(chat_path)
                            # Extract only the metadata, not the messages
                            chat_info = {k: v for k, v in chat_data.items() if k != "messages"}
                            chats.append(chat_info)
                        except Exception as e:
                            self.logger.warning(f"Error loading chat {file}: {e}")
            else:
                # Look for files with user_id prefix
                if not os.path.exists(self.base_path):
                    # No chats yet
                    return []
                    
                for file in os.listdir(self.base_path):
                    if file.startswith(f"{user_id}_") and file.endswith(".json") and not file.endswith(".tmp"):
                        chat_path = os.path.join(self.base_path, file)
                        try:
                            chat_data = await self._load_chat(chat_path)
                            # Extract only the metadata, not the messages
                            chat_info = {k: v for k, v in chat_data.items() if k != "messages"}
                            chats.append(chat_info)
                        except Exception as e:
                            self.logger.warning(f"Error loading chat {file}: {e}")
            
            # Sort by updated_at descending (newest first)
            chats.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            
            return chats
        except UserIDError:
            # Re-raise user ID errors
            raise
        except Exception as e:
            raise ChatHistoryError(f"Failed to list chats for user {user_id}: {e}")
    
    async def generate_title(self, chat_id: str) -> Optional[str]:
        """
        Generates or updates a concise title for the chat based on its content.
        
        Args:
            chat_id: The unique identifier for the chat
            
        Returns:
            Optional[str]: The generated title, or None if title generation fails
            
        Raises:
            ChatHistoryError: If title generation fails
            ChatIDError: If the chat_id is invalid or not found
        """
        self._check_initialized()
        
        try:
            # Find the chat file
            chat_path = await self._find_chat_file_by_id(chat_id)
            
            # Load the chat
            chat_data = await self._load_chat(chat_path)
            
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
                    await self._save_chat(chat_data, chat_path)
                    
                    self.logger.info(f"Generated title for chat {chat_id}: {title}")
                    return title
            
            return None
        except ChatIDError:
            # Re-raise chat ID errors
            raise
        except Exception as e:
            raise ChatHistoryError(f"Failed to generate title for chat {chat_id}: {e}")
    
    async def rename_chat(self, chat_id: str, new_title: str) -> bool:
        """
        Manually renames a chat session.
        
        Args:
            chat_id: The unique identifier for the chat
            new_title: The new title for the chat
            
        Returns:
            bool: True if rename was successful, False otherwise
            
        Raises:
            ChatHistoryError: If the rename operation fails
            ChatIDError: If the chat_id is invalid or not found
        """
        self._check_initialized()
        
        try:
            # Find the chat file
            chat_path = await self._find_chat_file_by_id(chat_id)
            
            # Load the chat
            chat_data = await self._load_chat(chat_path)
            
            # Update title
            chat_data["title"] = new_title
            chat_data["updated_at"] = datetime.utcnow().isoformat()
            
            # Save updated chat
            await self._save_chat(chat_data, chat_path)
            
            self.logger.info(f"Renamed chat {chat_id} to '{new_title}'")
            return True
        except ChatIDError:
            # Re-raise chat ID errors
            raise
        except Exception as e:
            raise ChatHistoryError(f"Failed to rename chat {chat_id}: {e}")
    
    async def delete_chat(self, chat_id: str) -> bool:
        """
        Deletes a chat session and all associated messages.
        
        Args:
            chat_id: The unique identifier for the chat
            
        Returns:
            bool: True if deletion was successful, False otherwise
            
        Raises:
            ChatHistoryError: If the delete operation fails
            ChatIDError: If the chat_id is invalid or not found
        """
        self._check_initialized()
        
        try:
            # Find the chat file
            chat_path = await self._find_chat_file_by_id(chat_id)
            
            # Delete the file
            async with self.lock:
                os.remove(chat_path)
            
            self.logger.info(f"Deleted chat {chat_id}")
            return True
        except ChatIDError:
            # Re-raise chat ID errors
            raise
        except Exception as e:
            raise ChatHistoryError(f"Failed to delete chat {chat_id}: {e}")
    
    async def export_chat(self, chat_id: str, format: str = "json") -> Any:
        """
        Exports the chat history in a specified format.
        
        Args:
            chat_id: The unique identifier for the chat
            format: The export format ("json" or "text")
            
        Returns:
            Any: The exported chat data in the requested format
            
        Raises:
            ChatHistoryError: If the export operation fails
            ChatIDError: If the chat_id is invalid or not found
        """
        self._check_initialized()
        
        if format not in ["json", "text"]:
            raise ChatHistoryError(f"Unsupported export format: {format}")
        
        try:
            # Find the chat file
            chat_path = await self._find_chat_file_by_id(chat_id)
            
            # Load the chat
            chat_data = await self._load_chat(chat_path)
            
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
        except ChatIDError:
            # Re-raise chat ID errors
            raise
        except Exception as e:
            raise ChatHistoryError(f"Failed to export chat {chat_id}: {e}")
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Checks if the chat history manager is properly configured and functioning.
        
        Returns:
            Dict[str, Any]: A dictionary containing health status information
                
        Raises:
            ChatHistoryError: If the health check itself encounters an error
        """
        try:
            # Check if base path exists and is writable
            base_path_exists = os.path.exists(self.base_path)
            base_path_writable = os.access(self.base_path, os.W_OK) if base_path_exists else False
            
            details = {
                "base_path_exists": base_path_exists,
                "base_path_writable": base_path_writable,
                "use_subdirectories": self.use_subdirectories,
                "default_message_limit": self.default_message_limit,
                "max_messages_per_chat": self.max_messages_per_chat,
                "initialized": self.initialized
            }
            
            # Healthy if initialized and base path is writable
            healthy = self.initialized and base_path_writable
            
            # Generate appropriate message
            if not self.initialized:
                message = "Chat history manager not initialized"
            elif not base_path_exists:
                message = f"Base path does not exist: {self.base_path}"
            elif not base_path_writable:
                message = f"Base path is not writable: {self.base_path}"
            else:
                message = "Chat history manager is healthy"
            
            return {
                "healthy": healthy,
                "message": message,
                "details": details
            }
        except Exception as e:
            raise ChatHistoryError(f"Health check failed: {e}") 