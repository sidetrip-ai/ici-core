from abc import ABC, abstractmethod
from typing import Any, Optional, Dict
from datetime import datetime


class Ingestor(ABC):
    """
    Interface for components that fetch raw data from external sources.

    Each Ingestor is designed for a specific data source, handling authentication
    and API-specific logic. Ingestors should be stateless, with state information
    maintained externally in a dedicated state storage.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the ingestor with configuration parameters.
        
        This method should be called after the ingestor instance is created,
        before any other methods are used. Configuration should be loaded from
        a central configuration source (e.g., config.yaml).
        
        Returns:
            None
        
        Raises:
            Exception: If initialization fails for any reason.
        """
        pass

    @abstractmethod
    async def fetch_full_data(self) -> Any:
        """
        Fetches all available data for initial ingestion.

        Returns:
            Any: Raw data in a source-native format for the Preprocessor to handle.

        Raises:
            IngestorError: If data fetching fails for any reason.
        """
        pass

    @abstractmethod
    async def fetch_new_data(self, since: Optional[datetime] = None) -> Any:
        """
        Fetches new data since the given timestamp.

        This method enables incremental ingestion by retrieving only data newer
        than the specified timestamp.

        Args:
            since: Optional timestamp to fetch data from. If None, should use
                  a reasonable default (e.g., last hour or day).

        Returns:
            Any: Raw data in a source-native format for the Preprocessor to handle.

        Raises:
            IngestorError: If data fetching fails for any reason.
        """
        pass

    @abstractmethod
    async def fetch_data_in_range(self, start: datetime, end: datetime) -> Any:
        """
        Fetches data within a specified date range.

        Args:
            start: Start timestamp for data range.
            end: End timestamp for data range.

        Returns:
            Any: Raw data in a source-native format for the Preprocessor to handle.

        Raises:
            IngestorError: If data fetching fails for any reason.
        """
        pass

    @abstractmethod
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Checks if the ingestor is properly configured and can connect to its data source.

        Returns:
            Dict[str, Any]: A dictionary containing health status information:
                {
                    'healthy': bool,  # Whether the ingestor is functioning properly
                    'message': str,   # Optional message providing more details
                    'details': dict   # Optional additional details about the health check
                }

        Raises:
            IngestorError: If the health check itself encounters an error.
        """
        pass
