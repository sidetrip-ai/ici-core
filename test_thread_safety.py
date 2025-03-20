#!/usr/bin/env python
"""
Simple test script for verifying StateManager thread safety.
"""

import os
import time
import threading
import logging
from concurrent.futures import ThreadPoolExecutor

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("thread_safety_test")

# Import the StateManager
from ici.utils.state_manager import StateManager

def test_state_manager_thread(thread_id, db_path):
    """Test function that runs in a separate thread"""
    try:
        logger.info(f"Thread {thread_id} starting")
        
        # Initialize a state manager in this thread
        state_manager = StateManager(db_path=db_path, logger_name=f"test_thread_{thread_id}")
        state_manager.initialize()
        
        # Test set_state
        state_manager.set_state(
            ingestor_id=f"test_ingestor_{thread_id}",
            last_timestamp=int(time.time()),
            additional_metadata={"thread_id": thread_id, "test_value": f"Value from thread {thread_id}"}
        )
        
        # Wait a bit
        time.sleep(0.5)
        
        # Test get_state
        state = state_manager.get_state(f"test_ingestor_{thread_id}")
        logger.info(f"Thread {thread_id} got state: {state}")
        
        # List ingestors
        ingestors = state_manager.list_ingestors()
        logger.info(f"Thread {thread_id} ingestors: {ingestors}")
        
        # Close connection
        state_manager.close()
        logger.info(f"Thread {thread_id} finished successfully")
        return True
    except Exception as e:
        logger.error(f"Thread {thread_id} error: {str(e)}")
        return False

def main():
    """Main function to run the thread safety test"""
    # Ensure ICI_CONFIG_PATH is set
    if not os.environ.get("ICI_CONFIG_PATH"):
        os.environ["ICI_CONFIG_PATH"] = os.path.join(os.getcwd(), "config.yaml")
    
    # Use a test database path
    db_path = "test_thread_safety.db"
    
    # Number of threads to test with
    num_threads = 5
    
    logger.info(f"Starting thread safety test with {num_threads} threads")
    
    # Run threads in a thread pool
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(test_state_manager_thread, i, db_path) for i in range(num_threads)]
        
        # Wait for all threads to complete
        results = [future.result() for future in futures]
        
    # Check results
    success_count = sum(1 for result in results if result)
    logger.info(f"Test completed: {success_count}/{num_threads} threads succeeded")
    
    if success_count == num_threads:
        logger.info("SUCCESS: StateManager appears to be thread-safe!")
    else:
        logger.error(f"FAILURE: {num_threads - success_count} threads encountered errors")

if __name__ == "__main__":
    main() 