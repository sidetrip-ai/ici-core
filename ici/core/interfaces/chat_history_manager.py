from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class ChatHistoryManager(ABC):
    """
    Interface for managing persistent, multi-turn conversation histories for users,
    enabling contextually aware interactions similar to modern AI chat interfaces.
    Supports multiple distinct chat sessions per user.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the chat history manager with configuration parameters.
        
        This method should be called after the chat history manager instance is created,
        before any other methods are used. Configuration should be loaded from
        a central configuration source (e.g., config.yaml).
        
        Returns:
            None
        
        Raises:
            ChatHistoryError: If initialization fails for any reason.
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Checks if the chat history manager is properly configured and functioning.
        
        Returns:
            Dict[str, Any]: A dictionary containing health status information:
                {
                    'healthy': bool,  # Whether the manager is functioning properly
                    'message': str,   # Optional message providing more details
                    'details': dict   # Optional additional details about the health check
                }
                
        Raises:
            ChatHistoryError: If the health check itself encounters an error
        """
        pass 