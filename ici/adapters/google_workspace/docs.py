"""Handles Google Docs API interactions."""

import datetime
from typing import Dict, Any, List

from ici.adapters.google_workspace.auth import get_service
from ici.adapters.google_workspace.tasks import create_task # For plan creation


async def create_doc_from_summary(doc_title: str, summary_content: str, sub_heading: str = "Summary") -> Dict[str, Any]:
    """
    Creates a Google Doc with the provided title and summary content.

    Args:
        doc_title: The title for the Google Doc.
        summary_content: The main content/body for the document.
        sub_heading: An optional sub-heading for the summary section.

    Returns:
        Dict containing document details and status
    """
    try:
        docs_service = get_service('docs', 'v1')
        drive_service = get_service('drive', 'v3') # Used implicitly by docs?

        # Create the document
        doc = {
            'title': doc_title
        }
        doc = docs_service.documents().create(body=doc).execute()
        doc_id = doc.get('documentId')

        # Format and insert the content
        # We build the text first and then insert it to simplify index calculation
        generated_on = f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        content_text = f"{doc_title}\n\n{sub_heading}\n{generated_on}{summary_content}"

        requests = [
            {
                'insertText': {
                    'location': {
                        'index': 1 # Start inserting at the beginning
                    },
                    'text': content_text
                }
            },
            {
                'updateTextStyle': { # Format title
                    'range': {
                        'startIndex': 1,
                        'endIndex': len(doc_title) + 1
                    },
                    'textStyle': {
                        'fontSize': {
                            'magnitude': 18,
                            'unit': 'PT'
                        },
                        'bold': True
                    },
                    'fields': 'fontSize,bold'
                }
            },
            {
                'updateTextStyle': { # Format sub-heading
                    'range': {
                        'startIndex': len(doc_title) + 2, # After title and newline
                        'endIndex': len(doc_title) + 2 + len(sub_heading) + 1
                    },
                    'textStyle': {
                        'fontSize': {
                            'magnitude': 14,
                            'unit': 'PT'
                        },
                        'bold': True
                    },
                    'fields': 'fontSize,bold'
                }
            },
        ]

        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()

        # Get the document URL
        doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

        return {
            'success': True,
            'doc_id': doc_id,
            'doc_url': doc_url,
            'title': doc_title
        }

    except Exception as e:
        print(f"Error creating Google Doc: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


async def create_plan_doc(plan_title: str, plan_content: str, extracted_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Creates a Google Doc for the plan and associated Google Tasks.

    Args:
        plan_title: Title for the plan document.
        plan_content: The structured content of the plan.
        extracted_tasks: List of task dictionaries extracted from the plan.

    Returns:
        Dict containing document and task creation status.
    """
    try:
        # Create the plan document first
        doc_result = await create_doc_from_summary(plan_title, plan_content, sub_heading="Plan Details")

        if not doc_result.get('success'):
            return doc_result # Return doc creation error

        created_tasks_info = []
        tasks_created_count = 0
        task_creation_errors = []

        # Create tasks from the extracted list
        for task_details in extracted_tasks:
            try:
                result = await create_task(task_details) # Call the task creation function
                if result.get('success'):
                    created_tasks_info.append(result)
                    tasks_created_count += 1
                else:
                    task_creation_errors.append(result.get('error', 'Unknown task error'))
            except Exception as task_e:
                error_msg = f"Error creating task '{task_details.get('title', 'N/A')}': {str(task_e)}"
                print(error_msg)
                task_creation_errors.append(error_msg)

        doc_result['tasks_created'] = tasks_created_count
        doc_result['tasks'] = created_tasks_info
        if task_creation_errors:
            doc_result['task_errors'] = task_creation_errors

        return doc_result

    except Exception as e:
        print(f"Error creating plan document or tasks: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        } 