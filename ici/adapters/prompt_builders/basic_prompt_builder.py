"""
BasicPromptBuilder implementation for the PromptBuilder interface.

This module provides a minimal implementation of the PromptBuilder interface
that combines documents and user input to create prompts for language models.
"""

import os
from typing import List, Dict, Any, Optional

from ici.core.interfaces.prompt_builder import PromptBuilder
from ici.core.exceptions import PromptBuilderError
from ici.utils.config import get_component_config
from ici.adapters.loggers.structured_logger import StructuredLogger


class BasicPromptBuilder(PromptBuilder):
    """
    A minimal implementation of the PromptBuilder interface.
    
    Combines documents and user input using configurable templates.
    """
    
    def __init__(self, logger_name: str = "prompt_builder"):
        """
        Initialize the BasicPromptBuilder.
        
        Args:
            logger_name: Name to use for the logger
        """
        self.logger = StructuredLogger(name=logger_name)
        self._is_initialized = False
        self._config_path = os.environ.get("ICI_CONFIG_PATH", "config.yaml")
        
        # Default templates
        self._template = "Context:\n{context}\n\nQuestion: {question}"
        self._fallback_template = "Answer based on general knowledge: {question}"
        self._error_template = "Unable to process: {error}"
    
    async def initialize(self) -> None:
        """
        Initialize the prompt builder with configuration parameters.
        
        Loads prompt builder configuration from config.yaml.
        
        Returns:
            None
            
        Raises:
            PromptBuilderError: If initialization fails
        """
        try:
            self.logger.info({
                "action": "PROMPT_BUILDER_INIT_START",
                "message": "Initializing BasicPromptBuilder"
            })
            
            # Load prompt builder configuration
            prompt_builder_config = get_component_config("prompt_builder", self._config_path)
            
            # Extract templates with defaults
            self._template = prompt_builder_config.get("template", self._template)
            self._fallback_template = prompt_builder_config.get("fallback_template", self._fallback_template)
            self._error_template = prompt_builder_config.get("error_template", self._error_template)
            
            self._is_initialized = True
            
            self.logger.info({
                "action": "PROMPT_BUILDER_INIT_SUCCESS",
                "message": "BasicPromptBuilder initialized successfully"
            })
            
        except Exception as e:
            self.logger.error({
                "action": "PROMPT_BUILDER_INIT_ERROR",
                "message": f"Failed to initialize prompt builder: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise PromptBuilderError(f"Prompt builder initialization failed: {str(e)}") from e
    
    async def build_prompt(
        self,
        input: str,
        documents: List[Dict[str, Any]],
        max_context_length: Optional[int] = None,
    ) -> str:
        """
        Constructs a prompt from the input and retrieved documents.

        Args:
            input: The user input/question
            documents: List of relevant documents from the vector store
            max_context_length: Optional maximum length for context section

        Returns:
            str: Complete prompt for the language model

        Raises:
            PromptBuilderError: If prompt construction fails
        """
        if not self._is_initialized:
            raise PromptBuilderError("Prompt builder not initialized. Call initialize() first.")
        
        try:
            # Handle empty or invalid input
            if not input or not isinstance(input, str):
                error_msg = f"Invalid input: {input}"
                self.logger.warning({
                    "action": "PROMPT_BUILDER_INVALID_INPUT",
                    "message": error_msg
                })
                return self._error_template.format(error=error_msg)
            
            # Handle no documents case
            if not documents:
                self.logger.info({
                    "action": "PROMPT_BUILDER_NO_DOCUMENTS",
                    "message": "No documents provided, using fallback template"
                })
                return self._fallback_template.format(question=input)
            
            # Create context from documents
            context_parts = []
            for doc in documents:
                if "text" in doc:
                    context_parts.append(doc["text"])
                elif "content" in doc:
                    context_parts.append(doc["content"])
            
            # Handle case where documents don't contain text/content
            if not context_parts:
                self.logger.warning({
                    "action": "PROMPT_BUILDER_EMPTY_DOCUMENTS",
                    "message": "Documents provided don't contain valid text/content"
                })
                return self._fallback_template.format(question=input)
            
            context = "\n\n".join(context_parts)
            
            # Apply truncation if max_context_length is specified
            if max_context_length and len(context) > max_context_length:
                self.logger.info({
                    "action": "PROMPT_BUILDER_TRUNCATE",
                    "message": f"Truncating context to {max_context_length} characters",
                    "data": {"original_length": len(context), "max_length": max_context_length}
                })
                context = context[:max_context_length]
            
            # Build final prompt
            prompt = self._template.format(context=context, question=input)
            
            self.logger.debug({
                "action": "PROMPT_BUILDER_SUCCESS",
                "message": "Prompt built successfully",
                "data": {
                    "documents_count": len(documents),
                    "context_length": len(context),
                    "prompt_length": len(prompt)
                }
            })
            
            return prompt
            
        except Exception as e:
            error_msg = f"Failed to build prompt: {str(e)}"
            
            self.logger.error({
                "action": "PROMPT_BUILDER_ERROR",
                "message": error_msg,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            
            raise PromptBuilderError(error_msg) from e
    
    async def set_template(self, template: str) -> None:
        """
        Sets a custom template for the prompt builder.

        Args:
            template: The template string with {context} and {question} placeholders

        Raises:
            PromptBuilderError: If the template is invalid
        """
        if not self._is_initialized:
            raise PromptBuilderError("Prompt builder not initialized. Call initialize() first.")
        
        try:
            # Basic validation
            if not isinstance(template, str):
                raise ValueError("Template must be a string")
            
            if "{context}" not in template:
                raise ValueError("Template must contain {context} placeholder")
                
            if "{question}" not in template:
                raise ValueError("Template must contain {question} placeholder")
            
            self._template = template
            
            self.logger.info({
                "action": "PROMPT_BUILDER_SET_TEMPLATE",
                "message": "Template updated successfully"
            })
            
        except Exception as e:
            error_msg = f"Failed to set template: {str(e)}"
            
            self.logger.error({
                "action": "PROMPT_BUILDER_SET_TEMPLATE_ERROR",
                "message": error_msg,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            
            raise PromptBuilderError(error_msg) from e
    
    def set_fallback_template(self, template: str) -> None:
        """
        Sets a custom fallback template for when no documents are available.

        Args:
            template: The fallback template string with {question} placeholder

        Raises:
            PromptBuilderError: If the template is invalid
        """
        if not self._is_initialized:
            raise PromptBuilderError("Prompt builder not initialized. Call initialize() first.")
        
        try:
            # Basic validation
            if not isinstance(template, str):
                raise ValueError("Fallback template must be a string")
                
            if "{question}" not in template:
                raise ValueError("Fallback template must contain {question} placeholder")
            
            self._fallback_template = template
            
            self.logger.info({
                "action": "PROMPT_BUILDER_SET_FALLBACK_TEMPLATE",
                "message": "Fallback template updated successfully"
            })
            
        except Exception as e:
            error_msg = f"Failed to set fallback template: {str(e)}"
            
            self.logger.error({
                "action": "PROMPT_BUILDER_SET_FALLBACK_TEMPLATE_ERROR",
                "message": error_msg,
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            
            raise PromptBuilderError(error_msg) from e
    
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Checks if the prompt builder is properly configured and functioning.

        Returns:
            Dict[str, Any]: Health status information
            
        Raises:
            PromptBuilderError: If the health check itself fails
        """
        health_result = {
            "healthy": False,
            "message": "Prompt builder health check failed",
            "details": {"initialized": self._is_initialized}
        }
        
        if not self._is_initialized:
            health_result["message"] = "Prompt builder not initialized"
            return health_result
        
        try:
            # Test prompt building
            test_input = "test question"
            test_documents = [{"text": "test document"}]
            test_prompt = await self.build_prompt(test_input, test_documents)
            
            # Test fallback
            test_fallback = await self.build_prompt(test_input, [])
            
            health_result["healthy"] = True
            health_result["message"] = "Prompt builder is healthy"
            health_result["details"].update({
                "template": self._template,
                "fallback_template": self._fallback_template,
                "error_template": self._error_template,
                "test_prompt_success": bool(test_prompt),
                "test_fallback_success": bool(test_fallback)
            })
            
            return health_result
            
        except Exception as e:
            health_result["message"] = f"Prompt builder health check failed: {str(e)}"
            health_result["details"]["error"] = str(e)
            health_result["details"]["error_type"] = type(e).__name__
            
            self.logger.error({
                "action": "PROMPT_BUILDER_HEALTHCHECK_ERROR",
                "message": f"Health check failed: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            
            return health_result 