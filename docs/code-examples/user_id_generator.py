"""
Example implementation of UserIDGenerator component for different source types.
"""

import uuid
import os
import re
import platform
import socket
import getpass
from abc import ABC, abstractmethod
from typing import Optional

class UserIDGenerator(ABC):
    """
    Abstract base class for user ID generation strategies.
    """
    @abstractmethod
    def generate_id(self, source: str, identifier: str) -> str:
        """
        Generates a unique user ID based on source and identifier.
        
        Args:
            source: The connector/source type (e.g., 'cli', 'telegram', 'web')
            identifier: A unique identifier within that source
            
        Returns:
            A unique composite user ID in the format "{source}:{identifier}"
        """
        pass
    
    @staticmethod
    def validate_id(user_id: str) -> bool:
        """
        Validates a user ID format.
        
        Args:
            user_id: The user ID to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Pattern: source:identifier where both parts contain only allowed characters
        pattern = r'^[a-zA-Z0-9_-]+:[a-zA-Z0-9_.-]+$'
        return bool(re.match(pattern, user_id))


class DefaultUserIDGenerator(UserIDGenerator):
    """
    Default implementation that handles common sources with basic validation.
    """
    def generate_id(self, source: str, identifier: str) -> str:
        """
        Generate a user ID with basic validation.
        
        Args:
            source: Source type (e.g., 'cli', 'telegram', 'web')
            identifier: Unique identifier within the source
            
        Returns:
            Composite user ID
        """
        # Validate source and identifier
        if not re.match(r'^[a-zA-Z0-9_-]+$', source):
            raise ValueError(f"Invalid source format: {source}")
        
        if not re.match(r'^[a-zA-Z0-9_.-]+$', identifier):
            raise ValueError(f"Invalid identifier format: {identifier}")
        
        return f"{source}:{identifier}"


class CLIUserIDGenerator(UserIDGenerator):
    """
    Generates user IDs for CLI users based on system information.
    """
    def generate_id(self, source: str = "cli", identifier: Optional[str] = None) -> str:
        """
        Generate a CLI-specific user ID using system username and machine information.
        
        Args:
            source: Should be 'cli' (default)
            identifier: Optional custom identifier. If None, will be auto-generated
            
        Returns:
            CLI user ID
        """
        if source != "cli":
            raise ValueError("Source must be 'cli' for CLIUserIDGenerator")
        
        if identifier is None:
            # Generate a machine-specific identifier
            username = getpass.getuser().lower()
            hostname = socket.gethostname().lower()
            platform_name = platform.system().lower()
            
            # Clean up identifier components
            username = re.sub(r'[^a-z0-9_.-]', '', username)
            hostname = re.sub(r'[^a-z0-9_.-]', '', hostname)
            platform_name = re.sub(r'[^a-z0-9_.-]', '', platform_name)
            
            # Combine components
            identifier = f"{username}_{platform_name}_{hostname[:8]}"
        
        return super().generate_id("cli", identifier)


class TelegramUserIDGenerator(UserIDGenerator):
    """
    Generates user IDs for Telegram users.
    """
    def generate_id(self, source: str = "telegram", identifier: str = None) -> str:
        """
        Generate a Telegram-specific user ID.
        
        Args:
            source: Should be 'telegram' (default)
            identifier: Telegram user ID (required)
            
        Returns:
            Telegram user ID
        """
        if source != "telegram":
            raise ValueError("Source must be 'telegram' for TelegramUserIDGenerator")
        
        if not identifier:
            raise ValueError("Telegram user ID is required")
        
        # Ensure identifier contains only digits
        if not re.match(r'^\d+$', identifier):
            raise ValueError(f"Invalid Telegram user ID: {identifier}")
        
        return super().generate_id("telegram", identifier)


class WebUserIDGenerator(UserIDGenerator):
    """
    Generates user IDs for web interface users.
    """
    def generate_id(self, source: str = "web", identifier: Optional[str] = None) -> str:
        """
        Generate a web-specific user ID.
        
        Args:
            source: Should be 'web' (default)
            identifier: Optional custom identifier. If None, will generate a UUID
            
        Returns:
            Web user ID
        """
        if source != "web":
            raise ValueError("Source must be 'web' for WebUserIDGenerator")
        
        if identifier is None:
            # Generate a UUID for anonymous web users
            identifier = str(uuid.uuid4())
        
        return super().generate_id("web", identifier)


# Factory function to get the appropriate generator
def get_user_id_generator(source_type: str) -> UserIDGenerator:
    """
    Factory function to get the appropriate UserIDGenerator based on source type.
    
    Args:
        source_type: The source type (e.g., 'cli', 'telegram', 'web')
        
    Returns:
        An appropriate UserIDGenerator instance
    """
    generators = {
        "cli": CLIUserIDGenerator(),
        "telegram": TelegramUserIDGenerator(),
        "web": WebUserIDGenerator(),
    }
    
    return generators.get(source_type, DefaultUserIDGenerator())


# Example usage
if __name__ == "__main__":
    # CLI user
    cli_generator = get_user_id_generator("cli")
    cli_user_id = cli_generator.generate_id()
    print(f"CLI User ID: {cli_user_id}")
    
    # Telegram user
    telegram_generator = get_user_id_generator("telegram")
    telegram_user_id = telegram_generator.generate_id(identifier="123456789")
    print(f"Telegram User ID: {telegram_user_id}")
    
    # Web user
    web_generator = get_user_id_generator("web")
    web_user_id = web_generator.generate_id()
    print(f"Web User ID: {web_user_id}")
    
    # Custom source
    custom_generator = get_user_id_generator("custom")
    custom_user_id = custom_generator.generate_id("custom", "user123")
    print(f"Custom User ID: {custom_user_id}")
    
    # Validate IDs
    print(f"\nValidation:")
    print(f"CLI ID valid: {UserIDGenerator.validate_id(cli_user_id)}")
    print(f"Telegram ID valid: {UserIDGenerator.validate_id(telegram_user_id)}")
    print(f"Web ID valid: {UserIDGenerator.validate_id(web_user_id)}")
    print(f"Invalid ID example: {UserIDGenerator.validate_id('invalid:user@id')}") 