"""
State management utilities for tracking ingestor progress.

This module provides a StateManager class that handles persistence of ingestor
state in a SQLite database, including tracking timestamps and additional metadata.
"""

import os
import json
import sqlite3
import threading
import logging  # Temporary standard logging for initialization
from typing import Dict, Any, List, Optional
from datetime import datetime

# Remove the import that causes circular dependency
# from ici.adapters.loggers import StructuredLogger
from ici.utils.datetime_utils import from_timestamp, ensure_tz_aware


class StateManager:
    """
    Manages state persistence for ingestors using SQLite.
    
    This class provides a standardized interface for storing and retrieving
    ingestor state, including the last processed timestamp and additional
    metadata stored as JSON.
    """
    
    def __init__(self, db_path: str, logger_name: str = "state_manager"):
        """
        Initialize the StateManager.
        
        Args:
            db_path: Path to the SQLite database file
            logger_name: Name for the logger
        """
        self.db_path = db_path
        self.logger_name = logger_name  # Store the name for later logger initialization
        # Use a basic logger initially, will be replaced with StructuredLogger
        self.logger = logging.getLogger(logger_name)
        self._local = threading.local()
        self._initialized = False
    
    def _get_connection(self):
        """
        Get a thread-local database connection.
        
        Returns:
            sqlite3.Connection: A SQLite connection object for the current thread
        """
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            # Create a new connection for this thread
            self._local.connection = sqlite3.connect(self.db_path)
            
            # Enable foreign keys
            cursor = self._local.connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            
            self.logger.debug({
                "action": "STATE_MANAGER_THREAD_CONNECTION",
                "message": f"Created new database connection for thread {threading.get_ident()}",
                "data": {"thread_id": threading.get_ident()}
            })
            
        return self._local.connection
    
    def initialize(self) -> None:
        """
        Initialize the state database.
        
        Creates the database tables if they don't exist and sets up
        any necessary indices or constraints.
        
        Returns:
            None
        
        Raises:
            Exception: If database initialization fails
        """
        try:
            # Initialize the structured logger only when needed (lazy import)
            from ici.adapters.loggers import StructuredLogger
            self.logger = StructuredLogger(name=self.logger_name)
            
            # Ensure directory exists
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            
            # Connect to database using thread-local connection
            connection = self._get_connection()
            cursor = connection.cursor()
            
            # Create the ingestor_state table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS ingestor_state (
                ingestor_id TEXT PRIMARY KEY,
                last_timestamp INTEGER,
                additional_metadata TEXT
            )
            ''')
            
            connection.commit()
            self._initialized = True
            
            self.logger.info({
                "action": "STATE_MANAGER_INIT",
                "message": "State database initialized",
                "data": {"db_path": self.db_path}
            })
            
        except Exception as e:
            self.logger.error({
                "action": "STATE_MANAGER_INIT_ERROR",
                "message": f"Failed to initialize state database: {str(e)}",
                "data": {"db_path": self.db_path, "error": str(e)}
            })
            raise
    
    def get_state(self, ingestor_id: str) -> Dict[str, Any]:
        """
        Retrieve the current state for an ingestor.
        
        Args:
            ingestor_id: Unique identifier for the ingestor
            
        Returns:
            Dict[str, Any]: Current state information, including:
                - 'last_timestamp': int - Timestamp of last successful ingestion
                - 'additional_metadata': Dict[str, Any] - Additional state information
                
        Raises:
            Exception: If state retrieval fails
        """
        if not self._initialized:
            raise RuntimeError("StateManager not initialized. Call initialize() first.")
        
        try:
            # Get thread-local connection
            connection = self._get_connection()
            cursor = connection.cursor()
            
            cursor.execute(
                "SELECT last_timestamp, additional_metadata FROM ingestor_state WHERE ingestor_id = ?",
                (ingestor_id,)
            )
            result = cursor.fetchone()
            
            if result:
                last_timestamp, additional_metadata_json = result
                
                # Parse additional_metadata from JSON
                try:
                    additional_metadata = json.loads(additional_metadata_json) if additional_metadata_json else {}
                except json.JSONDecodeError:
                    self.logger.warning({
                        "action": "STATE_MANAGER_JSON_DECODE_ERROR",
                        "message": f"Failed to decode additional_metadata JSON for {ingestor_id}",
                        "data": {"ingestor_id": ingestor_id}
                    })
                    additional_metadata = {}
                
                return {
                    "last_timestamp": last_timestamp,
                    "additional_metadata": additional_metadata
                }
            else:
                # No state exists for this ingestor, return default
                return {
                    "last_timestamp": 0,
                    "additional_metadata": {}
                }
                
        except Exception as e:
            self.logger.error({
                "action": "STATE_MANAGER_GET_STATE_ERROR",
                "message": f"Failed to retrieve state for ingestor {ingestor_id}: {str(e)}",
                "data": {"ingestor_id": ingestor_id, "error": str(e)}
            })
            raise
    
    def set_state(self, ingestor_id: str, last_timestamp: int, additional_metadata: Dict[str, Any]) -> None:
        """
        Update the state for an ingestor.
        
        Args:
            ingestor_id: Unique identifier for the ingestor
            last_timestamp: Timestamp of the last processed data
            additional_metadata: Additional state information as a dictionary
            
        Returns:
            None
            
        Raises:
            Exception: If state update fails
        """
        if not self._initialized:
            raise RuntimeError("StateManager not initialized. Call initialize() first.")
        
        try:
            # Get thread-local connection
            connection = self._get_connection()
            
            # Serialize additional_metadata to JSON
            additional_metadata_json = json.dumps(additional_metadata)
            
            cursor = connection.cursor()
            
            # Use INSERT OR REPLACE to handle both new and existing records
            cursor.execute(
                """
                INSERT OR REPLACE INTO ingestor_state (ingestor_id, last_timestamp, additional_metadata)
                VALUES (?, ?, ?)
                """,
                (ingestor_id, last_timestamp, additional_metadata_json)
            )
            
            connection.commit()
            
            # Use the datetime_utils for proper timezone handling in logs
            readable_timestamp = from_timestamp(last_timestamp).isoformat() if last_timestamp else None
            
            self.logger.info({
                "action": "STATE_MANAGER_SET_STATE",
                "message": f"Updated state for ingestor {ingestor_id}",
                "data": {
                    "ingestor_id": ingestor_id,
                    "last_timestamp": last_timestamp,
                    "timestamp_readable": readable_timestamp
                }
            })
            
        except Exception as e:
            self.logger.error({
                "action": "STATE_MANAGER_SET_STATE_ERROR",
                "message": f"Failed to update state for ingestor {ingestor_id}: {str(e)}",
                "data": {"ingestor_id": ingestor_id, "error": str(e)}
            })
            raise
    
    def update_metadata(self, ingestor_id: str, metadata_updates: Dict[str, Any]) -> None:
        """
        Update specific fields in the additional_metadata without changing other fields.
        
        Args:
            ingestor_id: Unique identifier for the ingestor
            metadata_updates: Dictionary of metadata fields to update
            
        Returns:
            None
            
        Raises:
            Exception: If metadata update fails
        """
        if not self._initialized:
            raise RuntimeError("StateManager not initialized. Call initialize() first.")
        
        try:
            # Get current state
            current_state = self.get_state(ingestor_id)
            current_metadata = current_state.get("additional_metadata", {})
            
            # Update metadata with new values
            current_metadata.update(metadata_updates)
            
            # Save updated state
            self.set_state(
                ingestor_id=ingestor_id,
                last_timestamp=current_state.get("last_timestamp", 0),
                additional_metadata=current_metadata
            )
            
            self.logger.debug({
                "action": "STATE_MANAGER_UPDATE_METADATA",
                "message": f"Updated metadata for ingestor {ingestor_id}",
                "data": {
                    "ingestor_id": ingestor_id,
                    "updated_fields": list(metadata_updates.keys())
                }
            })
            
        except Exception as e:
            self.logger.error({
                "action": "STATE_MANAGER_UPDATE_METADATA_ERROR",
                "message": f"Failed to update metadata for ingestor {ingestor_id}: {str(e)}",
                "data": {"ingestor_id": ingestor_id, "error": str(e)}
            })
            raise
    
    def list_ingestors(self) -> List[str]:
        """
        List all registered ingestor IDs.
        
        Returns:
            List[str]: List of ingestor IDs
            
        Raises:
            Exception: If listing fails
        """
        if not self._initialized:
            raise RuntimeError("StateManager not initialized. Call initialize() first.")
        
        try:
            # Get thread-local connection
            connection = self._get_connection()
            cursor = connection.cursor()
            
            cursor.execute("SELECT ingestor_id FROM ingestor_state")
            result = cursor.fetchall()
            
            ingestor_ids = [row[0] for row in result]
            
            self.logger.debug({
                "action": "STATE_MANAGER_LIST_INGESTORS",
                "message": f"Listed {len(ingestor_ids)} registered ingestors",
                "data": {"count": len(ingestor_ids)}
            })
            
            return ingestor_ids
            
        except Exception as e:
            self.logger.error({
                "action": "STATE_MANAGER_LIST_INGESTORS_ERROR",
                "message": f"Failed to list ingestors: {str(e)}",
                "data": {"error": str(e)}
            })
            raise
    
    def delete_state(self, ingestor_id: str) -> None:
        """
        Delete the state for an ingestor.
        
        Args:
            ingestor_id: Unique identifier for the ingestor
            
        Returns:
            None
            
        Raises:
            Exception: If deletion fails
        """
        if not self._initialized:
            raise RuntimeError("StateManager not initialized. Call initialize() first.")
        
        try:
            # Get thread-local connection
            connection = self._get_connection()
            cursor = connection.cursor()
            
            cursor.execute(
                "DELETE FROM ingestor_state WHERE ingestor_id = ?",
                (ingestor_id,)
            )
            
            connection.commit()
            
            self.logger.info({
                "action": "STATE_MANAGER_DELETE_STATE",
                "message": f"Deleted state for ingestor {ingestor_id}",
                "data": {"ingestor_id": ingestor_id}
            })
            
        except Exception as e:
            self.logger.error({
                "action": "STATE_MANAGER_DELETE_STATE_ERROR",
                "message": f"Failed to delete state for ingestor {ingestor_id}: {str(e)}",
                "data": {"ingestor_id": ingestor_id, "error": str(e)}
            })
            raise
    
    def close(self) -> None:
        """
        Close all database connections.
        
        Returns:
            None
        """
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
            
            self.logger.debug({
                "action": "STATE_MANAGER_CLOSE",
                "message": f"Closed state database connection for thread {threading.get_ident()}",
                "data": {"thread_id": threading.get_ident()}
            }) 