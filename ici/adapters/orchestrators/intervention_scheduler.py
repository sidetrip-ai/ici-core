
import time
import threading
import logging
import schedule
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class InterventionScheduler:
    """Schedules and manages therapeutic interventions and check-ins."""
    
    def __init__(self):
        """Initialize the intervention scheduler."""
        self.scheduled_interventions = {}  # user_id -> list of intervention details
        self.recurring_jobs = {}  # job_id -> job details
        self.scheduler_thread = None
        self.is_running = False
        self.callback = None
        logger.info("InterventionScheduler initialized")
    
    def start(self, callback: Callable[[str, str], None]):
        """
        Start the scheduler in a background thread.
        
        Args:
            callback: Function to call when an intervention is triggered (user_id, message)
        """
        if self.scheduler_thread and self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.callback = callback
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Intervention scheduler started")
    
    def stop(self):
        """Stop the scheduler thread."""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=1.0)
            self.scheduler_thread = None
        logger.info("Intervention scheduler stopped")
    
    def _run_scheduler(self):
        """Run the scheduler loop in a background thread."""
        while self.is_running:
            schedule.run_pending()
            time.sleep(1)
    
    def schedule_intervention(self, user_id: str, interval_minutes: int, 
                               message: str, intervention_type: str = "check_in"):
        """
        Schedule a one-time intervention for a user.
        
        Args:
            user_id: Unique identifier for the user
            interval_minutes: Minutes to wait before intervention
            message: Message to send for the intervention
            intervention_type: Type of intervention (check_in, crisis_follow_up, etc.)
            
        Returns:
            The ID of the scheduled intervention
        """
        # Create a unique job ID for this intervention
        intervention_id = f"{user_id}_{intervention_type}_{int(time.time())}"
        
        # Calculate intervention time
        intervention_time = datetime.now() + timedelta(minutes=interval_minutes)
        
        # Store intervention details
        if user_id not in self.scheduled_interventions:
            self.scheduled_interventions[user_id] = []
        
        self.scheduled_interventions[user_id].append({
            "id": intervention_id,
            "type": intervention_type,
            "scheduled_time": intervention_time,
            "message": message,
            "is_recurring": False
        })
        
        # Schedule the job
        schedule.every(interval_minutes).minutes.do(
            self._trigger_intervention, 
            user_id=user_id, 
            intervention_id=intervention_id
        ).tag(intervention_id)
        
        logger.info(f"Scheduled one-time {intervention_type} for user {user_id} in {interval_minutes} minutes")
        return intervention_id
    
    def schedule_recurring_job(self, user_id: str, minutes: int, 
                             message: str, job_type: str = "periodic_check"):
        """
        Schedule a recurring job that runs at regular intervals.
        
        Args:
            user_id: Unique identifier for the user
            minutes: Minutes between each job execution
            message: Message to send for the recurring job
            job_type: Type of job (periodic_check, mood_tracker, etc.)
            
        Returns:
            The ID of the scheduled recurring job
        """
        # Create a unique job ID for this recurring job
        job_id = f"{user_id}_{job_type}_recurring_{int(time.time())}"
        
        # Store job details
        if user_id not in self.scheduled_interventions:
            self.scheduled_interventions[user_id] = []
        
        # Create a job record
        job_record = {
            "id": job_id,
            "type": job_type,
            "interval_minutes": minutes,
            "scheduled_time": "recurring every {} minutes".format(minutes),
            "message": message,
            "is_recurring": True,
            "user_id": user_id,
            "last_run": None
        }
        
        # Add to both user records and global job registry
        self.scheduled_interventions[user_id].append(job_record)
        self.recurring_jobs[job_id] = job_record
        
        # Schedule the job
        if minutes == 10:  # Special case for 10 minutes (most common)
            scheduled_job = schedule.every(10).minutes.do(
                self._trigger_recurring_job, 
                job_id=job_id
            )
        else:
            scheduled_job = schedule.every(minutes).minutes.do(
                self._trigger_recurring_job, 
                job_id=job_id
            )
        
        # Tag the job with its ID for reference
        scheduled_job.tag(job_id)
        
        logger.info(f"Scheduled recurring {job_type} for user {user_id} every {minutes} minutes")
        return job_id
    
    def schedule_daily_job(self, user_id: str, hour: int, minute: int,
                            message: str, job_type: str = "daily_check"):
        """
        Schedule a job that runs at a specific time each day.
        
        Args:
            user_id: Unique identifier for the user
            hour: Hour of the day (0-23)
            minute: Minute of the hour (0-59)
            message: Message to send for the daily job
            job_type: Type of job (daily_check, summary, etc.)
            
        Returns:
            The ID of the scheduled daily job
        """
        # Create a unique job ID for this daily job
        job_id = f"{user_id}_{job_type}_daily_{int(time.time())}"
        
        # Format time for display
        time_str = f"{hour:02d}:{minute:02d}"
        
        # Store job details
        if user_id not in self.scheduled_interventions:
            self.scheduled_interventions[user_id] = []
        
        # Create a job record
        job_record = {
            "id": job_id,
            "type": job_type,
            "scheduled_time": f"daily at {time_str}",
            "hour": hour,
            "minute": minute,
            "message": message,
            "is_recurring": True,
            "user_id": user_id,
            "last_run": None
        }
        
        # Add to both user records and global job registry
        self.scheduled_interventions[user_id].append(job_record)
        self.recurring_jobs[job_id] = job_record
        
        # Schedule the job
        scheduled_job = schedule.every().day.at(time_str).do(
            self._trigger_recurring_job, 
            job_id=job_id
        )
        
        # Tag the job with its ID for reference
        scheduled_job.tag(job_id)
        
        logger.info(f"Scheduled daily {job_type} for user {user_id} at {time_str}")
        return job_id
    
    def _trigger_intervention(self, user_id: str, intervention_id: str):
        """
        Trigger a one-time intervention when its time arrives.
        
        Args:
            user_id: Unique identifier for the user
            intervention_id: Unique identifier for the intervention
        """
        # Find the intervention details
        intervention = None
        for item in self.scheduled_interventions.get(user_id, []):
            if item["id"] == intervention_id:
                intervention = item
                break
        
        if not intervention:
            logger.warning(f"Intervention {intervention_id} not found for user {user_id}")
            # Clean up the schedule just in case
            schedule.clear(intervention_id)
            return schedule.CancelJob
        
        # Execute the callback with the intervention message
        if self.callback:
            try:
                self.callback(user_id, intervention["message"])
                logger.info(f"Triggered one-time {intervention['type']} for user {user_id}")
            except Exception as e:
                logger.error(f"Error triggering intervention: {e}")
        
        # Remove the intervention from our records
        if user_id in self.scheduled_interventions:
            self.scheduled_interventions[user_id] = [
                item for item in self.scheduled_interventions[user_id] 
                if item["id"] != intervention_id
            ]
        
        # Clear the scheduled job
        schedule.clear(intervention_id)
        
        return schedule.CancelJob
    
    def _trigger_recurring_job(self, job_id: str):
        """
        Trigger a recurring job when its time arrives.
        
        Args:
            job_id: Unique identifier for the job
        """
        # Get job details from our registry
        if job_id not in self.recurring_jobs:
            logger.warning(f"Recurring job {job_id} not found in registry")
            # Clean up the schedule
            schedule.clear(job_id)
            return schedule.CancelJob
        
        job = self.recurring_jobs[job_id]
        user_id = job["user_id"]
        
        # Update last run time
        job["last_run"] = datetime.now()
        
        # Execute the callback with the job message
        if self.callback:
            try:
                self.callback(user_id, job["message"])
                logger.info(f"Triggered recurring {job['type']} for user {user_id}")
            except Exception as e:
                logger.error(f"Error triggering recurring job {job_id}: {e}")
        
        # For recurring jobs, we return None to keep them scheduled
        return None
    
    def cancel_intervention(self, intervention_id: str) -> bool:
        """
        Cancel a specific intervention by ID.
        
        Args:
            intervention_id: ID of the intervention to cancel
            
        Returns:
            True if canceled successfully, False otherwise
        """
        # Look for the intervention in all users
        for user_id, interventions in self.scheduled_interventions.items():
            for intervention in interventions:
                if intervention["id"] == intervention_id:
                    # Remove from scheduler
                    schedule.clear(intervention_id)
                    
                    # Remove from our records
                    self.scheduled_interventions[user_id] = [
                        item for item in self.scheduled_interventions[user_id] 
                        if item["id"] != intervention_id
                    ]
                    
                    # If it's a recurring job, also remove from job registry
                    if intervention.get("is_recurring", False) and intervention_id in self.recurring_jobs:
                        del self.recurring_jobs[intervention_id]
                    
                    logger.info(f"Cancelled intervention {intervention_id} for user {user_id}")
                    return True
        
        logger.warning(f"Intervention {intervention_id} not found for cancellation")
        return False
    
    def cancel_interventions(self, user_id: Optional[str] = None, 
                             intervention_type: Optional[str] = None,
                             recurring_only: bool = False) -> int:
        """
        Cancel scheduled interventions, optionally filtered by user and type.
        
        Args:
            user_id: Optional user ID to filter cancellations
            intervention_type: Optional intervention type to filter cancellations
            recurring_only: If True, only cancel recurring jobs
            
        Returns:
            Number of interventions cancelled
        """
        cancelled_count = 0
        
        # If user_id specified, only check that user's interventions
        users_to_check = [user_id] if user_id else list(self.scheduled_interventions.keys())
        
        for uid in users_to_check:
            if uid not in self.scheduled_interventions:
                continue
                
            interventions_to_cancel = []
            for intervention in self.scheduled_interventions[uid]:
                # Apply filters
                if recurring_only and not intervention.get("is_recurring", False):
                    continue
                    
                if intervention_type is not None and intervention["type"] != intervention_type:
                    continue
                
                interventions_to_cancel.append(intervention["id"])
            
            # Remove from scheduler
            for intervention_id in interventions_to_cancel:
                schedule.clear(intervention_id)
                
                # If it's a recurring job, also remove from job registry
                if intervention_id in self.recurring_jobs:
                    del self.recurring_jobs[intervention_id]
                    
                cancelled_count += 1
            
            # Update our records
            if interventions_to_cancel:
                self.scheduled_interventions[uid] = [
                    item for item in self.scheduled_interventions[uid] 
                    if item["id"] not in interventions_to_cancel
                ]
        
        logger.info(f"Cancelled {cancelled_count} interventions")
        return cancelled_count
    
    def get_pending_interventions(self, user_id: Optional[str] = None, 
                                  recurring_only: bool = False) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all pending interventions, optionally filtered by user.
        
        Args:
            user_id: Optional user ID to filter results
            recurring_only: If True, only return recurring jobs
            
        Returns:
            Dictionary mapping user IDs to lists of intervention details
        """
        result = {}
        
        if user_id:
            # Filter by user ID
            interventions = self.scheduled_interventions.get(user_id, [])
            if recurring_only:
                interventions = [i for i in interventions if i.get("is_recurring", False)]
            result[user_id] = interventions
        else:
            # All users
            for uid, interventions in self.scheduled_interventions.items():
                if recurring_only:
                    filtered = [i for i in interventions if i.get("is_recurring", False)]
                    if filtered:
                        result[uid] = filtered
                else:
                    result[uid] = interventions
        
        return result

