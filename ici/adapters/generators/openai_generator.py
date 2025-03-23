"""
OpenAIGenerator implementation for the Generator interface.

This module provides an implementation of the Generator interface
that uses OpenAI's API to generate responses with models like GPT-4o.
"""

import os
import time
import asyncio
from typing import Dict, Any, Optional, List

import openai
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from ici.core.interfaces.generator import Generator
from ici.core.exceptions import GenerationError
from ici.utils.config import get_component_config
from ici.adapters.loggers.structured_logger import StructuredLogger


class OpenAIGenerator(Generator):
    """
    A Generator implementation that uses OpenAI's API to generate responses.
    
    Supports all OpenAI models including GPT-4o with configurable parameters.
    """
    
    def __init__(self, logger_name: str = "generator"):
        """
        Initialize the OpenAIGenerator.
        
        Args:
            logger_name: Name to use for the logger
        """
        self.logger = StructuredLogger(name=logger_name)
        self._is_initialized = False
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        
        # Default model and options
        self._model = "gpt-4o"
        self._default_options = {
            "temperature": 0.7,
            "max_tokens": 1024,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
        
        # Retry configuration
        self._max_retries = 3
        self._base_retry_delay = 1  # seconds
        
        # Client will be initialized in initialize()
        self._client = None
    
    async def initialize(self) -> None:
        """
        Initialize the generator with configuration parameters.
        
        Loads generator configuration from config.yaml and sets up OpenAI API client.
        
        Returns:
            None
            
        Raises:
            GenerationError: If initialization fails
        """
        try:
            self.logger.info({
                "action": "GENERATOR_INIT_START",
                "message": "Initializing OpenAIGenerator"
            })
            
            # Load generator configuration
            generator_config = get_component_config("generator", self._config_path)
            
            # Extract API key from config or environment
            api_key = generator_config.get("api_key")
            if not api_key:
                api_key = os.environ.get("OPENAI_API_KEY")
                
            if not api_key:
                raise ValueError("OpenAI API key not found in config or environment")
            
            # Extract model with default
            self._model = generator_config.get("model", self._model)
            
            # Extract default options with defaults
            config_options = generator_config.get("default_options", {})
            self._default_options.update(config_options)
            
            # Extract retry configuration
            self._max_retries = generator_config.get("max_retries", self._max_retries)
            self._base_retry_delay = generator_config.get("base_retry_delay", self._base_retry_delay)
            
            # Initialize OpenAI client
            self._client = AsyncOpenAI(api_key=api_key)
            
            self._is_initialized = True
            
            self.logger.info({
                "action": "GENERATOR_INIT_SUCCESS",
                "message": "OpenAIGenerator initialized successfully",
                "data": {"model": self._model}
            })
            
        except Exception as e:
            self.logger.error({
                "action": "GENERATOR_INIT_ERROR",
                "message": f"Failed to initialize generator: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise GenerationError(f"Generator initialization failed: {str(e)}") from e
    
    async def generate(
        self, prompt: str, generation_options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generates text using OpenAI's API based on the provided prompt.

        Args:
            prompt: The input prompt for the language model
            generation_options: Optional parameters to override defaults

        Returns:
            str: The generated text response

        Raises:
            GenerationError: If text generation fails
        """
        if not self._is_initialized:
            raise GenerationError("Generator not initialized. Call initialize() first.")
        
        # Combine default options with request-specific options
        options = self._default_options.copy()
        if generation_options:
            options.update(generation_options)
        
        try:
            # Format the message for the API
            messages = [{"role": "user", "content": prompt}]
            
            # Call OpenAI API with retries
            for attempt in range(self._max_retries):
                try:
                    self.logger.debug({
                        "action": "GENERATOR_API_CALL",
                        "message": f"Calling OpenAI API with model {self._model}",
                        "data": {
                            "model": self._model,
                            "options": options,
                            "attempt": attempt + 1
                        }
                    })
                    
                    # Call OpenAI API
                    response: ChatCompletion = await self._client.chat.completions.create(
                        model=self._model,
                        messages=messages,
                        temperature=options.get("temperature", 0.7),
                        max_tokens=options.get("max_tokens", 1024),
                        top_p=options.get("top_p", 1.0),
                        frequency_penalty=options.get("frequency_penalty", 0.0),
                        presence_penalty=options.get("presence_penalty", 0.0),
                        timeout=30  # 30 seconds timeout
                    )
                    
                    # Extract the generated text
                    generated_text = response.choices[0].message.content
                    
                    self.logger.info({
                        "action": "GENERATOR_SUCCESS",
                        "message": "Text generated successfully",
                        "data": {
                            "model": self._model,
                            "prompt_length": len(prompt),
                            "response_length": len(generated_text)
                        }
                    })
                    
                    return generated_text
                    
                except (openai.RateLimitError, openai.APITimeoutError) as e:
                    # Retry with exponential backoff for rate limits and timeouts
                    if attempt < self._max_retries - 1:
                        delay = self._base_retry_delay * (2 ** attempt)
                        
                        self.logger.warning({
                            "action": "GENERATOR_RETRY",
                            "message": f"API rate limit or timeout, retrying in {delay} seconds",
                            "data": {
                                "error": str(e),
                                "attempt": attempt + 1,
                                "max_retries": self._max_retries,
                                "delay": delay
                            }
                        })
                        
                        await asyncio.sleep(delay)
                    else:
                        # Last attempt failed, reraise
                        raise
                        
                except openai.APIError as e:
                    # For other API errors, retry if it seems transient
                    if attempt < self._max_retries - 1 and e.status_code >= 500:
                        delay = self._base_retry_delay * (2 ** attempt)
                        
                        self.logger.warning({
                            "action": "GENERATOR_RETRY",
                            "message": f"API error, retrying in {delay} seconds",
                            "data": {
                                "error": str(e),
                                "status_code": e.status_code,
                                "attempt": attempt + 1,
                                "max_retries": self._max_retries,
                                "delay": delay
                            }
                        })
                        
                        await asyncio.sleep(delay)
                    else:
                        # Non-transient error or last attempt, reraise
                        raise
            
            # This should not be reached due to the last raise, but just in case
            raise GenerationError("All retry attempts failed")
            
        except Exception as e:
            error_msg = f"Failed to generate text: {str(e)}"
            
            self.logger.error({
                "action": "GENERATOR_ERROR",
                "message": error_msg,
                "data": {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "model": self._model,
                    "prompt_length": len(prompt)
                }
            })
            
            raise GenerationError(error_msg) from e
    
    async def set_model(self, model: str) -> None:
        """
        Sets the specific OpenAI model to use for generation.

        Args:
            model: The OpenAI model identifier (e.g., 'gpt-4o', 'gpt-4', 'gpt-3.5-turbo')

        Raises:
            GenerationError: If the model is invalid or unavailable
        """
        if not self._is_initialized:
            raise GenerationError("Generator not initialized. Call initialize() first.")
        
        try:
            # Basic validation for model name format
            if not isinstance(model, str) or not model:
                raise ValueError(f"Invalid model name: {model}")
            
            # TODO: Could add model existence validation with OpenAI API when available
            
            # Update model
            self._model = model
            
            self.logger.info({
                "action": "GENERATOR_SET_MODEL",
                "message": f"Model updated to {model}",
                "data": {"model": model}
            })
            
        except Exception as e:
            error_msg = f"Failed to set model: {str(e)}"
            
            self.logger.error({
                "action": "GENERATOR_SET_MODEL_ERROR",
                "message": error_msg,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            
            raise GenerationError(error_msg) from e
    
    async def set_default_options(self, options: Dict[str, Any]) -> None:
        """
        Sets default options for all generation requests.

        Args:
            options: Dictionary of default generation parameters

        Raises:
            GenerationError: If any option is invalid
        """
        if not self._is_initialized:
            raise GenerationError("Generator not initialized. Call initialize() first.")
        
        try:
            # Basic validation
            if not isinstance(options, dict):
                raise ValueError("Options must be a dictionary")
            
            # Validate specific option values
            if "temperature" in options and not isinstance(options["temperature"], (int, float)):
                raise ValueError(f"Invalid temperature value: {options['temperature']}")
                
            if "max_tokens" in options and not isinstance(options["max_tokens"], int):
                raise ValueError(f"Invalid max_tokens value: {options['max_tokens']}")
                
            if "top_p" in options and not isinstance(options["top_p"], (int, float)):
                raise ValueError(f"Invalid top_p value: {options['top_p']}")
                
            if "frequency_penalty" in options and not isinstance(options["frequency_penalty"], (int, float)):
                raise ValueError(f"Invalid frequency_penalty value: {options['frequency_penalty']}")
                
            if "presence_penalty" in options and not isinstance(options["presence_penalty"], (int, float)):
                raise ValueError(f"Invalid presence_penalty value: {options['presence_penalty']}")
            
            # Update default options
            self._default_options.update(options)
            
            self.logger.info({
                "action": "GENERATOR_SET_OPTIONS",
                "message": "Default options updated",
                "data": {"options": self._default_options}
            })
            
        except Exception as e:
            error_msg = f"Failed to set default options: {str(e)}"
            
            self.logger.error({
                "action": "GENERATOR_SET_OPTIONS_ERROR",
                "message": error_msg,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            
            raise GenerationError(error_msg) from e
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Checks if the generator is properly configured and can connect to OpenAI API.

        Returns:
            Dict[str, Any]: Health status information
            
        Raises:
            GenerationError: If the health check itself fails
        """
        health_result = {
            "healthy": False,
            "message": "Generator health check failed",
            "details": {
                "initialized": self._is_initialized,
                "model": self._model
            }
        }
        
        if not self._is_initialized:
            health_result["message"] = "Generator not initialized"
            return health_result
        
        try:
            # Test with a simple prompt
            test_prompt = "Hello, are you working properly? Please respond with 'Yes, I am operational.'"
            test_response = await self.generate(
                test_prompt, 
                {"max_tokens": 20, "temperature": 0.0}
            )
            
            # Check if response contains expected confirmation
            contains_confirmation = "Yes" in test_response and ("operational" in test_response or "working" in test_response)
            
            health_result["healthy"] = contains_confirmation
            health_result["message"] = "Generator is healthy" if contains_confirmation else "Generator test failed"
            health_result["details"].update({
                "test_response": test_response,
                "response_success": bool(test_response),
                "contains_confirmation": contains_confirmation
            })
            
            return health_result
            
        except Exception as e:
            health_result["message"] = f"Generator health check failed: {str(e)}"
            health_result["details"]["error"] = str(e)
            health_result["details"]["error_type"] = type(e).__name__
            
            self.logger.error({
                "action": "GENERATOR_HEALTHCHECK_ERROR",
                "message": f"Health check failed: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            
            return health_result 