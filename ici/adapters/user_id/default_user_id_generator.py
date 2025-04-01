"""
Default implementation of a User ID generator.
"""

import uuid
import re
from typing import Dict, Any, Optional, Tuple

from ici.core.interfaces import UserIDGenerator
from ici.core.exceptions import UserIDError
from ici.adapters.loggers import StructuredLogger


class DefaultUserIDGenerator(UserIDGenerator):
    """
    Default implementation of a User ID Generator.
    
    Generates user IDs in the format: source:identifier (e.g. cli:anonymous, web:username)
    """
    
    USER_ID_PATTERN = re.compile(r'^(?P<source>[a-z]+):(?P<identifier>[a-zA-Z0-9-_.]+)$')
    DEFAULT_IDENTIFIER = "anonymous"
    
    def __init__(self):
        """Initialize the DefaultUserIDGenerator."""
        self.logger = StructuredLogger(name="user_id_generator")
        self.initialized = False
        self.source_types = {
            "cli": lambda x: x or self.DEFAULT_IDENTIFIER,
            "web": lambda x: x or f"user-{str(uuid.uuid4())[:8]}",
            "api": lambda x: x or f"api-{str(uuid.uuid4())[:8]}",
            "test": lambda x: x or "test-user",
        }
    
    async def initialize(self) -> None:
        """
        Initialize the user ID generator with configuration parameters.
        
        Raises:
            UserIDError: If initialization fails.
        """
        try:
            # In a real implementation, load config from YAML
            # For now, we use hardcoded defaults
            self.logger.info("Initialized DefaultUserIDGenerator")
            self.initialized = True
        except Exception as e:
            self.logger.error(f"Failed to initialize DefaultUserIDGenerator: {e}")
            raise UserIDError(f"Initialization failed: {e}")
    
    def _check_initialized(self) -> None:
        """Check if the generator is initialized."""
        if not self.initialized:
            raise UserIDError("UserIDGenerator not initialized. Call initialize() first.")
    
    async def generate_id(self, source: str, identifier: Optional[str] = None) -> str:
        """
        Generate a unique user ID based on the source and an optional identifier.
        
        Args:
            source: The source of the user (e.g., 'cli', 'web', 'api')
            identifier: Optional identifier for the user (e.g., username, email)
            
        Returns:
            str: A unique user ID in the format "source:identifier"
            
        Raises:
            UserIDError: If the source is invalid or ID generation fails
        """
        self._check_initialized()
        
        # Validate source
        if not source or not isinstance(source, str):
            raise UserIDError(f"Invalid source: {source}")
        
        source = source.lower()
        if source not in self.source_types:
            raise UserIDError(f"Unsupported source type: {source}. Supported types: {list(self.source_types.keys())}")
        
        try:
            # Apply source-specific transformation to identifier
            processed_identifier = self.source_types[source](identifier)
            
            # Ensure the identifier is valid
            if not processed_identifier or not isinstance(processed_identifier, str):
                raise UserIDError(f"Invalid identifier after processing: {processed_identifier}")
            
            # Remove any colons from the identifier to maintain format
            processed_identifier = processed_identifier.replace(":", "-")
            
            # Generate the user ID
            user_id = f"{source}:{processed_identifier}"
            
            self.logger.debug(f"Generated user ID: {user_id}")
            return user_id
        except Exception as e:
            if isinstance(e, UserIDError):
                raise
            raise UserIDError(f"Failed to generate user ID: {e}")
    
    async def validate_id(self, user_id: str) -> bool:
        """
        Validate the format of a user ID.
        
        Args:
            user_id: The user ID to validate
            
        Returns:
            bool: True if the user ID is valid, False otherwise
            
        Raises:
            UserIDError: If validation fails unexpectedly
        """
        self._check_initialized()
        
        if not user_id or not isinstance(user_id, str):
            return False
        
        try:
            # Check if the user ID matches the expected pattern
            match = self.USER_ID_PATTERN.match(user_id)
            if not match:
                return False
            
            # Extract and validate source
            source = match.group('source')
            if source not in self.source_types:
                return False
            
            return True
        except Exception as e:
            raise UserIDError(f"User ID validation failed: {e}")
    
    async def parse_id(self, user_id: str) -> Tuple[str, str]:
        """
        Parse a user ID into its component parts.
        
        Args:
            user_id: The user ID to parse
            
        Returns:
            Tuple[str, str]: A tuple containing (source, identifier)
            
        Raises:
            UserIDError: If the user ID is invalid or cannot be parsed
        """
        self._check_initialized()
        
        if not user_id or not isinstance(user_id, str):
            raise UserIDError(f"Invalid user ID: {user_id}")
        
        try:
            # Check if the user ID matches the expected pattern
            match = self.USER_ID_PATTERN.match(user_id)
            if not match:
                raise UserIDError(f"User ID has invalid format: {user_id}")
            
            # Extract source and identifier
            source = match.group('source')
            identifier = match.group('identifier')
            
            # Validate source
            if source not in self.source_types:
                raise UserIDError(f"Unsupported source type in user ID: {source}")
            
            return source, identifier
        except Exception as e:
            if isinstance(e, UserIDError):
                raise
            raise UserIDError(f"Failed to parse user ID: {e}")
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Check if the user ID generator is properly configured and functioning.
        
        Returns:
            Dict[str, Any]: A dictionary containing health status information
                
        Raises:
            UserIDError: If the health check itself encounters an error
        """
        try:
            details = {
                "available_sources": list(self.source_types.keys()),
                "initialized": self.initialized,
            }
            
            # Healthy if initialized
            healthy = self.initialized
            
            return {
                "healthy": healthy,
                "message": "User ID generator is healthy" if healthy else "User ID generator not initialized",
                "details": details
            }
        except Exception as e:
            raise UserIDError(f"Health check failed: {e}") 