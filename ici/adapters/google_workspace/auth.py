"""Handles Google API authentication and service creation."""

import os
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/tasks'
]

_SERVICES_CACHE = {}
_CREDS_CACHE = None

def _get_credentials():
    """Loads or retrieves Google API credentials."""
    global _CREDS_CACHE
    if _CREDS_CACHE and _CREDS_CACHE.valid:
        return _CREDS_CACHE

    creds = None
    # The file token.pickle stores the user's access and refresh tokens
    token_path = os.environ.get("ICI_GOOGLE_TOKEN_PATH", "token.pickle")
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {str(e)}")
                creds = None

        if not creds:
            try:
                # Path to the client secrets file, configurable via env var
                client_secrets_path_env = os.environ.get("ICI_GOOGLE_CLIENT_SECRETS_PATH")
                if client_secrets_path_env and os.path.exists(client_secrets_path_env):
                     client_secrets_path = client_secrets_path_env
                else:
                    # Fallback path relative to this file
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    # Try finding the secrets file in the workspace root or adapter dir
                    possible_paths = [
                        os.path.join(os.path.dirname(os.path.dirname(base_dir)), 'client_secret.json'), # <root>/client_secret.json
                        os.path.join(base_dir, 'client_secret.json'), # <adapter_dir>/client_secret.json
                        # The old hardcoded path (less ideal)
                        os.path.join(
                            os.path.dirname(os.path.dirname(os.path.dirname(base_dir))),
                            'adapters',
                            'agent',
                            'client_secret_923162412863-2o5pj72jep8avu1a8dh6au77ae8jpgof.apps.googleusercontent.com.json'
                        )
                    ]
                    client_secrets_path = next((p for p in possible_paths if os.path.exists(p)), None)

                if not client_secrets_path:
                    raise FileNotFoundError("Google Client Secrets JSON file not found. "
                                           "Set ICI_GOOGLE_CLIENT_SECRETS_PATH or place 'client_secret.json' "
                                           "in the workspace root or adapter directory.")

                print(f"Using client secrets file: {client_secrets_path}")
                flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                print(f"Error during authentication: {str(e)}")
                raise

        # Save the credentials for the next run
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    _CREDS_CACHE = creds
    return creds

def get_service(service_name: str, version: str):
    """
    Gets an authorized Google API service instance.
    Uses a cache to avoid rebuilding the service object repeatedly.

    Args:
        service_name: The name of the Google API service (e.g., 'calendar', 'gmail').
        version: The version of the API (e.g., 'v3', 'v1').

    Returns:
        The authorized Google API service object.
    """
    global _SERVICES_CACHE
    cache_key = (service_name, version)

    if cache_key in _SERVICES_CACHE:
        return _SERVICES_CACHE[cache_key]

    try:
        creds = _get_credentials()
        service = build(service_name, version, credentials=creds)

        # Test the service if it's Gmail
        if service_name == 'gmail':
             service.users().getProfile(userId='me').execute()

        _SERVICES_CACHE[cache_key] = service
        return service
    except Exception as e:
        print(f"Error creating {service_name} service: {str(e)}")
        # Clear cache if service creation fails
        if cache_key in _SERVICES_CACHE:
            del _SERVICES_CACHE[cache_key]
        raise 