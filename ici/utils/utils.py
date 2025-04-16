"""
Utility functions for Telegram storage file operations.

This module provides additional functionality for file system operations,
including backup management, file locking, and path utilities.
"""

import os
import shutil
import glob
import time
import fcntl
import tempfile
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Callable
import threading
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed

from ici.adapters.loggers import StructuredLogger
from ici.utils.config import get_component_config


class FileSystemLock:
    """
    File-based locking mechanism to prevent concurrent access to files.
    Uses fcntl for Unix-based systems.
    """
    
    # Dictionary to track open lock files
    _locks = {}
    _lock = threading.Lock()
    
    @staticmethod
    @contextmanager
    def acquire(filepath: str, shared: bool = False, timeout: int = 10):
        """
        Acquire a lock on a file.
        
        Args:
            filepath: Path to the file to lock.
            shared: If True, allow shared access (read). If False, exclusive access (write).
            timeout: Maximum time to wait for lock in seconds.
            
        Yields:
            The lock file descriptor.
            
        Raises:
            TimeoutError: If the lock cannot be acquired within the timeout period.
            IOError: If there is an error acquiring the lock.
        """
        lock_file = f"{filepath}.lock"
        lock_type = fcntl.LOCK_SH if shared else fcntl.LOCK_EX
        lock_type |= fcntl.LOCK_NB  # Non-blocking
        
        # Create directory for lock file if it doesn't exist
        os.makedirs(os.path.dirname(lock_file), exist_ok=True)
        
        # Keep track of start time for timeout
        start_time = time.time()
        
        while True:
            try:
                # Try to acquire the lock
                with FileSystemLock._lock:
                    if lock_file in FileSystemLock._locks:
                        fd = FileSystemLock._locks[lock_file]
                    else:
                        fd = open(lock_file, 'w+')
                        FileSystemLock._locks[lock_file] = fd
                
                fcntl.flock(fd, lock_type)
                
                try:
                    yield fd
                finally:
                    # Release the lock
                    fcntl.flock(fd, fcntl.LOCK_UN)
                
                break
                
            except IOError:
                # Check if we've timed out
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Could not acquire lock on {filepath} within {timeout} seconds")
                
                # Wait a bit before trying again
                time.sleep(0.1)
            
            except Exception as e:
                with FileSystemLock._lock:
                    if lock_file in FileSystemLock._locks:
                        FileSystemLock._locks[lock_file].close()
                        del FileSystemLock._locks[lock_file]
                
                raise IOError(f"Error acquiring lock on {filepath}: {str(e)}")


class BackupManager:
    """
    Manages backups of Telegram conversation files.
    """
    
    def __init__(self, 
                 storage_dir: str,
                 backup_dir: Optional[str] = None,
                 max_backups: int = 5,
                 logger: Optional[StructuredLogger] = None):
        """
        Initialize the backup manager.
        
        Args:
            storage_dir: Directory containing the conversation files to backup.
            backup_dir: Directory to store backups. If None, uses storage_dir/backups.
            max_backups: Maximum number of backup sets to keep.
            logger: Logger instance for reporting operations.
        """
        newLogger = StructuredLogger(__name__)
        newLogger.initialize()
        self.logger = logger or newLogger
        self.storage_dir = storage_dir
        
        # Set backup directory
        if backup_dir is None:
            self.backup_dir = os.path.join(storage_dir, "backups")
        else:
            self.backup_dir = backup_dir
            
        self.max_backups = max_backups
        
        # Create backup directory if it doesn't exist
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def create_backup(self, tag: Optional[str] = None) -> str:
        """
        Create a backup of all conversation files.
        
        Args:
            tag: Optional tag to add to the backup directory name.
            
        Returns:
            str: Path to the created backup directory.
            
        Raises:
            IOError: If there is an error creating the backup.
        """
        try:
            # Generate backup timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            
            # Create backup directory name
            if tag:
                backup_name = f"{timestamp}_{tag}"
            else:
                backup_name = timestamp
                
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # Create backup directory
            os.makedirs(backup_path, exist_ok=True)
            
            # Copy all JSON files to backup directory
            file_count = 0
            for filename in glob.glob(os.path.join(self.storage_dir, "*.json")):
                if os.path.isfile(filename):
                    shutil.copy2(filename, backup_path)
                    file_count += 1
            
            self.logger.info({
                "action": "BACKUP_CREATED",
                "message": "Backup created",
                "data": {
                    "backup_path": backup_path,
                    "file_count": file_count
                }
            })
            
            # Cleanup old backups
            self._cleanup_old_backups()
            
            return backup_path
            
        except Exception as e:
            self.logger.error({
                "action": "BACKUP_CREATION_FAILED",
                "message": "Failed to create backup",
                "data": {
                    "error": str(e),
                    "storage_dir": self.storage_dir
                },
                "exception": e
            })
            raise IOError(f"Failed to create backup: {str(e)}")
    
    def restore_backup(self, backup_id: str, overwrite: bool = False) -> int:
        """
        Restore a backup to the storage directory.
        
        Args:
            backup_id: Identifier (timestamp or timestamp_tag) of the backup to restore.
            overwrite: If True, overwrite existing files. If False, skip existing files.
            
        Returns:
            int: Number of files restored.
            
        Raises:
            FileNotFoundError: If the specified backup doesn't exist.
            IOError: If there is an error restoring the backup.
        """
        # Find backup directory
        backup_path = os.path.join(self.backup_dir, backup_id)
        
        if not os.path.isdir(backup_path):
            # Try partial match
            matching_dirs = [d for d in os.listdir(self.backup_dir) 
                           if d.startswith(backup_id) and os.path.isdir(os.path.join(self.backup_dir, d))]
            
            if len(matching_dirs) == 1:
                backup_path = os.path.join(self.backup_dir, matching_dirs[0])
            elif len(matching_dirs) > 1:
                raise FileNotFoundError(f"Multiple backups match '{backup_id}': {', '.join(matching_dirs)}")
            else:
                raise FileNotFoundError(f"Backup '{backup_id}' not found")
        
        try:
            # Restore files
            file_count = 0
            for filename in glob.glob(os.path.join(backup_path, "*.json")):
                if os.path.isfile(filename):
                    base_filename = os.path.basename(filename)
                    target_path = os.path.join(self.storage_dir, base_filename)
                    
                    # Check if target file exists
                    if os.path.exists(target_path) and not overwrite:
                        self.logger.warning({
                            "action": "RESTORE_SKIP_EXISTING",
                            "message": "Skipping existing file during restore",
                            "data": {
                                "file_path": target_path
                            }
                        })
                        continue
                    
                    shutil.copy2(filename, self.storage_dir)
                    file_count += 1
            
            self.logger.info({
                "action": "BACKUP_RESTORED",
                "message": "Backup restored",
                "data": {
                    "backup_id": backup_id,
                    "file_count": file_count
                }
            })
            return file_count
            
        except Exception as e:
            self.logger.error({
                "action": "BACKUP_RESTORE_FAILED",
                "message": "Failed to restore backup",
                "data": {
                    "backup_id": backup_id,
                    "error": str(e)
                },
                "exception": e
            })
            raise IOError(f"Failed to restore backup: {str(e)}")
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups.
        
        Returns:
            List[Dict[str, Any]]: List of backup information dictionaries.
                Each dictionary includes:
                - id: Backup identifier
                - timestamp: Creation time
                - file_count: Number of files in the backup
                - path: Full path to the backup directory
        """
        backups = []
        
        # Get all subdirectories in backup directory
        for dirname in os.listdir(self.backup_dir):
            backup_path = os.path.join(self.backup_dir, dirname)
            
            if os.path.isdir(backup_path):
                # Count files in backup
                file_count = len(glob.glob(os.path.join(backup_path, "*.json")))
                
                # Parse timestamp from directory name
                try:
                    # Extract timestamp (first 14 characters for YYYYMMDDhhmmss)
                    timestamp_str = dirname[:14]
                    timestamp = datetime.datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                    
                    # Extract tag if present
                    tag = dirname[15:] if len(dirname) > 15 else None
                    
                    backups.append({
                        "id": dirname,
                        "timestamp": timestamp,
                        "tag": tag,
                        "file_count": file_count,
                        "path": backup_path
                    })
                except ValueError:
                    # Skip directories with invalid format
                    self.logger.warning({
                        "action": "INVALID_BACKUP_DIRECTORY",
                        "message": "Skipping invalid backup directory",
                        "data": {
                            "directory": dirname
                        }
                    })
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return backups
    
    def _cleanup_old_backups(self) -> int:
        """
        Remove old backups to stay within the maximum limit.
        
        Returns:
            int: Number of backups removed.
        """
        backups = self.list_backups()
        
        # If we have more backups than the limit, remove the oldest
        count_to_remove = max(0, len(backups) - self.max_backups)
        removed = 0
        
        if count_to_remove > 0:
            # Backups are already sorted newest first, so remove from the end
            for backup in backups[-count_to_remove:]:
                try:
                    shutil.rmtree(backup["path"])
                    self.logger.info({
                        "action": "BACKUP_REMOVED",
                        "message": "Removed old backup",
                        "data": {
                            "backup_id": backup['id']
                        }
                    })
                    removed += 1
                except Exception as e:
                    self.logger.error({
                        "action": "BACKUP_REMOVAL_FAILED",
                        "message": "Failed to remove backup",
                        "data": {
                            "backup_id": backup['id'],
                            "error": str(e)
                        },
                        "exception": e
                    })
        
        return removed


def get_backup_frequency() -> int:
    """
    Get the backup frequency from configuration.
    
    Returns:
        int: Backup frequency in hours. Default is 24 hours.
    """
    try:
        config = get_component_config("ingestors.telegram", "config.yaml")
        return int(config.get("backup_frequency", 24))
    except Exception:
        return 24  # Default to 24 hours


def atomic_write(filepath: str, content: str) -> None:
    """
    Write content to a file atomically to prevent corruption.
    
    Args:
        filepath: Path to the file to write.
        content: Content to write to the file.
        
    Raises:
        IOError: If there is an error writing to the file.
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Write to a temporary file first
    with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8') as temp_file:
        temp_file.write(content)
        temp_path = temp_file.name
    
    # Atomic move to destination
    try:
        shutil.move(temp_path, filepath)
    except Exception as e:
        # Clean up temp file if move failed
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise IOError(f"Failed to write file: {str(e)}")


def batch_process_files(directory: str, 
                       pattern: str, 
                       processor: Callable[[str], Any], 
                       max_workers: int = 4) -> Dict[str, Any]:
    """
    Process multiple files in parallel using a thread pool.
    
    Args:
        directory: Directory containing files to process.
        pattern: Glob pattern to match files.
        processor: Function that takes a file path and returns a result.
        max_workers: Maximum number of parallel threads.
        
    Returns:
        Dict[str, Any]: Dictionary mapping file paths to processor results.
    """
    results = {}
    file_paths = glob.glob(os.path.join(directory, pattern))
    
    if not file_paths:
        return results
    
    # Process files in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(processor, file_path): file_path
            for file_path in file_paths
        }
        
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                result = future.result()
                results[file_path] = result
            except Exception as e:
                results[file_path] = f"Error: {str(e)}"
    
    return results 