# Continuous Ingestion Pipeline

## Overview

The continuous ingestion pipeline feature enables the ICI system to periodically fetch and process data from various sources in the background without requiring manual intervention. This implementation allows for a clear separation of concerns between query processing and data ingestion, with the ingestion process running as a background task on a configurable schedule.

## Implementation Details

The feature is implemented in the `DefaultIngestionPipeline` class and consists of:

1. A background task that runs in a loop
2. Configurable scheduling intervals for periodic ingestion 
3. Error handling and recovery mechanisms
4. Control methods for starting and stopping the process

### Key Components

#### Attributes

```python
def __init__(self, ...):
    # Existing initialization code...
    self._ingestion_task = None      # Holds the running task reference
    self._running = False            # Flag to track running state
    self._schedule_interval_minutes = 60  # Default interval between ingestion cycles
```

#### Start Method

```python
async def start(self) -> None:
    """
    Start the ingestion process as a continuous background task.
    
    This method starts a background task that periodically runs
    ingestion for all registered ingestors based on the configured interval.
    """
    if not self._is_initialized:
        raise IngestionPipelineError("Pipeline not initialized. Call initialize() first.")
    
    if self._running:
        self.logger.info({
            "action": "PIPELINE_ALREADY_RUNNING",
            "message": "Ingestion pipeline is already running"
        })
        return
        
    if not self._ingestors:
        self.logger.warning({
            "action": "PIPELINE_NO_INGESTORS",
            "message": "No ingestors registered, nothing to run"
        })
        return
    
    self.logger.info({
        "action": "PIPELINE_START",
        "message": f"Starting continuous ingestion for {len(self._ingestors)} registered ingestors",
        "data": {"schedule_interval_minutes": self._schedule_interval_minutes}
    })
    
    # Set running flag and start background task
    self._running = True
    self._ingestion_task = asyncio.create_task(self._run_periodic_ingestion())
```

#### Stop Method

```python
def stop(self) -> None:
    """
    Stop the continuous ingestion process.
    
    This method cancels the background ingestion task.
    """
    if not self._running:
        return
        
    self.logger.info({
        "action": "PIPELINE_STOP",
        "message": "Stopping continuous ingestion"
    })
    
    # Cancel the task and clear the running flag
    if self._ingestion_task:
        self._ingestion_task.cancel()
        self._ingestion_task = None
    
    self._running = False
    
    self.logger.info({
        "action": "PIPELINE_STOPPED",
        "message": "Continuous ingestion stopped"
    })
```

#### Periodic Ingestion Worker

```python
async def _run_periodic_ingestion(self) -> None:
    """
    Run the ingestion process periodically.
    
    This method runs in a loop, periodically executing ingestion for all
    registered ingestors based on the configured interval.
    """
    try:
        while self._running:
            start_time = datetime.now(timezone.utc)
            
            self.logger.info({
                "action": "PIPELINE_INGESTION_CYCLE_START",
                "message": "Starting ingestion cycle"
            })
            
            try:
                # Run ingestion for all registered ingestors
                for ingestor_id in self._ingestors.keys():
                    try:
                        await self.run_ingestion(ingestor_id)
                    except Exception as e:
                        self.logger.error({
                            "action": "INGESTOR_RUN_ERROR",
                            "message": f"Error running ingestion for {ingestor_id}: {str(e)}",
                            "data": {"ingestor_id": ingestor_id, "error": str(e)}
                        })
                
                self.logger.info({
                    "action": "PIPELINE_INGESTION_CYCLE_COMPLETE",
                    "message": "Completed ingestion cycle for all registered ingestors"
                })
            except Exception as e:
                self.logger.error({
                    "action": "PIPELINE_INGESTION_CYCLE_ERROR",
                    "message": f"Error in ingestion cycle: {str(e)}",
                    "data": {"error": str(e), "error_type": type(e).__name__}
                })
            
            # Calculate sleep time, ensuring we don't sleep negative time 
            # if processing took longer than interval
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            sleep_seconds = max(0, self._schedule_interval_minutes * 60 - elapsed)
            
            self.logger.info({
                "action": "PIPELINE_WAITING",
                "message": f"Waiting {sleep_seconds:.1f} seconds until next ingestion cycle",
                "data": {"sleep_seconds": sleep_seconds}
            })
            
            # Sleep until next cycle
            await asyncio.sleep(sleep_seconds)
    
    except asyncio.CancelledError:
        # Task was cancelled, exit gracefully
        self.logger.info({
            "action": "PIPELINE_TASK_CANCELLED",
            "message": "Ingestion task cancelled"
        })
    except Exception as e:
        self.logger.error({
            "action": "PIPELINE_PERIODIC_TASK_ERROR",
            "message": f"Unexpected error in ingestion task: {str(e)}",
            "data": {"error": str(e), "error_type": type(e).__name__, "traceback": traceback.format_exc()}
        })
```

## Configuration

The continuous ingestion pipeline can be configured using the following settings in `config.yaml`:

```yaml
pipelines:
  default:
    batch_size: 100
    schedule:
      interval_minutes: 60  # How often to run the ingestion cycle
```

## Integration with IngestController

The simplified `IngestController` initializes the `IngestOrchestrator`, which in turn initializes the continuous ingestion pipeline:

```python
async def start(self) -> None:
    """
    Start the background ingestion process.
    """
    if self._is_running:
        return
    
    try:
        # Start the ingestion process
        await self._orchestrator.start_ingestion()
        self._is_running = True
    except Exception as e:
        # Handle errors
        raise
```

## Benefits

1. **Separation of Concerns**: Ingestion runs independently from query processing
2. **Background Processing**: Data is continuously ingested without blocking user operations
3. **Resilience**: Errors in one ingestion cycle don't affect subsequent cycles
4. **Configurability**: Interval can be adjusted based on system requirements
5. **Resource Management**: Task-based approach allows for clean cancellation and shutdown

## Testing

To test the continuous ingestion pipeline:

1. Configure a short interval (e.g., 1 minute) in the configuration file
2. Start the ingestion service using the ICI controller
3. Monitor logs to confirm that ingestion cycles are running at the expected intervals
4. Verify that errors in individual ingestors don't crash the overall pipeline
5. Check that stopping the service properly cancels the task 