from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime

class Ingestor(ABC):
    """Base class for all data ingestors."""
    
    def __init__(self):
        """Initialize the ingestor."""
        pass
    
    @abstractmethod
    def fetch_full_data(self) -> Dict[str, Any]:
        """
        Fetch all available data from the source.
        
        Returns:
            Dict containing all fetched data
        """
        pass
    
    @abstractmethod
    def fetch_new_data(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Fetch new data since the specified timestamp.
        
        Args:
            since: Optional datetime to fetch data from
            
        Returns:
            Dict containing new data
        """
        pass
    
    @abstractmethod
    def fetch_data_in_range(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """
        Fetch data within a specific date range.
        
        Args:
            start: Start datetime
            end: End datetime
            
        Returns:
            Dict containing data within range
        """
        pass 