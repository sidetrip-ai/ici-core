"""
RuleBasedValidator implementation for the Validator interface.

This module provides a simplified implementation of the Validator interface
that currently only checks if the input is coming from COMMAND_LINE source.
"""

import os
from typing import Dict, Any, List, Optional

from ici.core.interfaces.validator import Validator
from ici.core.exceptions import ValidationError
from ici.utils.config import get_component_config
from ici.adapters.loggers.structured_logger import StructuredLogger


class RuleBasedValidator(Validator):
    """
    Validator implementation using source checking.
    
    Currently only checks if the input is coming from COMMAND_LINE source.
    """
    
    def __init__(self, logger_name: str = "validator"):
        """
        Initialize the RuleBasedValidator.
        
        Args:
            logger_name: Name to use for the logger
        """
        self.logger = StructuredLogger(name=logger_name)
        self._is_initialized = False
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        self._allowed_sources = []
        self._rules = []
    
    async def initialize(self) -> None:
        """
        Initialize the validator with configuration parameters.
        
        Loads validation configuration from config.yaml.
        
        Returns:
            None
            
        Raises:
            ValidationError: If initialization fails
        """
        try:
            self.logger.info({
                "action": "VALIDATOR_INIT_START",
                "message": "Initializing RuleBasedValidator"
            })
            
            # Load validator configuration
            validator_config = get_component_config("validator", self._config_path)
            
            # Get allowed sources and rules
            self._allowed_sources = validator_config.get("allowed_sources", ["COMMAND_LINE"])
            self._rules = validator_config.get("rules", [])
            
            self._is_initialized = True
            
            self.logger.info({
                "action": "VALIDATOR_INIT_SUCCESS",
                "message": "RuleBasedValidator initialized successfully",
                "data": {
                    "allowed_sources": self._allowed_sources,
                    "rules": self._rules
                }
            })
            
        except Exception as e:
            self.logger.error({
                "action": "VALIDATOR_INIT_ERROR",
                "message": f"Failed to initialize validator: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise ValidationError(f"Validator initialization failed: {str(e)}") from e
    
    async def validate(
        self,
        input: str,
        context: Dict[str, Any],
        rules: List[Dict[str, Any]],
        failure_reasons: Optional[List[str]] = None
    ) -> bool:
        """
        Validates the input based on configured rules and context.
        
        Args:
            input: The user input to validate
            context: Runtime data for rule evaluation (e.g., user_id, timestamp, source)
            rules: List of validation rule dictionaries
            failure_reasons: Optional list to populate with reasons for validation failure
            
        Returns:
            bool: True if input passes all rules, False otherwise
            
        Raises:
            ValidationError: If the validation process itself fails
        """
        if not self._is_initialized:
            raise ValidationError("Validator not initialized. Call initialize() first.")
        
        # Use empty list if None provided for failure reasons
        if failure_reasons is None:
            failure_reasons = []
        
        try:
            # Get source from context
            source = context.get("source", "")
            
            # Check if source is allowed
            if source not in self._allowed_sources:
                failure_reasons.append(f"Input source '{source}' is not allowed. Allowed sources: {self._allowed_sources}")
                self.logger.info({
                    "action": "VALIDATOR_FAILED",
                    "message": "Input source validation failed",
                    "data": {"source": source, "allowed_sources": self._allowed_sources}
                })
                return False
            
            # Apply configured rules
            for rule in self._rules:
                rule_type = rule.get("type")
                
                if rule_type == "source":
                    allowed_sources = rule.get("allowed", [])
                    if source not in allowed_sources:
                        failure_reasons.append(f"Source '{source}' not in allowed sources: {allowed_sources}")
                        return False
                
                elif rule_type == "length":
                    min_len = rule.get("min", 0)
                    max_len = rule.get("max", float("inf"))
                    input_len = len(input)
                    
                    if input_len < min_len or input_len > max_len:
                        failure_reasons.append(f"Input length {input_len} not within allowed range [{min_len}, {max_len}]")
                        return False
            
            # All rules passed
            self.logger.debug({
                "action": "VALIDATOR_SUCCESS",
                "message": "Input validation successful",
                "data": {"source": source}
            })
            return True
            
        except Exception as e:
            error_msg = f"Validation process failed: {str(e)}"
            failure_reasons.append(error_msg)
            
            self.logger.error({
                "action": "VALIDATOR_ERROR",
                "message": error_msg,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            
            raise ValidationError(error_msg) from e
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Check if the validator is properly configured and functioning.
        
        Returns:
            Dict[str, Any]: Health status information
            
        Raises:
            ValidationError: If the health check itself fails
        """
        health_result = {
            "healthy": False,
            "message": "Validator health check failed",
            "details": {"initialized": self._is_initialized}
        }
        
        if not self._is_initialized:
            health_result["message"] = "Validator not initialized"
            return health_result
        
        try:
            # Test validation with valid source
            test_context = {"source": "COMMAND_LINE"}
            failure_reasons = []
            
            # Test valid source
            valid_test = await self.validate("test input", test_context, [], failure_reasons)
            
            # Test invalid source
            failure_reasons.clear()
            invalid_test = not await self.validate("test input", {"source": "WEB"}, [], failure_reasons)
            
            health_result["healthy"] = valid_test and invalid_test
            health_result["message"] = "Validator is healthy" if health_result["healthy"] else "Validator test failed"
            health_result["details"].update({
                "valid_test_passed": valid_test,
                "invalid_test_passed": invalid_test
            })
            
            return health_result
            
        except Exception as e:
            health_result["message"] = f"Validator health check failed: {str(e)}"
            health_result["details"]["error"] = str(e)
            health_result["details"]["error_type"] = type(e).__name__
            
            self.logger.error({
                "action": "VALIDATOR_HEALTHCHECK_ERROR",
                "message": f"Health check failed: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            
            return health_result 