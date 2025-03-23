"""
LangchainGenerator implementation for the Generator interface.

This module provides an implementation of the Generator interface
that uses LangChain to generate responses with support for multiple LLM providers.
"""

import os
import time
import asyncio
from typing import Dict, Any, Optional, List, Union, cast

from langchain.chains import LLMChain
from langchain.chains.conversation.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.schema.language_model import BaseLanguageModel
from langchain_openai import ChatOpenAI
from langchain_ollama import OllamaLLM
from langchain.schema.output import LLMResult, Generation

from ici.core.interfaces.generator import Generator
from ici.core.exceptions import GenerationError
from ici.utils.config import get_component_config
from ici.adapters.loggers.structured_logger import StructuredLogger


class LangchainGenerator(Generator):
    """
    A Generator implementation that uses LangChain to generate responses.
    
    Supports multiple model providers with configurable parameters and memory.
    """
    
    def __init__(self, logger_name: str = "generator"):
        """
        Initialize the LangchainGenerator.
        
        Args:
            logger_name: Name to use for the logger
        """
        self.logger = StructuredLogger(name=logger_name)
        self._is_initialized = False
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        
        # Default model and options
        self._provider = "openai"
        self._model = "gpt-4o"
        self._chain_type = "simple"
        self._default_options = {
            "temperature": 0.7,
            "max_tokens": 1024,
            "top_p": 1.0,
        }
        
        # Retry configuration
        self._max_retries = 3
        self._base_retry_delay = 1  # seconds
        
        # LangChain components - will be initialized in initialize()
        self._llm = None
        self._chain = None
        self._memory = None
        self._prompt_template = None
    
    def _get_credentials(self):
        """
        Securely fetch credentials (API keys or URLs) when needed instead of storing as instance variables.
        
        Returns:
            str: The credentials for the configured provider
            
        Raises:
            ValueError: If required credentials are not found
        """
        generator_config = get_component_config("generator", self._config_path)
        
        if self._provider == "openai":
            api_key = generator_config.get("api_key")
            if not api_key:
                api_key = os.environ.get("OPENAI_API_KEY")
                
            if not api_key:
                raise ValueError("OpenAI API key not found in config or environment")
                
            return api_key
        elif self._provider == "anthropic":
            api_key = generator_config.get("api_key")
            if not api_key:
                api_key = os.environ.get("ANTHROPIC_API_KEY")
                
            if not api_key:
                raise ValueError("Anthropic API key not found in config or environment")
                
            return api_key
        elif self._provider == "ollama":
            # For Ollama, we return the base_url instead of an API key
            base_url = generator_config.get("base_url", "http://localhost:11434")
            return base_url
        else:
            raise ValueError(f"Unsupported provider: {self._provider}")
            
    async def initialize(self) -> None:
        """
        Initialize the generator with configuration parameters.
        
        Loads generator configuration from config.yaml and sets up LangChain components.
        
        Returns:
            None
            
        Raises:
            GenerationError: If initialization fails
        """
        try:
            self.logger.info({
                "action": "GENERATOR_INIT_START",
                "message": "Initializing LangchainGenerator"
            })
            
            # Load generator configuration
            generator_config = get_component_config("generator", self._config_path)
            
            # Extract provider type
            self._provider = generator_config.get("provider", self._provider)
            
            # Get credentials to verify they exist (but don't store them)
            credentials = self._get_credentials()
            
            # Extract model with default
            self._model = generator_config.get("model", self._model)
            
            # Extract chain type
            self._chain_type = generator_config.get("chain_type", self._chain_type)
            
            # Extract default options with defaults
            config_options = generator_config.get("default_options", {})
            self._default_options.update(config_options)
            
            # Extract retry configuration
            self._max_retries = generator_config.get("max_retries", self._max_retries)
            self._base_retry_delay = generator_config.get("base_retry_delay", self._base_retry_delay)
            
            # Setup memory if configured
            memory_config = generator_config.get("memory")
            if memory_config and memory_config.get("type") == "buffer":
                k = memory_config.get("k", 5)
                self._memory = ConversationBufferMemory(k=k)
            
            # Initialize LLM based on provider
            if self._provider == "openai":
                self._llm = ChatOpenAI(
                    model_name=self._model,
                    temperature=self._default_options.get("temperature", 0.7),
                    max_tokens=self._default_options.get("max_tokens", 1024),
                    top_p=self._default_options.get("top_p", 1.0),
                    api_key=credentials  # Use API key but don't store it as instance variable
                )
            elif self._provider == "ollama":
                self._llm = OllamaLLM(
                    model=self._model,
                    base_url=credentials,  # Use base_url from credentials
                    temperature=self._default_options.get("temperature", 0.7),
                    # Add other Ollama-specific parameters as needed
                    num_predict=self._default_options.get("max_tokens", 1024),
                    top_p=self._default_options.get("top_p", 1.0),
                )
            # Add additional providers here as elif blocks
            
            # Set up prompt template
            template = "System: You are a helpful assistant.\n\nHuman: {prompt}\n\nAssistant:"
            self._prompt_template = PromptTemplate(
                input_variables=["prompt"],
                template=template
            )
            
            # Set up chain
            if self._memory:
                self._chain = LLMChain(
                    llm=self._llm,
                    prompt=self._prompt_template,
                    memory=self._memory
                )
            else:
                self._chain = LLMChain(
                    llm=self._llm,
                    prompt=self._prompt_template
                )
            
            self._is_initialized = True
            
            self.logger.info({
                "action": "GENERATOR_INIT_SUCCESS",
                "message": "LangchainGenerator initialized successfully",
                "data": {
                    "provider": self._provider, 
                    "model": self._model,
                    "chain_type": self._chain_type,
                    "has_memory": self._memory is not None
                }
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
        Generates text using LangChain based on the provided prompt.

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
            # Call LangChain with retries
            for attempt in range(self._max_retries):
                try:
                    self.logger.debug({
                        "action": "GENERATOR_API_CALL",
                        "message": f"Calling LangChain with {self._provider} model {self._model}",
                        "data": {
                            "provider": self._provider,
                            "model": self._model,
                            "options": options,
                            "attempt": attempt + 1
                        }
                    })
                    
                    # Update LLM parameters if needed
                    if options:
                        # Create new LLM instance with updated parameters
                        temp_llm = None
                        if self._provider == "openai":
                            # Get credentials securely when needed
                            credentials = self._get_credentials()
                            temp_llm = ChatOpenAI(
                                model_name=self._model,
                                temperature=options.get("temperature", self._default_options.get("temperature")),
                                max_tokens=options.get("max_tokens", self._default_options.get("max_tokens")),
                                top_p=options.get("top_p", self._default_options.get("top_p")),
                                api_key=credentials  # Use freshly retrieved credentials
                            )
                        elif self._provider == "ollama":
                            # Get credentials (base_url) securely when needed
                            credentials = self._get_credentials()
                            temp_llm = OllamaLLM(
                                model=self._model,
                                base_url=credentials,
                                temperature=options.get("temperature", self._default_options.get("temperature")),
                                num_predict=options.get("max_tokens", self._default_options.get("max_tokens")),
                                top_p=options.get("top_p", self._default_options.get("top_p")),
                            )
                        
                        # Use the temporary LLM for this request if created
                        if temp_llm:
                            chain = LLMChain(llm=temp_llm, prompt=self._prompt_template)
                            response = await chain.ainvoke({"prompt": prompt})
                        else:
                            response = await self._chain.ainvoke({"prompt": prompt})
                    else:
                        # Use the default chain
                        response = await self._chain.ainvoke({"prompt": prompt})
                    
                    # Extract the generated text
                    generated_text = self.extract_text(response)
                    
                    self.logger.info({
                        "action": "GENERATOR_SUCCESS",
                        "message": "Text generated successfully",
                        "data": {
                            "provider": self._provider,
                            "model": self._model,
                            "prompt_length": len(prompt),
                            "response_length": len(generated_text)
                        }
                    })
                    
                    return generated_text
                    
                except Exception as e:
                    # For API errors, retry if it seems transient
                    if attempt < self._max_retries - 1:
                        delay = self._base_retry_delay * (2 ** attempt)
                        
                        self.logger.warning({
                            "action": "GENERATOR_RETRY",
                            "message": f"API error, retrying in {delay} seconds",
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
                    "provider": self._provider,
                    "model": self._model,
                    "prompt_length": len(prompt)
                }
            })
            
            raise GenerationError(error_msg) from e
    
    async def set_model(self, model: str) -> None:
        """
        Sets the specific model to use for generation.

        Args:
            model: The model identifier (e.g., 'gpt-4o', 'claude-3-opus', 'llama3')

        Raises:
            GenerationError: If the model is invalid or unavailable
        """
        if not self._is_initialized:
            raise GenerationError("Generator not initialized. Call initialize() first.")
        
        try:
            # Basic validation for model name format
            if not isinstance(model, str) or not model:
                raise ValueError(f"Invalid model name: {model}")
            
            # Update model
            self._model = model
            
            # Re-initialize the LLM with the new model
            if self._provider == "openai":
                # Get credentials securely when needed
                credentials = self._get_credentials()
                self._llm = ChatOpenAI(
                    model_name=self._model,
                    temperature=self._default_options.get("temperature", 0.7),
                    max_tokens=self._default_options.get("max_tokens", 1024),
                    top_p=self._default_options.get("top_p", 1.0),
                    api_key=credentials  # Use freshly retrieved credentials
                )
            elif self._provider == "ollama":
                # Get credentials (base_url) securely when needed
                credentials = self._get_credentials()
                self._llm = OllamaLLM(
                    model=self._model,
                    base_url=credentials,
                    temperature=self._default_options.get("temperature", 0.7),
                    num_predict=self._default_options.get("max_tokens", 1024),
                    top_p=self._default_options.get("top_p", 1.0),
                )
            # Add additional providers here as elif blocks
            
            # Update the chain with the new LLM
            if self._memory:
                self._chain = LLMChain(
                    llm=self._llm,
                    prompt=self._prompt_template,
                    memory=self._memory
                )
            else:
                self._chain = LLMChain(
                    llm=self._llm,
                    prompt=self._prompt_template
                )
            
            self.logger.info({
                "action": "GENERATOR_SET_MODEL",
                "message": f"Model updated to {model}",
                "data": {"provider": self._provider, "model": model}
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
            
            # Update default options
            self._default_options.update(options)
            
            # Update the LLM with new default options
            if self._provider == "openai":
                # Get credentials securely when needed
                credentials = self._get_credentials()
                self._llm = ChatOpenAI(
                    model_name=self._model,
                    temperature=self._default_options.get("temperature", 0.7),
                    max_tokens=self._default_options.get("max_tokens", 1024),
                    top_p=self._default_options.get("top_p", 1.0),
                    api_key=credentials  # Use freshly retrieved credentials
                )
            elif self._provider == "ollama":
                # Get credentials (base_url) securely when needed
                credentials = self._get_credentials()
                self._llm = OllamaLLM(
                    model=self._model,
                    base_url=credentials,
                    temperature=self._default_options.get("temperature", 0.7),
                    num_predict=self._default_options.get("max_tokens", 1024),
                    top_p=self._default_options.get("top_p", 1.0),
                )
            # Add additional providers here as elif blocks
            
            # Update the chain with the new LLM
            if self._memory:
                self._chain = LLMChain(
                    llm=self._llm,
                    prompt=self._prompt_template,
                    memory=self._memory
                )
            else:
                self._chain = LLMChain(
                    llm=self._llm,
                    prompt=self._prompt_template
                )
            
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
        Checks if the generator is properly configured and can connect to the language model.

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
                "provider": self._provider,
                "model": self._model,
                "chain_type": self._chain_type,
                "has_memory": self._memory is not None
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
        
    def extract_text(self, response):
        if isinstance(response, str):
            return response
        elif isinstance(response, dict):
            return response.get('text', '')
        elif hasattr(response, 'content'):
            return response.content
        else:
            return str(response)