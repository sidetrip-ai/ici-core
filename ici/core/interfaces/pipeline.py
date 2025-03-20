from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List


class IngestionPipeline(ABC):
    """
    Interface for components that manage the ingestion process, including scheduling,
    state tracking, and component coordination.

    The IngestionPipeline coordinates Ingestor, Preprocessor, Embedder, and VectorStore
    components in a sequential workflow, with configurable scheduling options.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the ingestion pipeline with configuration parameters.
        
        This method should be called after the pipeline instance is created,
        before any other methods are used. Configuration should be loaded from
        a central configuration source (e.g., config.yaml).
        
        Returns:
            None
        
        Raises:
            Exception: If initialization fails for any reason.
        """
        pass

    @abstractmethod
    async def run_ingestion(self, ingestor_id: str) -> Dict[str, Any]:
        """
        Executes the ingestion process for a specific ingestor.

        Workflow:
        1. Retrieves ingestor state from the database (including last_timestamp)
        2. Calls appropriate ingestor method based on state
        3. Preprocesses raw data into standardized format
        4. Generates embeddings for each document
        5. Stores documents with vectors and metadata
        6. Updates ingestor state with the latest timestamp

        Args:
            ingestor_id: Unique identifier for the ingestor (e.g., "@alice/twitter_ingestor")

        Returns:
            Dict[str, Any]: Summary of the ingestion run, including:
                - 'success': bool - Whether ingestion completed successfully
                - 'documents_processed': int - Number of documents processed
                - 'errors': List[str] - Any errors encountered
                - 'start_time': datetime - When ingestion started
                - 'end_time': datetime - When ingestion completed
                - 'duration': float - Duration in seconds

        Raises:
            IngestionPipelineError: If the ingestion process fails critically
        """
        pass

    @abstractmethod
    async def start(self) -> None:
        """
        Asynchronously starts a single ingestion run.
        
        This method performs a single ingestion run following the async-first pattern.

        Raises:
            IngestionPipelineError: If the ingestion process fails
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Stops the ingestion scheduler.

        This method should gracefully stop the scheduler, allowing any in-progress
        ingestion to complete.

        Raises:
            IngestionPipelineError: If the scheduler cannot be stopped
        """
        pass

    @abstractmethod
    def register_ingestor(
        self, ingestor_id: str, ingestor_config: Dict[str, Any]
    ) -> None:
        """
        Registers an ingestor with the pipeline.

        Args:
            ingestor_id: Unique identifier for the ingestor
            ingestor_config: Configuration for the ingestor, including:
                - 'type': str - Ingestor class/type
                - 'config': Dict[str, Any] - Ingestor-specific configuration
                - 'schedule': Dict[str, Any] - Scheduling parameters

        Raises:
            IngestionPipelineError: If registration fails
        """
        pass

    @abstractmethod
    def get_ingestor_state(self, ingestor_id: str) -> Dict[str, Any]:
        """
        Retrieves the current state for an ingestor.

        Args:
            ingestor_id: Unique identifier for the ingestor

        Returns:
            Dict[str, Any]: Current state information, including:
                - 'last_timestamp': datetime - Timestamp of last successful ingestion
                - 'additional_metadata': Dict[str, Any] - Additional state information

        Raises:
            IngestionPipelineError: If state cannot be retrieved
        """
        pass

    @abstractmethod
    def set_ingestor_state(self, ingestor_id: str, state: Dict[str, Any]) -> None:
        """
        Updates the state for an ingestor.

        Args:
            ingestor_id: Unique identifier for the ingestor
            state: New state information

        Raises:
            IngestionPipelineError: If state cannot be updated
        """
        pass

    @abstractmethod
    async def healthcheck(self) -> Dict[str, Any]:
        """
        Checks if the ingestion pipeline and all its components are properly configured and functioning.

        Returns:
            Dict[str, Any]: A dictionary containing health status information:
                {
                    'healthy': bool,  # Whether the pipeline is functioning properly
                    'message': str,   # Optional message providing more details
                    'details': dict,  # Optional additional details
                    'components': {    # Health status of each component
                        'ingestor': {...},
                        'preprocessor': {...},
                        'embedder': {...},
                        'vector_store': {...}
                    }
                }

        Raises:
            IngestionPipelineError: If the health check itself encounters an error
        """
        pass
