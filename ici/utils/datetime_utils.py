"""
Datetime utilities for the ICI framework.

This module provides standardized datetime handling functions to ensure
consistent timezone handling throughout the application.
"""

from datetime import datetime, timezone
from typing import Optional, Union


def ensure_tz_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Ensure a datetime is timezone-aware (UTC if naive).
    
    Args:
        dt: The datetime to process, can be None
        
    Returns:
        The timezone-aware datetime (or None if input was None)
    """
    if dt is None:
        return None
        
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Convert a datetime to UTC.
    
    Args:
        dt: The datetime to convert, can be None
        
    Returns:
        The UTC datetime (or None if input was None)
    """
    if dt is None:
        return None
        
    # First ensure it's timezone-aware
    dt = ensure_tz_aware(dt)
    
    # Then convert to UTC if it's not already
    if dt.tzinfo != timezone.utc:
        return dt.astimezone(timezone.utc)
    return dt


def from_timestamp(timestamp: Union[int, float]) -> datetime:
    """
    Create a timezone-aware UTC datetime from a timestamp.
    
    Args:
        timestamp: Unix timestamp (seconds since epoch)
        
    Returns:
        Timezone-aware datetime in UTC
    """
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def from_isoformat(iso_string: str) -> datetime:
    """
    Create a timezone-aware datetime from an ISO format string.
    
    If the string has no timezone info, UTC is assumed.
    
    Args:
        iso_string: ISO 8601 formatted datetime string
        
    Returns:
        Timezone-aware datetime
    """
    dt = datetime.fromisoformat(iso_string)
    return ensure_tz_aware(dt)


def safe_compare(dt1: Optional[datetime], dt2: Optional[datetime]) -> bool:
    """
    Safely compare two datetimes that may have different timezone information.
    
    Args:
        dt1: First datetime (may be None)
        dt2: Second datetime (may be None)
        
    Returns:
        True if dt1 is less than dt2, False otherwise
        If either is None, returns False
    """
    if dt1 is None or dt2 is None:
        return False
        
    # Ensure both datetimes are timezone-aware before comparison
    dt1 = ensure_tz_aware(dt1)
    dt2 = ensure_tz_aware(dt2)
    
    return dt1 < dt2 