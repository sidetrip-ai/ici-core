"""
BasicPromptBuilder implementation for the PromptBuilder interface.

This module provides a minimal implementation of the PromptBuilder interface
that combines documents and user input to create prompts for language models.
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

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
        
        # Default templates for main prompt
        self._template = """
# Retrieval-Augmented Response Instructions

## How to Understand This Prompt
{understanding_instructions}

## How to Read Context Messages
{reading_instructions}

## Message Direction Guidelines
{direction_instructions}

## Relevant Context
{context}

## Question
{question}
"""
        self._fallback_template = "Answer based on general knowledge: {question}"
        self._error_template = "Unable to process: {error}"
        
        # Default templates for instruction sections
        self._understanding_instructions = """
This prompt contains contextual information followed by a question. Your task is to answer the question based on the provided context. The context includes messages from various sources, structured by conversations and participants.
"""
        
        self._reading_instructions = """
Each message follows this format:
- **Source**: The origin of the message (chat group, conversation)
- **Author**: Who wrote the message
- **Timestamp**: When the message was sent
- **Previous Message ID**: Reference to the message that came before (if available)
- **Next Message ID**: Reference to the message that follows (if available)
- **Content**: The actual message text

Messages are grouped under headings showing their Message ID for clarity.
When a message shows a Previous/Next Message ID that isn't included in the context, it indicates parts of the conversation are not shown.
"""
        
        self._direction_instructions = """
Pay close attention to message recipients and authorship:
- Each message will be under correct conversation ID or chat name. It can happen that when I'm chatting with a friend via DM, the conversation name or ID is my friend name and the author is also my friend. Ensure we are not mixing up conversations and authors.
- Messages with author "Me" are written by me, the current user asking the question
- Messages with any other author are written by someone else
- Content may include tags like "@username" or "@userId" referencing specific users
- All of these terms refer to me, the current user: {user_reference_terms}
- If a message has tags that don't match any of these terms, the message is directed to someone else
- Use message metadata and content to determine the conversation flow and direction
"""
        
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
            
            # Initialize instruction templates
            instruction_config = prompt_builder_config.get("instructions", {})
            self._understanding_instructions = instruction_config.get(
                "understanding", 
                self._understanding_instructions
            )
            self._reading_instructions = instruction_config.get(
                "reading", 
                self._reading_instructions
            )
            self._direction_instructions = instruction_config.get(
                "direction", 
                self._direction_instructions
            )
            
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
    
    def _get_timestamp_value(self, timestamp):
        """Convert timestamp to comparable value for sorting"""
        if not timestamp:
            return 0
        
        if isinstance(timestamp, (int, float)):
            return timestamp
        
        try:
            if str(timestamp).isdigit():
                return int(timestamp)
            
            # Try to parse ISO format if string
            from datetime import datetime
            return datetime.fromisoformat(timestamp).timestamp()
        except:
            return 0

    def _format_timestamp(self, timestamp):
        """Format timestamp for display"""
        if not timestamp:
            return "*No timestamp*"
        
        try:
            if str(timestamp).isdigit():
                # Detect if timestamp is in seconds or milliseconds
                # Timestamps in seconds typically have 10 digits, milliseconds have 13
                ts = int(timestamp)
                if len(str(ts)) <= 10:  # Seconds
                    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                else:  # Milliseconds
                    return datetime.fromtimestamp(ts/1000, tz=timezone.utc).isoformat()
            return timestamp
        except:
            return str(timestamp)
    
    def _format_timestamp_by_source(self, timestamp, source_name):
        """Format timestamp based on the source type"""
        try:
            if str(timestamp).isdigit():
                ts = int(timestamp)
                if source_name.lower() == "telegram":
                    # Telegram uses seconds
                    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                else:
                    # WhatsApp and others use milliseconds
                    return datetime.fromtimestamp(ts/1000, tz=timezone.utc).isoformat()
            return timestamp
        except:
            return str(timestamp)
    
    def _log_message_id_extraction(self, source_name, original_ids, extracted_id, id_type):
        """Log details about message ID extraction for debugging purposes"""
        self.logger.debug({
            "action": "PROMPT_BUILDER_MESSAGE_ID_EXTRACTION",
            "message": f"Extracted {id_type} ID from {source_name}",
            "data": {
                "source": source_name,
                f"original_{id_type}_ids": original_ids,
                f"extracted_{id_type}_id": extracted_id
            }
        })
    
    def _extract_metadata_by_source(self, metadata, source_name):
        """Extract and normalize metadata based on source"""
        result = {}
        
        # Get author based on source type
        if source_name.lower() == "telegram":
            result["author"] = metadata.get("sender_name") or metadata.get("from_name") or "*Unknown Author*"
        elif source_name.lower() == "whatsapp":
            result["author"] = metadata.get("author") or metadata.get("sender") or metadata.get("from") or "*Unknown Author*"
        else:  # Generic fallback
            result["author"] = (
                metadata.get("author") or 
                metadata.get("sender_name") or 
                metadata.get("sender") or 
                metadata.get("from") or 
                metadata.get("from_name") or
                "*Unknown Author*"
            )
        
        # Handle timestamp formats
        timestamp = metadata.get("timestamp") or metadata.get("date") or metadata.get("time")
        if timestamp:
            result["timestamp"] = self._format_timestamp_by_source(timestamp, source_name)
        else:
            result["timestamp"] = "*No timestamp*"
        
        # Special handling for Telegram message IDs
        if source_name.lower() == "telegram":
            # Handle previous_message_ids as a comma-separated list
            prev_ids_str = metadata.get("previous_message_ids")
            if prev_ids_str and isinstance(prev_ids_str, str):
                try:
                    prev_ids = [id.strip() for id in prev_ids_str.split(',')]
                    if prev_ids and self._is_valid_message_id(prev_ids[-1], source_name):
                        # Use the last element (most recent previous message)
                        result["previous_message_id"] = prev_ids[-1]
                        self._log_message_id_extraction(source_name, prev_ids_str, result["previous_message_id"], "previous")
                except Exception as e:
                    self.logger.warning({
                        "action": "PROMPT_BUILDER_PARSE_ERROR",
                        "message": f"Error parsing Telegram previous_message_ids: {str(e)}",
                        "data": {"prev_ids_str": prev_ids_str}
                    })
            
            # Handle next_message_ids as a comma-separated list
            next_ids_str = metadata.get("next_message_ids")
            if next_ids_str and isinstance(next_ids_str, str):
                try:
                    next_ids = [id.strip() for id in next_ids_str.split(',')]
                    if next_ids and self._is_valid_message_id(next_ids[0], source_name):
                        # Use the first element (earliest next message)
                        result["next_message_id"] = next_ids[0]
                        self._log_message_id_extraction(source_name, next_ids_str, result["next_message_id"], "next")
                except Exception as e:
                    self.logger.warning({
                        "action": "PROMPT_BUILDER_PARSE_ERROR",
                        "message": f"Error parsing Telegram next_message_ids: {str(e)}",
                        "data": {"next_ids_str": next_ids_str}
                    })
        
        # Special handling for WhatsApp message IDs
        elif source_name.lower() == "whatsapp":
            # Handle previous_message_ids as a comma-separated list
            prev_ids_str = metadata.get("previous_message_ids")
            if prev_ids_str and isinstance(prev_ids_str, str):
                try:
                    prev_ids = [id.strip() for id in prev_ids_str.split(',')]
                    if prev_ids and self._is_valid_message_id(prev_ids[-1], source_name):
                        # Use the last element (most recent previous message)
                        result["previous_message_id"] = prev_ids[-1]
                        self._log_message_id_extraction(source_name, prev_ids_str, result["previous_message_id"], "previous")
                except Exception as e:
                    self.logger.warning({
                        "action": "PROMPT_BUILDER_PARSE_ERROR",
                        "message": f"Error parsing WhatsApp previous_message_ids: {str(e)}",
                        "data": {"prev_ids_str": prev_ids_str}
                    })
            
            # Handle next_message_ids as a comma-separated list
            next_ids_str = metadata.get("next_message_ids")
            if next_ids_str and isinstance(next_ids_str, str):
                try:
                    next_ids = [id.strip() for id in next_ids_str.split(',')]
                    if next_ids and self._is_valid_message_id(next_ids[0], source_name):
                        # Use the first element (earliest next message)
                        result["next_message_id"] = next_ids[0]
                        self._log_message_id_extraction(source_name, next_ids_str, result["next_message_id"], "next")
                except Exception as e:
                    self.logger.warning({
                        "action": "PROMPT_BUILDER_PARSE_ERROR",
                        "message": f"Error parsing WhatsApp next_message_ids: {str(e)}",
                        "data": {"next_ids_str": next_ids_str}
                    })
                    
        else:
            # Standard handling for other sources
            prev_id = (
                metadata.get("previous_message_id") or 
                metadata.get("previous_message_ids") or 
                metadata.get("prev_message_id") or
                metadata.get("prev_msg_id")
            )
            
            next_id = (
                metadata.get("next_message_id") or 
                metadata.get("next_message_ids") or
                metadata.get("next_msg_id")
            )
            
            # Validate IDs before using them
            if self._is_valid_message_id(prev_id, source_name):
                result["previous_message_id"] = prev_id
                
            if self._is_valid_message_id(next_id, source_name):
                result["next_message_id"] = next_id
        
        # Handle message ID with support for variations
        result["message_id"] = (
            metadata.get("message_id") or 
            metadata.get("message_ids") or 
            metadata.get("msg_id") or
            metadata.get("id")
        )
        
        # Group/chat name handling
        result["group"] = (
            metadata.get("group") or 
            metadata.get("chat_name") or 
            metadata.get("group_name") or
            metadata.get("channel_name")
        )
        
        # Recipient handling
        result["recipient"] = (
            metadata.get("recipient") or 
            metadata.get("to") or 
            metadata.get("to_name")
        )
        
        # Conversation ID handling
        result["conversation_id"] = (
            metadata.get("conversation_id") or 
            metadata.get("chat_id") or 
            metadata.get("thread_id")
        )
        
        # Include any additional metadata that might be useful
        for field in ["source", "url", "file_name", "location", "language"]:
            if field in metadata:
                result[field] = metadata[field]
        
        return result

    def _get_conversation_name(self, conversation_id, docs):
        """Derive a meaningful conversation name from metadata"""
        if not docs:
            return f"Conversation {conversation_id}"
        
        # Try to get name from first document's metadata
        first_doc = docs[0]
        metadata = first_doc.get("metadata", {})
        
        if "conversation_name" in metadata:
            return metadata["conversation_name"]
        if "group" in metadata:
            return metadata["group"]
        if "chat_name" in metadata:
            return metadata["chat_name"]
        
        return f"Conversation {conversation_id}"

    def _is_valid_message_id(self, message_id, source_name):
        """
        Validate a message ID based on the source type.
        
        Returns:
            bool: True if the message ID is valid, False otherwise
        """
        if not message_id:
            return False
            
        if message_id == "null":
            return False
            
        # For WhatsApp, IDs can start with "false_" or "true_"
        if source_name.lower() == "whatsapp":
            return True
            
        # For other sources, check if the ID is just the string "false"
        if message_id.lower() == "false":
            return False
            
        return True
        
    def _has_earlier_messages(self, first_doc, message_id_map):
        """Check if there are earlier messages not included in the context"""
        if not first_doc:
            return False
            
        metadata = first_doc.get("metadata", {})
        source_name = metadata.get("source", "unknown")
        
        # Extract normalized metadata
        norm_metadata = self._extract_metadata_by_source(metadata, source_name)
        
        # If the message explicitly references a previous message
        prev_message_id = norm_metadata.get("previous_message_id")
        if self._is_valid_message_id(prev_message_id, source_name) and prev_message_id not in message_id_map:
            return True
        
        # Look for reply indicators in the first message
        content = first_doc.get("text", "")
        if content and (content.startswith("Re:") or "replied to" in content):
            return True
        
        return False

    def _has_later_messages(self, last_doc, message_id_map):
        """Check if there are later messages not included in the context"""
        if not last_doc:
            return False
            
        metadata = last_doc.get("metadata", {})
        source_name = metadata.get("source", "unknown")
        
        # Extract normalized metadata
        norm_metadata = self._extract_metadata_by_source(metadata, source_name)
        
        # If the message explicitly references a next message
        next_message_id = norm_metadata.get("next_message_id")
        if self._is_valid_message_id(next_message_id, source_name) and next_message_id not in message_id_map:
            return True
        
        return False
        
    def _has_gap_between_messages(self, prev_doc, curr_doc, message_id_map):
        """Detect if there's a gap between messages based on next/previous references"""
        prev_metadata = prev_doc.get("metadata", {})
        curr_metadata = curr_doc.get("metadata", {})
        source_name = prev_metadata.get("source", "unknown")
        
        # Extract normalized metadata for better comparison
        prev_norm = self._extract_metadata_by_source(prev_metadata, source_name)
        curr_norm = self._extract_metadata_by_source(curr_metadata, source_name)
        
        # Get the normalized message IDs
        prev_next_id = prev_norm.get("next_message_id")
        curr_prev_id = curr_norm.get("previous_message_id")
        curr_msg_id = curr_norm.get("message_id")
        prev_msg_id = prev_norm.get("message_id")
        
        # If previous message references a next that isn't our current message
        if (self._is_valid_message_id(prev_next_id, source_name) and 
            prev_next_id != curr_msg_id and 
            prev_next_id not in message_id_map):
            return True
        
        # If current message references a previous that isn't our previous message
        if (self._is_valid_message_id(curr_prev_id, source_name) and 
            curr_prev_id != prev_msg_id and 
            curr_prev_id not in message_id_map):
            return True
        
        # Check timestamp gap as a fallback
        prev_timestamp = self._get_timestamp_value(prev_metadata.get("timestamp", 0))
        curr_timestamp = self._get_timestamp_value(curr_metadata.get("timestamp", 0))
        
        # If messages are more than 5 minutes apart (configurable threshold)
        if prev_timestamp and curr_timestamp and (curr_timestamp - prev_timestamp) > (5 * 60):
            return True
        
        return False

    def _format_context_markdown(self, sources):
        """Format context using Markdown structure"""
        context_parts = []
        
        # Process each source with its documents
        for source_idx, (source_name, source_docs) in enumerate(sources.items()):
            context_parts.append(f"### Source: {source_name}")
            
            # Group by conversation ID if available
            conversations = {}
            for doc in source_docs:
                metadata = doc.get("metadata", {})
                conversation_id = metadata.get("conversation_id", "default_conversation")
                
                if conversation_id not in conversations:
                    conversations[conversation_id] = []
                
                conversations[conversation_id].append(doc)
            
            # Process each conversation
            for conv_idx, (conversation_id, conv_docs) in enumerate(conversations.items()):
                # Create a map of message IDs for quick lookup
                message_id_map = {}
                for doc in conv_docs:
                    metadata = doc.get("metadata", {})
                    # Check both singular and plural message_id fields
                    if "message_id" in metadata:
                        message_id_map[metadata["message_id"]] = doc
                    elif "message_ids" in metadata:
                        message_id_map[metadata["message_ids"]] = doc
                
                # Sort documents by timestamp
                sorted_docs = sorted(conv_docs, 
                                    key=lambda x: self._get_timestamp_value(x.get("metadata", {}).get("timestamp", 0)),
                                    reverse=False)
                
                conv_name = self._get_conversation_name(conversation_id, sorted_docs)
                context_parts.append(f"\n#### Conversation: {conv_name}")
                
                # Check if we have partial conversation at the beginning
                has_earlier_messages = self._has_earlier_messages(sorted_docs[0], message_id_map) if sorted_docs else False
                if has_earlier_messages:
                    context_parts.append("*Note: This conversation has earlier messages not shown here*")
                
                # Add each message with its metadata
                for i, doc in enumerate(sorted_docs):
                    # Check for gaps between consecutive messages in our sorted list
                    if i > 0:
                        prev_doc = sorted_docs[i-1]
                        if self._has_gap_between_messages(prev_doc, doc, message_id_map):
                            context_parts.append("\n*Some messages between these timestamps are not included*\n")
                    
                    # Get original metadata
                    original_metadata = doc.get("metadata", {})
                    
                    # Extract and normalize metadata based on source
                    normalized_metadata = self._extract_metadata_by_source(original_metadata, source_name)
                    
                    # Get message ID from normalized metadata or generate one
                    message_id = normalized_metadata.get("message_id", f"{conversation_id}_{i+1}")
                    
                    # Format document content with normalized metadata
                    author = normalized_metadata.get("author")
                    timestamp = normalized_metadata.get("timestamp")
                    content = doc.get("text", "")
                    
                    # Create message block with consistent formatting
                    context_parts.append(f"#### Message ID: {message_id}")
                    context_parts.append(f"- **Source**: {conv_name}")
                    context_parts.append(f"- **Author**: {author}")
                    context_parts.append(f"- **Timestamp**: {timestamp}")
                    
                    # Add reference to previous/next messages using normalized IDs
                    prev_message_id = normalized_metadata.get("previous_message_id")
                    next_message_id = normalized_metadata.get("next_message_id")
                    
                    if prev_message_id and prev_message_id.lower() != "false" and prev_message_id != "null":
                        context_parts.append(f"- **Previous Message ID**: {prev_message_id}")
                    
                    if next_message_id and next_message_id.lower() != "false" and next_message_id != "null":
                        context_parts.append(f"- **Next Message ID**: {next_message_id}")
                    
                    # Add message content as a bullet point
                    context_parts.append(f"- **Content**: {content}")
                    
                    # No separator between messages within the same conversation
                
                # Check if we have partial conversation at the end
                has_later_messages = self._has_later_messages(sorted_docs[-1], message_id_map) if sorted_docs else False
                if has_later_messages:
                    context_parts.append("*Note: This conversation has more recent messages not shown here*")
                
                # Add separator between conversations (except for the last conversation in a source)
                if conv_idx < len(conversations) - 1:
                    context_parts.append("\n---\n")
            
            # Add separator between sources (except for the last source)
            if source_idx < len(sources) - 1:
                context_parts.append("\n\n==========\n\n")
        
        return "\n".join(context_parts)
    
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
                # Debug output - can be removed in production
                print("--------------------------------")
                print("Document: ", doc)
                print("--------------------------------")
                
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
                
                # Add to sources dict
                if source not in sources:
                    sources[source] = []
                
                sources[source].append({
                    "text": text,
                    "metadata": metadata,
                    "score": score if score is not None else 0
                })
            
            # Check for user references in the context (for logging purposes only)
            found_terms = []
            if self._user_reference_enabled and self._user_reference_terms:
                # First combine all text to look for references
                all_text = ""
                for source_docs in sources.values():
                    for doc in source_docs:
                        all_text += doc.get("text", "") + " "
                
                # Check for each term in the combined text
                for term in self._user_reference_terms:
                    if term.lower() in all_text.lower():
                        found_terms.append(term)
            
            # Create context using Markdown formatting
            context = self._format_context_markdown(sources)
            
            # Always use all configured user reference terms, not just found ones
            if self._user_reference_enabled and self._user_reference_terms:
                # Create example tags for all configured terms
                reference_examples = []
                for term in self._user_reference_terms:
                    if term.startswith('@'):
                        reference_examples.append(f'"{term}"')
                    else:
                        reference_examples.append(f'"@{term}"')
                        reference_examples.append(f'"{term}"')
                
                # Join the examples with commas
                examples_str = ", ".join(reference_examples)
                
                # Update direction instructions with all configured terms
                direction_instructions = self._direction_instructions.format(
                    user_reference_terms=examples_str
                )
                
                self.logger.info({
                    "action": "PROMPT_BUILDER_USER_REFERENCES_ADDED",
                    "message": f"Added all {len(self._user_reference_terms)} configured user reference terms to instructions",
                    "data": {
                        "configured_terms": self._user_reference_terms,
                        "found_in_context": found_terms
                    }
                })
            else:
                # No configured terms, use generic placeholder
                direction_instructions = self._direction_instructions.format(
                    user_reference_terms="@username, @userId"
                )
            
            # Build the prompt using the template
            prompt = self._template.format(
                understanding_instructions=self._understanding_instructions,
                reading_instructions=self._reading_instructions,
                direction_instructions=direction_instructions,
                context=context,
                question=input
            )
            
            self.logger.info({
                "action": "PROMPT_BUILDER_SUCCESS",
                "message": "Prompt built successfully using Markdown format",
                "data": {
                    "input_length": len(input),
                    "context_length": len(context),
                    "prompt_length": len(prompt),
                    "num_sources": len(sources),
                    "num_documents": len(documents),
                    "user_references_found": len(found_terms) > 0,
                    "user_references_configured": len(self._user_reference_terms) if self._user_reference_enabled else 0
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
            test_documents = [{
                "text": "test document",
                "metadata": {
                    "author": "Test User",
                    "timestamp": int(datetime.now().timestamp() * 1000),
                    "message_id": "test_1",
                    "conversation_id": "test_convo"
                }
            }]
            test_prompt = await self.build_prompt(test_input, test_documents)
            
            # Test fallback
            test_fallback = await self.build_prompt(test_input, [])
            
            health_result["healthy"] = True
            health_result["message"] = "Prompt builder is healthy"
            health_result["details"].update({
                "markdown_formatting": "enabled",
                "instruction_sections": ["understanding", "reading", "direction"],
                "template_format": "hierarchical markdown",
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