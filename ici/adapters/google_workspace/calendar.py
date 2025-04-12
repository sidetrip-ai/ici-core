"""Handles Google Calendar API interactions."""

import datetime
from typing import Dict, Any

from ici.adapters.google_workspace.auth import get_service


async def create_calendar_event_from_meeting(meeting_details: Dict[str, Any], create_meet: bool = False) -> Dict[str, Any]:
    """Creates a calendar event from meeting details with optional Google Meet.

    Args:
        meeting_details: Dictionary containing meeting information
        create_meet: Whether to create a Google Meet link (default: False)

    Returns:
        Dict containing event details and optional Google Meet link
    """
    try:
        service = get_service('calendar', 'v3')

        # Convert string times to datetime objects
        # Ensure time strings are handled correctly (e.g., ISO format with timezone)
        try:
            start_time = datetime.datetime.fromisoformat(meeting_details['Start_time'].replace('Z', '+00:00'))
            end_time = datetime.datetime.fromisoformat(meeting_details['End_time'].replace('Z', '+00:00'))
        except ValueError as ve:
            print(f"Error parsing datetime string: {ve}. Ensure format is ISO (e.g., YYYY-MM-DDTHH:MM:SS+00:00)")
            raise

        # Create attendees list
        attendees = []
        if meeting_details.get('Participants'):
            # Split participants string into list and clean up
            participants = [p.strip() for p in meeting_details['Participants'].split(',')]
            attendees = [{'email': p} for p in participants if '@' in p]

        event = {
            'summary': meeting_details.get('Agenda', 'Meeting'), # Provide default agenda
            'description': f"Meeting created by ICI Core\nAgenda: {meeting_details.get('Agenda')}",
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'UTC', # Assuming UTC, adjust if necessary
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC', # Assuming UTC, adjust if necessary
            }
        }

        # Only add conference data if Google Meet is requested
        if create_meet:
            event['conferenceData'] = {
                'createRequest': {
                    'requestId': 'random-string-' + str(datetime.datetime.now().timestamp()), # Use a more robust random string
                    'conferenceSolutionKey': {
                        'type': 'hangoutsMeet'
                    }
                }
            }

        if attendees:
            event['attendees'] = attendees

        created_event = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1 if create_meet else 0,
            sendUpdates='all'
        ).execute()

        # Extract Meet link only if it was created
        meet_link = ''
        if create_meet and 'conferenceData' in created_event:
            entry_points = created_event['conferenceData'].get('entryPoints', [])
            if entry_points:
                meet_link = entry_points[0].get('uri', '')

        return {
            'success': True,
            'event_link': created_event.get('htmlLink'),
            'meet_link': meet_link,
            'event_id': created_event.get('id')
        }

    except Exception as e:
        print(f"Error creating calendar event: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        } 