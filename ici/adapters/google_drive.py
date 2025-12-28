import os
import tempfile
from pathlib import Path
from typing import List, Optional, Dict, Any
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

class GoogleDriveAdapter:
    """Adapter for interacting with Google Drive."""
    
    # If modifying these scopes, delete the token.json file.
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    def __init__(self, credentials_path: str = 'credentials.json', token_path: str = 'token.json'):
        """
        Initialize the Google Drive adapter.
        
        Args:
            credentials_path: Path to the credentials.json file
            token_path: Path to save/load the token.json file
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.creds = self._get_credentials()
        self.service = build('drive', 'v3', credentials=self.creds)
        
    def _get_credentials(self) -> Credentials:
        """Get or refresh credentials."""
        creds = None
        
        # Load existing token if it exists
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
        
        # If no valid credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        return creds
    
    def list_files(self, file_types: Optional[List[str]] = None, 
                   folder_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List files in Google Drive.
        
        Args:
            file_types: List of file extensions to filter (e.g., ['.pdf', '.txt'])
            folder_id: Optional folder ID to search in
            
        Returns:
            List of file metadata
        """
        query_parts = []
        
        # Filter by file types if specified
        if file_types:
            type_queries = []
            for ext in file_types:
                ext = ext.lower()
                if ext == '.txt':
                    type_queries.append("mimeType='text/plain'")
                elif ext == '.pdf':
                    type_queries.append("mimeType='application/pdf'")
                elif ext == '.docx':
                    type_queries.append("mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'")
            if type_queries:
                query_parts.append(f"({' or '.join(type_queries)})")
        
        # Filter by folder if specified
        if folder_id:
            query_parts.append(f"'{folder_id}' in parents")
        
        # Combine query parts
        query = ' and '.join(query_parts) if query_parts else None
        
        # List files
        results = []
        page_token = None
        while True:
            try:
                # Call the Drive v3 API
                response = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name, mimeType)',
                    pageToken=page_token
                ).execute()
                
                results.extend(response.get('files', []))
                page_token = response.get('nextPageToken')
                
                if not page_token:
                    break
                    
            except Exception as e:
                print(f'An error occurred: {e}')
                break
        
        return results
    
    def download_file(self, file_id: str, file_name: str) -> Optional[Path]:
        """
        Download a file from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            file_name: Name to save the file as
            
        Returns:
            Path to the downloaded file, or None if download failed
        """
        try:
            # Create a temporary directory to store downloaded files
            temp_dir = Path(tempfile.gettempdir()) / 'gdrive_downloads'
            temp_dir.mkdir(exist_ok=True)
            
            # Create request to download file
            request = self.service.files().get_media(fileId=file_id)
            
            # Download the file
            file_path = temp_dir / file_name
            with open(file_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            
            return file_path
            
        except Exception as e:
            print(f'An error occurred while downloading {file_name}: {e}')
            return None
    
    def process_files(self, file_types: Optional[List[str]] = None, 
                     folder_id: Optional[str] = None) -> List[Path]:
        """
        List and download files from Google Drive.
        
        Args:
            file_types: List of file extensions to filter
            folder_id: Optional folder ID to search in
            
        Returns:
            List of paths to downloaded files
        """
        # List files
        files = self.list_files(file_types, folder_id)
        
        # Download files
        downloaded_files = []
        for file in files:
            file_path = self.download_file(file['id'], file['name'])
            if file_path:
                downloaded_files.append(file_path)
        
        return downloaded_files 