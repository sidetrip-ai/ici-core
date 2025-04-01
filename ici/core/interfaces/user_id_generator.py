from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class UserIDGenerator(ABC):
    """
    Interface for components that generate and validate user IDs.
    
    The UserIDGenerator is responsible for creating consistent user identifiers
    across different sources/connectors, following a standardized format.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the user ID generator with configuration parameters.
        
        This method should be called after the generator instance is created,
        before any other methods are used. Configuration should be loaded from
        a central configuration source (e.g., config.yaml).
        
        Returns:
            None
        
        Raises:
            UserIDError: If initialization fails for any reason.
        """
        pass

    @abstractmethod
    async def generate_id(self, source: str, identifier: Optional[str] = None) -> str:
        """
        Generates a unique user ID based on source and identifier.
        
        Args:
            source: The connector/source type (e.g., 'cli', 'telegram', 'web')
            identifier: A unique identifier within that source. If None,
                        an appropriate identifier will be generated.
            
        Returns:
            str: A unique composite user ID in the format "{source}:{identifier}"
        
        Raises:
            UserIDError: If ID generation fails or parameters are invalid
        """
        pass

    @abstractmethod
    async def validate_id(self, user_id: str) -> bool:
        """
        Validates a user ID format.
        
        Args:
            user_id: The user ID to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        pass

    @abstractmethod
    async def parse_id(self, user_id: str) -> Dict[str, str]:
        """
        Parses a user ID into its component parts.
        
        Args:
            user_id: The user ID to parse
            
        Returns:
            Dict[str, str]: A dictionary containing the 'source' and 'identifier'
        
        Raises:
            UserIDError: If the ID format is invalid and cannot be parsed
        """
        pass

    @abstractmethod
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Checks if the user ID generator is properly configured and functioning.
        
        Returns:
            Dict[str, Any]: A dictionary containing health status information:
                {
                    'healthy': bool,  # Whether the generator is functioning properly
                    'message': str,   # Optional message providing more details
                    'details': dict   # Optional additional details about the health check
                }
                
        Raises:
            UserIDError: If the health check itself encounters an error
        """
        pass 