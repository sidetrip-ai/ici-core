from abc import ABC, abstractmethod
from typing import Any, Dict, List

class Preprocessor(ABC):
    """Base class for all data preprocessors."""
    
    def __init__(self):
        """Initialize the preprocessor."""
        pass
    
    @abstractmethod
    def preprocess(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transform raw data into standardized documents.
        
        Args:
            raw_data: Raw data from ingestor
            
        Returns:
            List of standardized documents ready for embedding
        """
        pass 