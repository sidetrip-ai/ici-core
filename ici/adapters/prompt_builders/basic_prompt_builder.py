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
        
        # User reference settings with defaults
        self._user_reference_enabled = False
        self._user_reference_terms = []
        self._user_reference_template = "Note: In the context, the terms {terms} refer to you, the user."
        self._reference_patterns = []
    
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
            
            # Load user reference configuration
            user_ref_config = prompt_builder_config.get("user_reference", {})
            self._user_reference_enabled = user_ref_config.get("enabled", False)
            self._user_reference_terms = user_ref_config.get("terms", [])
            self._user_reference_template = user_ref_config.get(
                "template", 
                "Note: In the context, the terms {terms} refer to you, the user."
            )
            
            if self._user_reference_enabled and self._user_reference_terms:
                # Compile regex patterns for efficient matching
                import re
                self._reference_patterns = [
                    re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE) 
                    for term in self._user_reference_terms
                ]
                
                self.logger.info({
                    "action": "PROMPT_BUILDER_USER_REFERENCES_LOADED",
                    "message": f"Loaded {len(self._user_reference_terms)} user reference terms",
                    "data": {
                        "reference_terms": self._user_reference_terms,
                        "enabled": self._user_reference_enabled
                    }
                })
            
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
        Constructs a prompt from the input and retrieved documents with enhanced organization.

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
            
            # Group documents by source for better organization
            sources = {}
            for doc in documents:
                # Get text content from doc
                text = None
                if "text" in doc:
                    text = doc["text"]
                elif "content" in doc:
                    text = doc["content"]
                else:
                    continue  # Skip if no text content
                
                # Get metadata
                metadata = doc.get("metadata", {})
                source = metadata.get("source", "Unknown Source")
                
                # Get relevance information
                score = doc.get("score", None)
                rrf_score = doc.get("rrf_score", None)
                
                # Add source annotation with relevance if available
                score_info = ""
                if score is not None:
                    score_info = f" (Relevance: {score:.2f})"
                
                # Get creation time if available
                timestamp = metadata.get("creation_time", metadata.get("timestamp", ""))
                time_info = f" | {timestamp}" if timestamp else ""
                
                # Format source header
                source_header = f"--- {source}{score_info}{time_info} ---"
                
                # Add to sources dict
                if source not in sources:
                    sources[source] = []
                
                sources[source].append({
                    "header": source_header,
                    "text": text,
                    "score": score if score is not None else 0
                })
            
            # Build context from organized documents
            context_parts = []
            
            # Include a summary of sources first
            if len(sources) > 1:
                source_list = ", ".join(sources.keys())
                context_parts.append(f"Information from multiple sources: {source_list}\n")
            
            # Sort sources by highest scoring document within each source
            sorted_sources = sorted(
                sources.keys(),
                key=lambda s: max([doc.get("score", 0) for doc in sources[s]]),
                reverse=True
            )
            
            # Add documents from each source, organized by source
            for source in sorted_sources:
                source_docs = sources[source]
                
                # Sort documents within source by score
                source_docs = sorted(source_docs, key=lambda x: x.get("score", 0), reverse=True)
                
                # Add each document with its header
                for doc in source_docs:
                    context_parts.append(f"{doc['header']}\n{doc['text']}")
            
            # Combine context parts
            context = "\n\n".join(context_parts)
            
            # Check for user references in the context
            found_terms = []
            if self._user_reference_enabled and self._user_reference_terms and self._reference_patterns:
                for pattern, term in zip(self._reference_patterns, self._user_reference_terms):
                    if pattern.search(context):
                        found_terms.append(term)
            
            # Check if we need to truncate
            if max_context_length and len(context) > max_context_length:
                self.logger.warning({
                    "action": "PROMPT_BUILDER_TRUNCATE",
                    "message": f"Truncating context from {len(context)} to {max_context_length} characters"
                })
                context = context[:max_context_length] + "...[truncated due to length]"
            
            # Build the prompt using the template
            prompt = self._template.format(context=context, question=input)
            
            # Add user reference information if references were found
            if found_terms:
                terms_str = ", ".join([f'"{term}"' for term in found_terms])
                reference_note = self._user_reference_template.format(terms=terms_str)
                
                # Add the reference note at the beginning of the prompt
                prompt = f"{reference_note}\n\n{prompt}"
                
                self.logger.info({
                    "action": "PROMPT_BUILDER_USER_REFERENCES_ADDED",
                    "message": f"Added user reference note for {len(found_terms)} terms",
                    "data": {"found_terms": found_terms}
                })
            
            self.logger.info({
                "action": "PROMPT_BUILDER_SUCCESS",
                "message": "Prompt built successfully",
                "data": {
                    "input_length": len(input),
                    "context_length": len(context),
                    "prompt_length": len(prompt),
                    "num_sources": len(sources),
                    "num_documents": len(documents),
                    "user_references_found": len(found_terms) > 0
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
            
            return self._error_template.format(error=error_msg)
    
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