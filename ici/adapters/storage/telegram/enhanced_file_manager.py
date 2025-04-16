"""
Enhanced file manager for Telegram conversation storage.

This module extends the basic FileManager with additional functionality like
automated backups, file locking, and improved file operations.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional, Tuple, Iterator
from datetime import datetime, timedelta

from ici.adapters.storage.telegram.file_manager import FileManager
from ici.adapters.loggers import StructuredLogger
from ici.adapters.storage.telegram.serializer import ConversationSerializer
from ici.utils.utils import (
    FileSystemLock,
    BackupManager,
    get_backup_frequency,
    atomic_write,
    batch_process_files
)
from ici.utils.conversation_utils import (
    is_personal_chat,
    is_bot_chat,
    is_private_group,
    add_conversation_type_metadata,
    filter_conversations,
    get_fetch_mode_from_config
)


class EnhancedFileManager(FileManager):
    """
    Enhanced file manager with additional functionality for Telegram conversation storage.
    
    Adds features like:
    - Automatic backups based on configurable frequency
    - File locking for concurrent access
    - Parallel file processing
    - Export and import capabilities
    """
    
    def __init__(self, 
                 storage_dir: Optional[str] = None, 
                 serializer: Optional[ConversationSerializer] = None,
                 logger: Optional[StructuredLogger] = None,
                 backup_enabled: bool = True,
                 max_backups: int = 5,
                 lock_timeout: int = 10):
        """
        Initialize the enhanced file manager.
        
        Args:
            storage_dir: Directory for storing conversation files. If None, uses config.
            serializer: Serializer for conversation data. If None, creates a new one.
            logger: Logger instance for reporting operations. If None, creates a new one.
            backup_enabled: Whether automatic backups are enabled.
            max_backups: Maximum number of backup sets to keep.
            lock_timeout: Maximum time to wait for locks in seconds.
        """
        # Initialize base FileManager
        super().__init__(storage_dir, serializer, logger)
        
        # Initialize backup manager if enabled
        self.backup_enabled = backup_enabled
        self.last_backup_time = None
        self.backup_frequency = get_backup_frequency()  # in hours
        self.lock_timeout = lock_timeout
        
        if backup_enabled:
            self.backup_manager = BackupManager(
                storage_dir=self.storage_dir,
                max_backups=max_backups,
                logger=self.logger
            )
            self.logger.info({
                "action": "BACKUP_ENABLED",
                "message": "Backup enabled with configured frequency",
                "data": {
                    "backup_frequency_hours": self.backup_frequency,
                    "max_backups": max_backups
                }
            })
    
    def save_conversation(self, conversation: Dict[str, Any], force: bool = False) -> str:
        """
        Serialize and save a conversation as an unprocessed file with locking.
        
        Args:
            conversation: Dictionary representing a Telegram conversation.
            force: If True, overwrites any existing file.
            
        Returns:
            str: Path to the saved file.
            
        Raises:
            ValueError: If the conversation is invalid or missing required fields.
            FileExistsError: If the file already exists and force is False.
            TimeoutError: If the lock cannot be acquired.
        """
        # Extract conversation ID from metadata
        try:
            # Add conversation type metadata before saving
            conversation = self._add_conversation_type_metadata(conversation)
            
            metadata = self.serializer.extract_metadata(conversation)
            conversation_id = metadata.get("id")
            
            if not conversation_id:
                raise ValueError("Conversation ID not found in metadata")
                
        except Exception as e:
            self.logger.error({
                "action": "CONVERSATION_ID_EXTRACTION_FAILED",
                "message": "Failed to extract conversation ID",
                "data": {
                    "error": str(e)
                },
                "exception": e
            })
            raise ValueError(f"Invalid conversation structure: {str(e)}")
        
        # Get file path (always unprocessed when saving initially)
        file_path = self.get_storage_path(conversation_id, processed=False)
        
        # Check if file exists and handle force flag
        if os.path.exists(file_path) and not force:
            self.logger.warning({
                "action": "FILE_ALREADY_EXISTS",
                "message": "File already exists",
                "data": {
                    "file_path": file_path,
                    "conversation_id": conversation_id,
                    "force": force
                }
            })
            raise FileExistsError(f"Conversation file already exists: {file_path}")
        
        # Serialize conversation
        json_string = self.serializer.serialize_conversation(conversation, pretty=True)
        
        # Use file lock for atomic write
        try:
            with FileSystemLock.acquire(file_path, shared=False, timeout=self.lock_timeout):
                atomic_write(file_path, json_string)
                self.logger.info({
                    "action": "CONVERSATION_SAVED",
                    "message": "Saved conversation to file",
                    "data": {
                        "conversation_id": conversation_id,
                        "file_path": file_path,
                        "processed": False,
                        "with_lock": True
                    }
                })
                
                # Check if we need to create a backup
                self._check_and_create_backup()
                
                return file_path
                
        except TimeoutError:
            self.logger.error({
                "action": "LOCK_ACQUISITION_FAILED",
                "message": "Could not acquire lock for writing file",
                "data": {
                    "file_path": file_path,
                    "conversation_id": conversation_id,
                    "timeout": self.lock_timeout
                }
            })
            raise TimeoutError(f"Could not acquire lock for writing file: {file_path}")
            
        except Exception as e:
            self.logger.error({
                "action": "SAVE_CONVERSATION_FAILED",
                "message": "Failed to save conversation",
                "data": {
                    "conversation_id": conversation_id,
                    "file_path": file_path,
                    "error": str(e)
                },
                "exception": e
            })
            raise IOError(f"Failed to save conversation: {str(e)}")
    
    def load_conversation(self, conversation_id: str, require_unprocessed: bool = False) -> Dict[str, Any]:
        """
        Load and deserialize a conversation by ID with file locking.
        
        Args:
            conversation_id: Unique identifier for the conversation.
            require_unprocessed: If True, only loads unprocessed conversations.
            
        Returns:
            Dict[str, Any]: Dictionary representation of the conversation.
            
        Raises:
            FileNotFoundError: If the conversation file is not found.
            ValueError: If the file contains invalid JSON or schema.
            TimeoutError: If the lock cannot be acquired.
        """
        # First try to find the file with the specified status if required
        if require_unprocessed:
            file_path = self.get_storage_path(conversation_id, processed=False)
            if not os.path.exists(file_path):
                self.logger.error({
                    "action": "UNPROCESSED_FILE_NOT_FOUND",
                    "message": "Unprocessed conversation file not found",
                    "data": {
                        "conversation_id": conversation_id,
                        "file_path": file_path
                    }
                })
                raise FileNotFoundError(f"Unprocessed conversation file not found: {file_path}")
        else:
            # Try unprocessed first, then processed
            unprocessed_path = self.get_storage_path(conversation_id, processed=False)
            processed_path = self.get_storage_path(conversation_id, processed=True)
            
            if os.path.exists(unprocessed_path):
                file_path = unprocessed_path
            elif os.path.exists(processed_path):
                file_path = processed_path
            else:
                self.logger.info({
                    "action": "CONVERSATION_FILE_NOT_FOUND",
                    "message": "Conversation file not found for ID",
                    "data": {
                        "conversation_id": conversation_id,
                        "unprocessed_path": unprocessed_path,
                        "processed_path": processed_path
                    }
                })
                raise FileNotFoundError(f"Conversation file not found for ID: {conversation_id}")
        
        try:
            # Use shared lock for reading
            with FileSystemLock.acquire(file_path, shared=True, timeout=self.lock_timeout):
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_string = f.read()
                
                conversation = self.serializer.deserialize_conversation(json_string)
                self.logger.info({
                    "action": "CONVERSATION_LOADED",
                    "message": "Loaded conversation from file",
                    "data": {
                        "conversation_id": conversation_id,
                        "file_path": file_path,
                        "processed": "processed" in file_path,
                        "with_lock": True
                    }
                })
                return conversation
                
        except TimeoutError:
            self.logger.error({
                "action": "LOCK_ACQUISITION_FAILED",
                "message": "Could not acquire lock for reading file",
                "data": {
                    "file_path": file_path,
                    "conversation_id": conversation_id,
                    "timeout": self.lock_timeout
                }
            })
            raise TimeoutError(f"Could not acquire lock for reading file: {file_path}")
            
        except Exception as e:
            self.logger.error({
                "action": "LOAD_CONVERSATION_FAILED",
                "message": "Failed to load conversation",
                "data": {
                    "conversation_id": conversation_id,
                    "file_path": file_path,
                    "error": str(e)
                },
                "exception": e
            })
            raise ValueError(f"Failed to load conversation: {str(e)}")
    
    def mark_as_processed(self, conversation_id: str) -> str:
        """
        Rename a conversation file to indicate processed status with file locking.
        
        Args:
            conversation_id: Unique identifier for the conversation.
            
        Returns:
            str: Path to the renamed file.
            
        Raises:
            FileNotFoundError: If the unprocessed conversation file is not found.
            FileExistsError: If the processed file already exists.
            TimeoutError: If the lock cannot be acquired.
        """
        unprocessed_path = self.get_storage_path(conversation_id, processed=False)
        processed_path = self.get_storage_path(conversation_id, processed=True)
        
        # Check if unprocessed file exists
        if not os.path.exists(unprocessed_path):
            self.logger.error({
                "action": "UNPROCESSED_FILE_NOT_FOUND",
                "message": "Unprocessed conversation file not found",
                "data": {
                    "conversation_id": conversation_id,
                    "file_path": unprocessed_path
                }
            })
            raise FileNotFoundError(f"Unprocessed conversation file not found: {unprocessed_path}")
        
        # Check if processed file already exists
        if os.path.exists(processed_path):
            self.logger.warning({
                "action": "PROCESSED_FILE_EXISTS",
                "message": "Processed file already exists",
                "data": {
                    "conversation_id": conversation_id,
                    "file_path": processed_path
                }
            })
            raise FileExistsError(f"Processed file already exists: {processed_path}")
        
        # Try to acquire locks on both files
        try:
            # Need exclusive lock on both source and destination
            with FileSystemLock.acquire(unprocessed_path, shared=False, timeout=self.lock_timeout):
                with FileSystemLock.acquire(processed_path, shared=False, timeout=self.lock_timeout):
                    # Rename the file (atomic operation on same filesystem)
                    os.rename(unprocessed_path, processed_path)
                    self.logger.info({
                        "action": "CONVERSATION_MARKED_PROCESSED",
                        "message": "Marked conversation as processed",
                        "data": {
                            "conversation_id": conversation_id,
                            "old_path": unprocessed_path,
                            "new_path": processed_path,
                            "with_lock": True
                        }
                    })
                    return processed_path
                    
        except TimeoutError:
            self.logger.error({
                "action": "LOCK_ACQUISITION_FAILED",
                "message": "Could not acquire locks for renaming file",
                "data": {
                    "conversation_id": conversation_id,
                    "unprocessed_path": unprocessed_path,
                    "processed_path": processed_path,
                    "timeout": self.lock_timeout
                }
            })
            raise TimeoutError(f"Could not acquire locks for renaming file: {unprocessed_path}")
            
        except Exception as e:
            self.logger.error({
                "action": "MARK_PROCESSED_FAILED",
                "message": "Failed to mark conversation as processed",
                "data": {
                    "conversation_id": conversation_id,
                    "unprocessed_path": unprocessed_path,
                    "processed_path": processed_path,
                    "error": str(e)
                },
                "exception": e
            })
            raise IOError(f"Failed to mark conversation as processed: {str(e)}")
    
    def process_all_unprocessed(self, processor_func: callable) -> Dict[str, Any]:
        """
        Process all unprocessed conversations in parallel.
        
        Args:
            processor_func: Function that takes a conversation and returns a result.
                The function should handle its own exceptions.
                
        Returns:
            Dict[str, Any]: Dictionary mapping conversation IDs to processor results.
        """
        # Get all unprocessed conversation IDs
        unprocessed_ids = self.list_conversations(processed=False)
        
        results = {}
        
        # Define processor function wrapper to handle loading
        def process_conversation(conversation_id):
            try:
                conversation = self.load_conversation(conversation_id, require_unprocessed=True)
                result = processor_func(conversation)
                
                # If processing was successful, mark as processed
                self.mark_as_processed(conversation_id)
                
                return result
            except Exception as e:
                return f"Error: {str(e)}"
        
        # Process conversations in parallel
        for conversation_id in unprocessed_ids:
            try:
                result = process_conversation(conversation_id)
                results[conversation_id] = result
            except Exception as e:
                results[conversation_id] = f"Error: {str(e)}"
        
        return results
    
    def create_manual_backup(self, tag: Optional[str] = None) -> str:
        """
        Create a manual backup of all conversation files.
        
        Args:
            tag: Optional tag to add to the backup directory name.
            
        Returns:
            str: Path to the created backup directory.
            
        Raises:
            RuntimeError: If backups are not enabled.
            IOError: If there is an error creating the backup.
        """
        if not self.backup_enabled:
            raise RuntimeError("Backups are not enabled for this file manager")
        
        # Update last backup time
        self.last_backup_time = datetime.now()
        
        return self.backup_manager.create_backup(tag)
    
    def restore_backup(self, backup_id: str, overwrite: bool = False) -> int:
        """
        Restore a backup to the storage directory.
        
        Args:
            backup_id: Identifier (timestamp or timestamp_tag) of the backup to restore.
            overwrite: If True, overwrite existing files. If False, skip existing files.
            
        Returns:
            int: Number of files restored.
            
        Raises:
            RuntimeError: If backups are not enabled.
            FileNotFoundError: If the specified backup doesn't exist.
            IOError: If there is an error restoring the backup.
        """
        if not self.backup_enabled:
            raise RuntimeError("Backups are not enabled for this file manager")
        
        return self.backup_manager.restore_backup(backup_id, overwrite)
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups.
        
        Returns:
            List[Dict[str, Any]]: List of backup information dictionaries.
            
        Raises:
            RuntimeError: If backups are not enabled.
        """
        if not self.backup_enabled:
            raise RuntimeError("Backups are not enabled for this file manager")
        
        return self.backup_manager.list_backups()
    
    def _check_and_create_backup(self) -> None:
        """
        Check if it's time to create a backup and create one if needed.
        """
        if not self.backup_enabled:
            return
        
        current_time = datetime.now()
        
        # If we haven't created a backup yet or it's been longer than the backup frequency
        if (self.last_backup_time is None or 
            current_time - self.last_backup_time > timedelta(hours=self.backup_frequency)):
            
            try:
                self.logger.info({
                    "action": "CREATING_AUTOMATIC_BACKUP",
                    "message": "Creating automatic backup",
                    "data": {
                        "backup_type": "auto",
                        "last_backup_time": self.last_backup_time.isoformat() if self.last_backup_time else None,
                        "backup_frequency_hours": self.backup_frequency
                    }
                })
                self.backup_manager.create_backup("auto")
                self.last_backup_time = current_time
            except Exception as e:
                self.logger.error({
                    "action": "AUTOMATIC_BACKUP_FAILED",
                    "message": "Failed to create automatic backup",
                    "data": {
                        "error": str(e)
                    },
                    "exception": e
                })
    
    def export_conversations_to_json(self, output_file: str, processed: Optional[bool] = None) -> int:
        """
        Export conversations to a single JSON file.
        
        Args:
            output_file: Path to the output JSON file.
            processed: If True, only export processed conversations.
                     If False, only export unprocessed conversations.
                     If None, export all conversations.
            
        Returns:
            int: Number of conversations exported.
            
        Raises:
            IOError: If there is an error exporting the conversations.
        """
        # Get conversation IDs based on status
        conversation_ids = self.list_conversations(processed=processed)
        
        export_data = {
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "conversation_count": len(conversation_ids),
                "processed_filter": processed
            },
            "conversations": {}
        }
        
        # Load each conversation and add to export data
        for conversation_id in conversation_ids:
            try:
                conversation = self.load_conversation(conversation_id)
                export_data["conversations"][conversation_id] = conversation
            except Exception as e:
                self.logger.error({
                    "action": "EXPORT_CONVERSATION_FAILED",
                    "message": "Failed to export conversation",
                    "data": {
                        "conversation_id": conversation_id,
                        "error": str(e)
                    },
                    "exception": e
                })
        
        # Write to output file
        try:
            output_dir = os.path.dirname(output_file)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
                
            self.logger.info({
                "action": "CONVERSATIONS_EXPORTED",
                "message": "Exported conversations to file",
                "data": {
                    "output_file": output_file,
                    "conversation_count": len(conversation_ids),
                    "processed_filter": processed
                }
            })
            return len(conversation_ids)
            
        except Exception as e:
            self.logger.error({
                "action": "EXPORT_FILE_WRITE_FAILED",
                "message": "Failed to write export file",
                "data": {
                    "output_file": output_file,
                    "error": str(e)
                },
                "exception": e
            })
            raise IOError(f"Failed to write export file: {str(e)}")
    
    def import_conversations_from_json(self, input_file: str, overwrite: bool = False) -> int:
        """
        Import conversations from a JSON file.
        
        Args:
            input_file: Path to the input JSON file.
            overwrite: If True, overwrite existing files. If False, skip existing files.
            
        Returns:
            int: Number of conversations imported.
            
        Raises:
            FileNotFoundError: If the input file doesn't exist.
            ValueError: If the input file contains invalid JSON.
            IOError: If there is an error importing the conversations.
        """
        # Check if input file exists
        if not os.path.exists(input_file):
            self.logger.error({
                "action": "IMPORT_FILE_NOT_FOUND",
                "message": "Input file not found",
                "data": {
                    "input_file": input_file
                }
            })
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        try:
            # Read input file
            with open(input_file, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Validate import data structure
            if not isinstance(import_data, dict) or "conversations" not in import_data:
                self.logger.error({
                    "action": "INVALID_IMPORT_FORMAT",
                    "message": "Invalid import file format",
                    "data": {
                        "input_file": input_file,
                        "expected_key": "conversations"
                    }
                })
                raise ValueError("Invalid import file format. Expected 'conversations' key.")
            
            conversations = import_data.get("conversations", {})
            imported_count = 0
            
            # Import each conversation
            for conversation_id, conversation in conversations.items():
                try:
                    # Validate conversation
                    self.serializer.validate_conversation(conversation)
                    
                    # Save conversation
                    self.save_conversation(conversation, force=overwrite)
                    imported_count += 1
                    
                except FileExistsError:
                    self.logger.warning({
                        "action": "IMPORT_CONVERSATION_EXISTS",
                        "message": "Skipping existing conversation",
                        "data": {
                            "conversation_id": conversation_id,
                            "overwrite": overwrite
                        }
                    })
                    
                except Exception as e:
                    self.logger.error({
                        "action": "IMPORT_CONVERSATION_FAILED",
                        "message": "Failed to import conversation",
                        "data": {
                            "conversation_id": conversation_id,
                            "error": str(e)
                        },
                        "exception": e
                    })
            
            self.logger.info({
                "action": "CONVERSATIONS_IMPORTED",
                "message": "Imported conversations from file",
                "data": {
                    "input_file": input_file,
                    "imported_count": imported_count,
                    "total_conversations": len(conversations),
                    "overwrite": overwrite
                }
            })
            return imported_count
            
        except json.JSONDecodeError as e:
            self.logger.error({
                "action": "INVALID_JSON_IN_IMPORT",
                "message": "Invalid JSON in import file",
                "data": {
                    "input_file": input_file,
                    "error": str(e)
                },
                "exception": e
            })
            raise ValueError(f"Invalid JSON in import file: {str(e)}")
            
        except Exception as e:
            self.logger.error({
                "action": "IMPORT_CONVERSATIONS_FAILED",
                "message": "Failed to import conversations",
                "data": {
                    "input_file": input_file,
                    "error": str(e)
                },
                "exception": e
            })
            raise IOError(f"Failed to import conversations: {str(e)}")
    
    def _add_conversation_type_metadata(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add conversation type metadata to a conversation.
        
        Args:
            conversation: Dictionary representing a Telegram conversation.
            
        Returns:
            Dict[str, Any]: Updated conversation with type metadata.
        """
        if not conversation or "metadata" not in conversation:
            return conversation
        
        metadata = conversation["metadata"]
        metadata["conversation_types"] = []
        
        if is_personal_chat(conversation):
            metadata["conversation_types"].append("personal_chat")
        
        if is_bot_chat(conversation):
            metadata["conversation_types"].append("bot_chat")
            
        if is_private_group(conversation):
            metadata["conversation_types"].append("private_group")
            
        return conversation
    
    def filter_by_conversation_type(self, conversations: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Filter conversations based on the configured fetch mode.
        
        Args:
            conversations: Dictionary of conversations keyed by conversation_id.
            
        Returns:
            Dict[str, Dict[str, Any]]: Filtered conversations based on fetch mode.
        """
        fetch_mode = get_fetch_mode_from_config()
        self.logger.info({
            "action": "FILTERING_CONVERSATIONS",
            "message": "Filtering conversations using fetch mode",
            "data": {
                "fetch_mode": fetch_mode,
                "original_count": len(conversations)
            }
        })
        
        return filter_conversations(conversations, fetch_mode)
    
    def batch_save_conversations(self, conversations: Dict[str, Dict[str, Any]], force: bool = False) -> Dict[str, str]:
        """
        Save multiple conversations, filtering based on fetch mode.
        
        Args:
            conversations: Dictionary of conversations keyed by conversation_id.
            force: If True, overwrites any existing files.
            
        Returns:
            Dict[str, str]: Dictionary mapping conversation IDs to file paths.
        """
        # Filter conversations based on fetch mode
        filtered_conversations = self.filter_by_conversation_type(conversations)
        
        if len(filtered_conversations) < len(conversations):
            self.logger.info({
                "action": "CONVERSATIONS_FILTERED",
                "message": "Filtered conversations based on fetch mode",
                "data": {
                    "original_count": len(conversations),
                    "filtered_count": len(filtered_conversations),
                    "filtered_out": len(conversations) - len(filtered_conversations)
                }
            })
        
        # Save each filtered conversation
        results = {}
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for conv_id, conversation in filtered_conversations.items():
            try:
                file_path = self.save_conversation(conversation, force=force)
                results[conv_id] = file_path
                success_count += 1
            except FileExistsError:
                if not force:
                    self.logger.warning({
                        "action": "BATCH_SAVE_SKIPPED",
                        "message": "Skipping existing conversation",
                        "data": {
                            "conversation_id": conv_id,
                            "force": force
                        }
                    })
                    skip_count += 1
                    continue
            except Exception as e:
                self.logger.error({
                    "action": "BATCH_SAVE_FAILED",
                    "message": "Error saving conversation in batch",
                    "data": {
                        "conversation_id": conv_id,
                        "error": str(e)
                    },
                    "exception": e
                })
                error_count += 1
                continue
        
        self.logger.info({
            "action": "BATCH_SAVE_COMPLETED",
            "message": "Batch save operation completed",
            "data": {
                "total_processed": len(filtered_conversations),
                "success_count": success_count,
                "skip_count": skip_count,
                "error_count": error_count
            }
        })
                
        return results 