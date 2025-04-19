
import json
import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import sqlite3

logger = logging.getLogger(__name__)

class MoodTracker:
    """Tracks and records user moods over time."""
    
    def __init__(self, db_path: str = "ici/db/mood_history.db"):
        """
        Initialize the mood tracker.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()
        logger.info(f"Mood tracker initialized with database at {db_path}")
    
    def _init_database(self) -> None:
        """Initialize the SQLite database for mood tracking."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create mood records table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS mood_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                mood TEXT NOT NULL,
                intensity REAL NOT NULL,
                issue TEXT,
                notes TEXT
            )
            ''')
            
            # Create mood patterns table if it doesn't exist
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS mood_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                dominant_mood TEXT NOT NULL,
                avg_intensity REAL NOT NULL,
                common_issues TEXT,
                detection_date TEXT NOT NULL
            )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Mood tracking database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing mood tracking database: {e}")
            raise
    
    def record_mood(self, user_id: str, mood: str, intensity: float, 
                     issue: Optional[str] = None, notes: Optional[str] = None) -> bool:
        """
        Record a user's mood.
        
        Args:
            user_id: Unique identifier for the user
            mood: The identified mood (e.g., "happy", "sad", "angry")
            intensity: Intensity of the mood (0.0 to 1.0)
            issue: Optional issue associated with the mood
            notes: Optional additional notes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = datetime.now().isoformat()
            
            cursor.execute(
                "INSERT INTO mood_records (user_id, timestamp, mood, intensity, issue, notes) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, timestamp, mood, intensity, issue, notes)
            )
            
            conn.commit()
            conn.close()
            logger.info(f"Recorded mood '{mood}' with intensity {intensity} for user {user_id}")
            
            # Check for patterns after recording
            self._detect_patterns(user_id)
            
            return True
        except Exception as e:
            logger.error(f"Error recording mood for user {user_id}: {e}")
            return False
    
    def get_mood_history(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Get mood history for a user over the specified number of days.
        
        Args:
            user_id: Unique identifier for the user
            days: Number of days of history to retrieve
            
        Returns:
            Dictionary containing mood history information
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            cursor = conn.cursor()
            
            # Calculate the start date
            start_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get mood records
            cursor.execute(
                "SELECT * FROM mood_records WHERE user_id = ? AND timestamp >= ? ORDER BY timestamp ASC",
                (user_id, start_date)
            )
            
            mood_records = [dict(row) for row in cursor.fetchall()]
            
            # Get mood patterns
            cursor.execute(
                "SELECT * FROM mood_patterns WHERE user_id = ? AND end_date >= ? ORDER BY detection_date DESC",
                (user_id, start_date)
            )
            
            mood_patterns = [dict(row) for row in cursor.fetchall()]
            
            # Calculate mood distribution
            mood_distribution = {}
            for record in mood_records:
                mood = record["mood"]
                if mood in mood_distribution:
                    mood_distribution[mood] += 1
                else:
                    mood_distribution[mood] = 1
            
            # Calculate average intensity
            avg_intensity = 0.0
            if mood_records:
                avg_intensity = sum(record["intensity"] for record in mood_records) / len(mood_records)
            
            # Calculate common issues
            issue_counts = {}
            for record in mood_records:
                issue = record.get("issue")
                if issue:
                    if issue in issue_counts:
                        issue_counts[issue] += 1
                    else:
                        issue_counts[issue] = 1
            
            # Sort issues by frequency
            common_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
            common_issues = [issue for issue, count in common_issues[:3]]  # Top 3 issues
            
            conn.close()
            
            return {
                "user_id": user_id,
                "period_days": days,
                "start_date": start_date,
                "end_date": datetime.now().isoformat(),
                "records": mood_records,
                "patterns": mood_patterns,
                "distribution": mood_distribution,
                "avg_intensity": avg_intensity,
                "common_issues": common_issues,
                "record_count": len(mood_records)
            }
        except Exception as e:
            logger.error(f"Error retrieving mood history for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "period_days": days,
                "error": str(e),
                "records": [],
                "patterns": [],
                "distribution": {},
                "avg_intensity": 0.0,
                "common_issues": [],
                "record_count": 0
            }
    
    def _detect_patterns(self, user_id: str) -> None:
        """
        Detect mood patterns for a user and record them.
        
        Args:
            user_id: Unique identifier for the user
        """
        try:
            # Get user's recent mood history (last 30 days)
            history = self.get_mood_history(user_id, days=30)
            records = history.get("records", [])
            
            if len(records) < 5:
                # Not enough data to detect patterns
                return
            
            # Check for consistent negative moods (3+ days)
            self._detect_consistent_mood_pattern(user_id, records, ["sad", "angry", "anxious"], "consistent_negative", 3)
            
            # Check for mood swings (high variance in intensity over 5+ days)
            self._detect_mood_swing_pattern(user_id, records, 5)
            
            # Check for issue-specific patterns
            self._detect_issue_specific_patterns(user_id, records)
            
        except Exception as e:
            logger.error(f"Error detecting mood patterns for user {user_id}: {e}")
    
    def _detect_consistent_mood_pattern(self, user_id: str, records: List[Dict[str, Any]], 
                                         mood_types: List[str], pattern_type: str, 
                                         min_days: int) -> None:
        """
        Detect consistent mood patterns.
        
        Args:
            user_id: Unique identifier for the user
            records: List of mood records
            mood_types: List of mood types to look for
            pattern_type: Type of pattern to record
            min_days: Minimum number of days required for pattern
        """
        # Group records by day
        daily_moods = {}
        for record in records:
            date = datetime.fromisoformat(record["timestamp"]).date().isoformat()
            if date not in daily_moods:
                daily_moods[date] = []
            daily_moods[date].append(record)
        
        # Check for consecutive days with the specified moods
        dates = sorted(daily_moods.keys())
        consecutive_days = 0
        start_date = None
        current_moods = []
        
        for date in dates:
            day_records = daily_moods[date]
            day_moods = [record["mood"] for record in day_records]
            
            # Check if any of the specified moods are present for this day
            if any(mood in mood_types for mood in day_moods):
                if consecutive_days == 0:
                    start_date = date
                consecutive_days += 1
                current_moods.extend([m for m in day_moods if m in mood_types])
            else:
                # Pattern broken, check if we had enough consecutive days
                if consecutive_days >= min_days:
                    self._record_pattern(
                        user_id, 
                        pattern_type, 
                        start_date, 
                        dates[dates.index(date) - 1],  # End date is previous day
                        self._most_common(current_moods),
                        sum(record["intensity"] for record in records if record["mood"] in mood_types) / len([r for r in records if r["mood"] in mood_types]),
                        self._most_common([record["issue"] for record in records if record["mood"] in mood_types and record["issue"]])
                    )
                
                # Reset counters
                consecutive_days = 0
                start_date = None
                current_moods = []
        
        # Check for pattern at the end of the records
        if consecutive_days >= min_days:
            self._record_pattern(
                user_id, 
                pattern_type, 
                start_date, 
                dates[-1],  # End date is last day
                self._most_common(current_moods),
                sum(record["intensity"] for record in records if record["mood"] in mood_types) / len([r for r in records if r["mood"] in mood_types]),
                self._most_common([record["issue"] for record in records if record["mood"] in mood_types and record["issue"]])
            )
    
    def _detect_mood_swing_pattern(self, user_id: str, records: List[Dict[str, Any]], min_days: int) -> None:
        """
        Detect mood swing patterns (high variance in intensity).
        
        Args:
            user_id: Unique identifier for the user
            records: List of mood records
            min_days: Minimum number of days required for pattern
        """
        # Group records by day
        daily_moods = {}
        for record in records:
            date = datetime.fromisoformat(record["timestamp"]).date().isoformat()
            if date not in daily_moods:
                daily_moods[date] = []
            daily_moods[date].append(record)
        
        dates = sorted(daily_moods.keys())
        if len(dates) < min_days:
            return
        
        # Calculate daily average intensities
        daily_intensities = {}
        for date in dates:
            day_records = daily_moods[date]
            daily_intensities[date] = sum(record["intensity"] for record in day_records) / len(day_records)
        
        # Check for high variance in rolling windows
        for i in range(len(dates) - min_days + 1):
            window_dates = dates[i:i+min_days]
            window_intensities = [daily_intensities[date] for date in window_dates]
            
            # Calculate variance
            mean_intensity = sum(window_intensities) / len(window_intensities)
            variance = sum((x - mean_intensity) ** 2 for x in window_intensities) / len(window_intensities)
            
            # If variance is high, record a mood swing pattern
            if variance > 0.1:  # Threshold for significant variance
                # Identify dominant moods in this window
                window_moods = []
                for date in window_dates:
                    window_moods.extend([record["mood"] for record in daily_moods[date]])
                
                dominant_mood = self._most_common(window_moods)
                
                # Get issues from this window
                window_issues = []
                for date in window_dates:
                    window_issues.extend([record["issue"] for record in daily_moods[date] if record["issue"]])
                
                common_issues = self._most_common(window_issues)
                
                self._record_pattern(
                    user_id,
                    "mood_swings",
                    window_dates[0],
                    window_dates[-1],
                    dominant_mood,
                    mean_intensity,
                    common_issues
                )
                
                # Skip overlapping windows to avoid duplicate patterns
                i += min_days - 1
    
    def _detect_issue_specific_patterns(self, user_id: str, records: List[Dict[str, Any]]) -> None:
        """
        Detect patterns related to specific issues.
        
        Args:
            user_id: Unique identifier for the user
            records: List of mood records
        """
        # Group records by issue
        issue_records = {}
        for record in records:
            issue = record.get("issue")
            if issue:
                if issue not in issue_records:
                    issue_records[issue] = []
                issue_records[issue].append(record)
        
        # Analyze each issue with sufficient data
        for issue, issue_data in issue_records.items():
            if len(issue_data) < 3:
                continue
            
            # Calculate average intensity for this issue
            avg_intensity = sum(record["intensity"] for record in issue_data) / len(issue_data)
            
            # Get the most common mood for this issue
            issue_moods = [record["mood"] for record in issue_data]
            dominant_mood = self._most_common(issue_moods)
            
            # Get date range
            timestamps = [datetime.fromisoformat(record["timestamp"]) for record in issue_data]
            start_date = min(timestamps).date().isoformat()
            end_date = max(timestamps).date().isoformat()
            
            # Record the pattern if intensity is high enough
            if avg_intensity > 0.6:  # Threshold for significant intensity
                self._record_pattern(
                    user_id,
                    "issue_specific",
                    start_date,
                    end_date,
                    dominant_mood,
                    avg_intensity,
                    issue
                )
    
    def _record_pattern(self, user_id: str, pattern_type: str, start_date: str, 
                         end_date: str, dominant_mood: str, avg_intensity: float, 
                         common_issues: Optional[str] = None) -> None:
        """
        Record a detected mood pattern.
        
        Args:
            user_id: Unique identifier for the user
            pattern_type: Type of pattern detected
            start_date: Start date of the pattern
            end_date: End date of the pattern
            dominant_mood: Dominant mood in the pattern
            avg_intensity: Average intensity of moods in the pattern
            common_issues: Common issues associated with the pattern
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if a similar pattern already exists
            cursor.execute(
                """
                SELECT id FROM mood_patterns 
                WHERE user_id = ? AND pattern_type = ? AND dominant_mood = ? 
                AND start_date >= ? AND end_date <= ?
                ORDER BY detection_date DESC
                LIMIT 1
                """,
                (user_id, pattern_type, dominant_mood, 
                 (datetime.fromisoformat(start_date) - timedelta(days=3)).isoformat(), 
                 (datetime.fromisoformat(end_date) + timedelta(days=3)).isoformat())
            )
            
            existing_pattern = cursor.fetchone()
            
            if existing_pattern:
                # Update existing pattern
                cursor.execute(
                    """
                    UPDATE mood_patterns 
                    SET end_date = ?, avg_intensity = ?, common_issues = ?, detection_date = ?
                    WHERE id = ?
                    """,
                    (end_date, avg_intensity, common_issues, datetime.now().isoformat(), existing_pattern[0])
                )
            else:
                # Insert new pattern
                cursor.execute(
                    """
                    INSERT INTO mood_patterns 
                    (user_id, pattern_type, start_date, end_date, dominant_mood, avg_intensity, common_issues, detection_date) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, pattern_type, start_date, end_date, dominant_mood, avg_intensity, 
                     common_issues, datetime.now().isoformat())
                )
            
            conn.commit()
            conn.close()
            logger.info(f"Recorded {pattern_type} pattern for user {user_id} from {start_date} to {end_date}")
        except Exception as e:
            logger.error(f"Error recording mood pattern for user {user_id}: {e}")
    
    def _most_common(self, items: List[Any]) -> Optional[Any]:
        """
        Find the most common item in a list.
        
        Args:
            items: List of items
            
        Returns:
            The most common item, or None if the list is empty
        """
        if not items:
            return None
        
        # Filter out None values
        items = [item for item in items if item is not None]
        if not items:
            return None
        
        # Count occurrences
        counts = {}
        for item in items:
            counts[item] = counts.get(item, 0) + 1
        
        # Find most common
        return max(counts.items(), key=lambda x: x[1])[0]

# Example usage
if __name__ == "__main__":
    tracker = MoodTracker()
    
    # Record some test moods
    tracker.record_mood("test_user", "happy", 0.8, "job_success", "Got a promotion at work")
    tracker.record_mood("test_user", "anxious", 0.6, "deadline", "Project due soon")
    
    # Get mood history
    history = tracker.get_mood_history("test_user")
    print(f"Mood history for test_user: {len(history['records'])} records")
    print(f"Average intensity: {history['avg_intensity']}")
    print(f"Common issues: {history['common_issues']}")