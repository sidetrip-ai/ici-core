from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class Validator(ABC):
    """
    Interface for components that ensure user input adheres to security and compliance rules.

    The Validator enforces security constraints on user input, providing a critical security
    layer before any query processing occurs.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the validator with configuration parameters.
        
        This method should be called after the validator instance is created,
        before any other methods are used. Configuration should be loaded from
        a central configuration source (e.g., config.yaml).
        
        Returns:
            None
        
        Raises:
            Exception: If initialization fails for any reason.
        """
        pass

    @abstractmethod
    async def validate(
        self,
        input: str,
        context: Dict[str, Any],
        rules: List[Dict[str, Any]],
        failure_reasons: Optional[List[str]] = None,
    ) -> bool:
        """
        Validates the input based on provided rules and context.

        Rules are dynamically supplied as structured dictionaries for maximum flexibility:
        - Keyword filtering: {'type': 'keyword', 'forbidden': ['delete', 'drop']}
        - Time restrictions: {'type': 'time', 'allowed_hours': [8, 18]}
        - User permissions: {'type': 'permission', 'required_level': 'admin'}
        - Content length: {'type': 'length', 'max': 1000, 'min': 5}
        - Pattern matching: {'type': 'regex', 'pattern': '^[a-zA-Z0-9\\s]+$'}

        Args:
            input: The user input to validate
            context: Runtime data for rule evaluation (e.g., user_id, timestamp)
            rules: List of validation rule dictionaries
            failure_reasons: Optional list to populate with reasons for validation failure

        Returns:
            bool: True if input passes all rules, False otherwise

        Raises:
            ValidationError: If the validation process itself fails
        """
        pass

    @abstractmethod
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Checks if the validator is properly configured and functioning.

        Returns:
            Dict[str, Any]: A dictionary containing health status information:
                {
                    'healthy': bool,  # Whether the validator is functioning properly
                    'message': str,   # Optional message providing more details
                    'details': dict   # Optional additional details about the health check
                }

        Raises:
            ValidationError: If the health check itself encounters an error
        """
        pass
