"""Handles Google Gmail API interactions."""

import json
import base64
from email.mime.text import MIMEText
from typing import Dict, Any, List

from ici.adapters.google_workspace.auth import get_service


async def create_email_draft(email_details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a Gmail draft based on the provided details.

    Args:
        email_details: Dictionary containing email information
                       (To, Subject, Body, Cc, Bcc).

    Returns:
        Dict containing draft details and status
    """
    try:
        # Validate required fields
        if not all(field in email_details for field in ['To', 'Subject', 'Body']):
            return {
                'success': False,
                'error': 'Missing required email fields: To, Subject, Body'
            }

        # Create the email message
        message = MIMEText(email_details['Body'])
        message['to'] = email_details['To']
        message['subject'] = email_details['Subject']

        if email_details.get('Cc') and isinstance(email_details['Cc'], list):
            message['cc'] = ', '.join(email_details['Cc'])
        if email_details.get('Bcc') and isinstance(email_details['Bcc'], list):
            message['bcc'] = ', '.join(email_details['Bcc'])

        # Create the raw email message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Get Gmail service
        service = get_service('gmail', 'v1')

        # Create the draft
        draft = service.users().drafts().create(
            userId='me',
            body={'message': {'raw': raw_message}}
        ).execute()

        return {
            'success': True,
            'draft_id': draft['id'],
            'message_id': draft['message']['id'],
            'to': email_details['To'],
            'subject': email_details['Subject']
        }

    except Exception as e:
        print(f"Error creating email draft: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        } 