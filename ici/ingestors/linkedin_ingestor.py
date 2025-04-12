from datetime import datetime
from typing import Any, Dict, List, Optional
from ..core.ingestor import Ingestor
import requests
import logging
import os
from urllib.parse import urlencode
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
import time
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

class OAuth2CallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth2 callback from LinkedIn."""
    code = None
    error = None
    
    def do_GET(self):
        """Handle GET request with authorization code."""
        try:
            print(f"\nReceived callback with path: {self.path}")
            
            if 'error=' in self.path:
                OAuth2CallbackHandler.error = self.path.split('error=')[1].split('&')[0]
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                error_msg = f"Authorization failed: {OAuth2CallbackHandler.error}"
                self.wfile.write(error_msg.encode())
                print(f"Error in callback: {OAuth2CallbackHandler.error}")
                return
                
            if 'code=' in self.path:
                OAuth2CallbackHandler.code = self.path.split('code=')[1].split('&')[0]
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                success_html = """
                <html>
                <body style="text-align: center; font-family: Arial, sans-serif; padding: 20px;">
                    <h2 style="color: #0077B5;">LinkedIn Authorization Successful!</h2>
                    <p>You can close this window and return to the application.</p>
                </body>
                </html>
                """
                self.wfile.write(success_html.encode())
                print("Successfully received authorization code")
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"No authorization code found in callback")
                print("No authorization code in callback")
        except Exception as e:
            print(f"Error handling callback: {str(e)}")
            self.send_response(500)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

class LinkedInIngestor(Ingestor):
    """LinkedIn data ingestor using official API."""
    
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize LinkedIn ingestor with OAuth2 configuration."""
        super().__init__()
        self.config = config
        self.client_id = os.getenv('LINKEDIN_CLIENT_ID')
        self.client_secret = os.getenv('LINKEDIN_CLIENT_SECRET')
        self.redirect_uri = 'http://localhost:8000/callback'  # Hardcoded to ensure consistency
        self.access_token = None
        
        if not self.client_id or not self.client_secret:
            raise ValueError("LinkedIn client_id and client_secret must be set in environment variables")
        
        self._authenticate()
    
    def _make_request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with retry logic."""
        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.request(method, url, **kwargs)
                
                # Check if we need to retry based on status code
                if response.status_code in [429, 500, 502, 503, 504]:
                    if attempt < self.MAX_RETRIES - 1:
                        wait_time = self.RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                        print(f"Request failed with status {response.status_code}. Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                
                return response
                
            except RequestException as e:
                if attempt < self.MAX_RETRIES - 1:
                    wait_time = self.RETRY_DELAY * (2 ** attempt)
                    print(f"Request failed with error: {str(e)}. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                raise
        
        raise Exception(f"Failed after {self.MAX_RETRIES} attempts")
    
    def _authenticate(self) -> None:
        """Perform OpenID Connect authentication flow with LinkedIn."""
        try:
            print("\n=== LinkedIn Authentication Debug Info ===")
            print(f"Client ID: {self.client_id}")
            print(f"Redirect URI: {self.redirect_uri}")
            print("Starting local server...")
            
            # Reset any previous state
            OAuth2CallbackHandler.code = None
            OAuth2CallbackHandler.error = None
            
            # Start local server to receive callback
            server = HTTPServer(('localhost', 8000), OAuth2CallbackHandler)
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            print("Local server started successfully")
            
            # Construct authorization URL with OpenID Connect scopes
            # Using only the OpenID Connect scopes that are authorized
            auth_params = {
                'response_type': 'code',
                'client_id': self.client_id,
                'redirect_uri': self.redirect_uri,
                'scope': 'openid profile email',  # Only OpenID Connect basic scopes
                'state': self._generate_state_param(),
                'nonce': self._generate_nonce()
            }
            
            auth_url = f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(auth_params)}"
            print("\nAuthorization URL:")
            print(auth_url)
            print("\nOpening browser for authorization...")
            
            webbrowser.open(auth_url)
            
            # Wait for callback with timeout
            timeout = 300  # 5 minutes
            start_time = datetime.now()
            print("Waiting for authorization (timeout in 5 minutes)...")
            
            while not OAuth2CallbackHandler.code and not OAuth2CallbackHandler.error:
                if (datetime.now() - start_time).seconds > timeout:
                    raise Exception("Authentication timeout - no response received within 5 minutes")
                time.sleep(1)
            
            if OAuth2CallbackHandler.error:
                raise Exception(f"LinkedIn authorization failed: {OAuth2CallbackHandler.error}")
            
            print(f"Authorization code received: {OAuth2CallbackHandler.code[:5]}...")
            print("Exchanging code for tokens...")
            
            # Exchange code for tokens (both access token and ID token)
            token_url = 'https://www.linkedin.com/oauth/v2/accessToken'
            token_data = {
                'grant_type': 'authorization_code',
                'code': OAuth2CallbackHandler.code,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'redirect_uri': self.redirect_uri
            }
            
            print("Making token request...")
            response = self._make_request_with_retry('POST', token_url, data=token_data)
            print(f"Token response status: {response.status_code}")
            
            if response.status_code == 200:
                tokens = response.json()
                self.access_token = tokens['access_token']
                # Store id_token if needed for user info
                self.id_token = tokens.get('id_token')
                print("Successfully obtained tokens!")
                logger.info("Successfully authenticated with LinkedIn")
                
                # Test the access token with a basic profile request
                print("\nTesting API access with basic profile request...")
                test_response = self._make_api_request('me')
                print("API test successful!")
                print(f"Connected as: {test_response.get('localizedFirstName', '')} {test_response.get('localizedLastName', '')}")
            else:
                error_msg = f"Failed to get tokens. Status: {response.status_code}, Response: {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
            
        except Exception as e:
            error_msg = f"LinkedIn authentication failed: {str(e)}"
            logger.error(error_msg)
            print(f"\nError: {error_msg}")
            raise
        finally:
            print("\nCleaning up...")
            try:
                server.shutdown()
                server.server_close()
                print("Local server shut down successfully")
            except Exception as e:
                print(f"Error during cleanup: {str(e)}")

    def _generate_state_param(self) -> str:
        """Generate a random state parameter for OAuth security."""
        import secrets
        return secrets.token_urlsafe(32)

    def _generate_nonce(self) -> str:
        """Generate a random nonce for OpenID Connect security."""
        import secrets
        return secrets.token_urlsafe(32)
    
    def _make_api_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make authenticated request to LinkedIn OpenID Connect endpoints."""
        if not self.access_token:
            raise Exception("Not authenticated")
            
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        # Use OpenID Connect userinfo endpoint for profile data
        if endpoint == 'me':
            url = "https://api.linkedin.com/v2/userinfo"
        else:
            url = f"https://api.linkedin.com/v2/{endpoint}"
            
        response = self._make_request_with_retry('GET', url, headers=headers, params=params)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise Exception("Authentication token expired or invalid")
        elif response.status_code == 403:
            raise Exception("Insufficient permissions. Please check API scopes")
        else:
            raise Exception(f"API request failed: {response.status_code} - {response.text}")
    
    def fetch_full_data(self) -> Dict[str, Any]:
        """Fetch all available LinkedIn data through OpenID Connect."""
        try:
            return {
                'profile': self._fetch_profile(),
                # Note: Posts and connections are not available through OpenID Connect
                'posts': [],
                'connections': []
            }
        except Exception as e:
            logger.error(f"Error fetching LinkedIn data: {str(e)}")
            raise

    def fetch_new_data(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        """Fetch new LinkedIn data through OpenID Connect."""
        return self.fetch_full_data()  # OpenID Connect doesn't support incremental data

    def fetch_data_in_range(self, start: datetime, end: datetime) -> Dict[str, Any]:
        """Fetch LinkedIn data within date range through OpenID Connect."""
        return self.fetch_full_data()  # OpenID Connect doesn't support date ranges

    def _fetch_profile(self) -> Dict[str, Any]:
        """Fetch user's profile using OpenID Connect userinfo endpoint."""
        try:
            profile = self._make_api_request('me')  # This will use the userinfo endpoint
            
            return {
                'id': profile.get('sub'),  # OpenID Connect uses 'sub' for user ID
                'name': profile.get('name', ''),
                'given_name': profile.get('given_name', ''),
                'family_name': profile.get('family_name', ''),
                'email': profile.get('email', ''),
                'picture': profile.get('picture', ''),
                'locale': profile.get('locale', ''),
                'updated_at': profile.get('updated_at', '')
            }
        except Exception as e:
            logger.error(f"Error fetching profile: {str(e)}")
            raise

    def _fetch_posts(self, since: Optional[datetime] = None, 
                    start: Optional[datetime] = None,
                    end: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Posts are not available through OpenID Connect."""
        logger.warning("Posts are not available through OpenID Connect")
        return []

    def _fetch_connections(self) -> List[Dict[str, Any]]:
        """Connections are not available through OpenID Connect."""
        logger.warning("Connections are not available through OpenID Connect")
        return [] 