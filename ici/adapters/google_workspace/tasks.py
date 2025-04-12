"""Handles Google Tasks API interactions."""

import json
from typing import Dict, Any

from ici.adapters.google_workspace.auth import get_service


async def create_task(task_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a Google Task from the provided details.

    Args:
        task_details: Dictionary containing task information
                      (title, notes, due, priority).

    Returns:
        Dict containing task details and status
    """
    try:
        # Validate required fields
        if 'title' not in task_details or not task_details['title']:
            return {
                'success': False,
                'error': 'Missing required task title'
            }

        # Get Tasks service
        service = get_service('tasks', 'v1')

        # Get the default task list (or allow configuration)
        # For simplicity, using the first task list
        try:
            tasklists = service.tasklists().list().execute()
            if not tasklists.get('items'):
                # Handle case where user has no task lists (optional: create one)
                return {
                    'success': False,
                    'error': 'No Google Task lists found for the user.'
                }
            tasklist_id = tasklists['items'][0]['id']
        except Exception as list_e:
            print(f"Error fetching task lists: {list_e}")
            return {
                'success': False,
                'error': f'Could not retrieve Google Task lists: {str(list_e)}'
            }


        # Prepare the task body
        task_body = {
            'title': task_details['title'],
            'notes': task_details.get('notes', ''),
            'status': 'needsAction' # Default status
        }

        # Add optional fields if present
        if task_details.get('due'):
            # Ensure due date is in RFC3339 format (YYYY-MM-DDTHH:MM:SSZ)
            # Add validation or conversion if needed
            task_body['due'] = task_details['due']

        # Google Tasks API does not directly support priority number 1-5.
        # Priority is handled via ordering or potentially using custom fields if needed.
        # We'll store the requested priority in the notes or ignore it for now.
        if task_details.get('priority'):
            priority = task_details['priority']
            task_body['notes'] += f"\n(Priority: {priority})" # Add priority to notes


        # Create the task
        result = service.tasks().insert(
            tasklist=tasklist_id,
            body=task_body
        ).execute()

        # Return success information including fields used
        return {
            'success': True,
            'task_id': result['id'],
            'title': task_details['title'],
            'notes': task_body['notes'], # Return notes possibly updated with priority
            'due': task_details.get('due'),
            'priority_requested': task_details.get('priority') # Indicate the requested priority
        }

    except Exception as e:
        print(f"Error creating Google Task: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        } 