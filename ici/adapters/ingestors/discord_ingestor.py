"""
Discord data ingestor with OAuth2 authentication.
"""

import asyncio
import aiohttp
from aiohttp import web
import webbrowser
from typing import Dict, Any, Optional, AsyncContextManager
from rich.status import Status
import logging
import secrets
import time
from contextlib import asynccontextmanager
from urllib.parse import urlencode

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Shared status context
def display_status(message: str) -> AsyncContextManager[Status]:
    """Create a status display context manager."""
    return Status(message, spinner="dots")

class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass

# --- OAuth2 Callback Handler ---

class OAuth2CallbackHandler:
    def __init__(self, port: int = 8001):
        self.port = port
        self.app = web.Application()
        self.app.router.add_get("/callback", self.handle_callback)
        self.runner = None
        self.site = None
        self.auth_code = None
        self.auth_state = None
        self._shutdown_event = asyncio.Event()

    async def start(self):
        """Start the callback server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, 'localhost', self.port)
        await self.site.start()

    async def stop(self):
        """Stop the callback server cleanly."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        self._shutdown_event.set()

    async def handle_callback(self, request: web.Request) -> web.Response:
        """Handle the OAuth2 callback."""
        try:
            self.auth_code = request.query.get('code')
            self.auth_state = request.query.get('state')
            
            # Send a success response to the browser
            html_response = """
            <html>
                <body style="background-color: #2C2F33; color: white; font-family: Arial, sans-serif; text-align: center; padding-top: 50px;">
                    <h2>Authentication Successful! ✨</h2>
                    <p>You can now close this window and return to the application.</p>
                </body>
            </html>
            """
            
            # Schedule server shutdown
            asyncio.create_task(self.stop())
            
            return web.Response(text=html_response, content_type='text/html')
            
        except Exception as e:
            logging.error(f"Callback error: {str(e)}")
            return web.Response(text=str(e), status=500)

    async def wait_for_code(self, timeout: int = 300) -> Optional[str]:
        """Wait for the authorization code with timeout."""
        try:
            await asyncio.wait_for(self._shutdown_event.wait(), timeout=timeout)
            return self.auth_code
        except asyncio.TimeoutError:
            logging.error("OAuth2 callback timeout")
            await self.stop()
            return None

# --- Discord Ingestor --- 

class DiscordIngestor:
    """
    Ingestor implementation for Discord data using OAuth2.
    
    Fetches user profile and server list.
    
    Required config parameters under `ingestors.discord`:
    - client_id: Discord Application Client ID
    - client_secret: Discord Application Client Secret
    - redirect_uri: Must match one registered in Discord Dev Portal (e.g., http://localhost:8001/callback)
    Optional:
    - scopes: List of OAuth scopes (defaults to ['identify', 'guilds'])
    - port: Port for the local callback server (defaults to 8001)
    - timeout_seconds: Timeout for waiting for user authorization (defaults to 300)
    """
    
    BASE_API_URL = "https://discord.com/api/v10" # Using API v10 as recommended
    AUTHORIZATION_URL = "https://discord.com/api/oauth2/authorize"
    TOKEN_URL = "https://discord.com/api/oauth2/token"

    def __init__(self, logger_name: str = "discord_ingestor"):
        """Initialize the Discord ingestor."""
        self.logger = logging.getLogger(logger_name)
        self._is_initialized = False
        self._config_path = None
        self._client_id = "1360574636945047628"
        self._client_secret = "8767582a828246e0a7a66eedce343967a33d1242212a61df6c78c0bc9d963063"
        self._redirect_uri = "http://localhost:8001/callback"
        self._scopes = [
            'identify',           # Basic user info
            'guilds',            # List of guilds (servers)
            'email',             # Email address
            'messages.read'      # Read message history
        ]
        self._port = 8001
        self._timeout_seconds = 300
        self._access_token = None
        self._refresh_token = None
        self._token_expires_at = None
        self._session: Optional[aiohttp.ClientSession] = None
        self.callback_handler = None

    @asynccontextmanager
    async def _http_session(self):
        """Async context manager for HTTP session."""
        if not self._session:
            self._session = aiohttp.ClientSession()
        try:
            yield self._session
        finally:
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None

    async def initialize(self) -> None:
        """Initialize the Discord ingestor."""
        if self._is_initialized:
            self.logger.info("Discord ingestor already initialized.")
            return

        try:
            with display_status("Starting Discord ingestor initialization..."):
                # Ensure we have an event loop
                loop = asyncio.get_running_loop()
                
                self._config_path = self._config_path or "config.yaml"
                config_path_key = "orchestrator.pipelines.discord_profile.ingestor.discord"
                config = get_component_config(config_path_key, self._config_path)
                
                if not config:
                    raise ConfigurationError(f"No configuration found for Discord ingestor using key '{config_path_key}' in {self._config_path}")
                
                # Load and validate configuration
                required_fields = ['client_id', 'client_secret', 'redirect_uri']
                missing_fields = [field for field in required_fields if not config.get(field)]
                if missing_fields:
                    raise ConfigurationError(f"Missing required fields: {', '.join(missing_fields)}")
                
                for field in required_fields:
                    setattr(self, f"_{field}", config[field])
                
                self._scopes = config.get("scopes", self._scopes)
                self._port = config.get("port", self._port)
                self._timeout_seconds = config.get("timeout_seconds", self._timeout_seconds)

            with display_status("Starting OAuth2 flow..."):
                # Perform OAuth flow with proper async timeout
                async with asyncio.timeout(self._timeout_seconds):
                    await self._perform_oauth_flow()

            with display_status("Finalizing initialization..."):
                self._is_initialized = True
                self.logger.info({
                    "action": "INGESTOR_INITIALIZED",
                    "message": "Discord ingestor initialized successfully"
                })
            
        except asyncio.TimeoutError:
            self.logger.error({
                "action": "INITIALIZATION_ERROR",
                "message": f"Discord ingestor initialization timed out after {self._timeout_seconds} seconds"
            })
            await self._cleanup()
            raise AuthenticationError(f"Discord initialization timed out after {self._timeout_seconds} seconds")
        except Exception as e:
            self.logger.error({
                "action": "INITIALIZATION_ERROR",
                "message": f"Discord ingestor initialization failed: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            await self._cleanup()
            raise

    async def _cleanup(self) -> None:
        """Clean up resources."""
        try:
            await self.callback_handler.stop()
            if self._session and not self._session.closed:
                await self._session.close()
                self._session = None
        except Exception as e:
            self.logger.error({
                "action": "CLEANUP_ERROR",
                "message": f"Error during cleanup: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })

    async def _perform_oauth_flow(self) -> None:
        """Handles the OAuth2 Authorization Code Grant flow for Discord."""
        try:
            # --- Generate State & Auth URL --- 
            state = secrets.token_urlsafe(32)
            auth_params = {
                'client_id': self._client_id,
                'redirect_uri': self._redirect_uri,
                'response_type': 'code',
                'scope': ' '.join(self._scopes),
                'state': state,
                'permissions': '0'  # Don't request any special permissions
            }
            auth_url = f"{self.AUTHORIZATION_URL}?{urlencode(auth_params)}"
            
            # --- Start Server and Open Browser ---
            self.logger.info("Starting OAuth2 callback server...")
            self.callback_handler = OAuth2CallbackHandler(port=self._port)
            await self.callback_handler.start()
            self.logger.info({
                "action": "OAUTH_FLOW_PROGRESS",
                "message": "Opening browser for Discord authorization",
                "data": {
                    "auth_url": auth_url,
                    "port": self._port,
                    "redirect_uri": self._redirect_uri
                }
            })
            webbrowser.open(auth_url)
            
            # --- Wait for Callback ---
            start_time = time.time()
            self.logger.info("Waiting for OAuth2 callback...")
            while time.time() - start_time < self._timeout_seconds:
                if self.callback_handler.auth_error:
                    error_msg = f"Discord authorization failed: {self.callback_handler.auth_error}"
                    self.logger.error({"action": "OAUTH_ERROR", "message": error_msg})
                    raise AuthenticationError(error_msg)
                if self.callback_handler.auth_code:
                    if self.callback_handler.auth_state != state:
                        error_msg = "State mismatch in OAuth callback"
                        self.logger.error({"action": "OAUTH_ERROR", "message": error_msg})
                        raise AuthenticationError(error_msg)
                    self.logger.info("Received OAuth2 callback code successfully.")
                    break
                await asyncio.sleep(0.5)
            else:
                error_msg = "Timeout waiting for Discord authorization"
                self.logger.error({"action": "OAUTH_ERROR", "message": error_msg})
                raise AuthenticationError(error_msg)

            # --- Exchange Code for Token ---
            self.logger.info("Exchanging authorization code for access token...")
            token_data = {
                'client_id': self._client_id,
                'client_secret': self._client_secret,
                'grant_type': 'authorization_code',
                'code': self.callback_handler.auth_code,
                'redirect_uri': self._redirect_uri,
                'scope': ' '.join(self._scopes)
            }
            
            async with self._http_session() as session:
                async with session.post(self.TOKEN_URL, data=token_data) as response:
                    if response.status != 200:
                        error_details = await response.text()
                        error_msg = f"Failed to exchange code for token. Status: {response.status}, Details: {error_details}"
                        self.logger.error({"action": "TOKEN_ERROR", "message": error_msg})
                        raise AuthenticationError(error_msg)
                    
                    token_response = await response.json()
                    self._access_token = token_response['access_token']
                    self._refresh_token = token_response.get('refresh_token')
                    expires_in = token_response.get('expires_in', 604800)  # Default to 7 days
                    self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                    
                    self.logger.info({
                        "action": "OAUTH_FLOW_COMPLETE",
                        "message": "Successfully obtained Discord access token",
                        "data": {"expires_in": expires_in}
                    })

        except Exception as e:
            self.logger.error({
                "action": "OAUTH_FLOW_ERROR",
                "message": f"Error during OAuth flow: {str(e)}",
                "data": {"error": str(e), "error_type": type(e).__name__}
            })
            raise
        finally:
            self.logger.info("Stopping OAuth2 callback server...")
            await self.callback_handler.stop()

    async def _refresh_access_token(self) -> None:
        """Refresh the access token using the refresh token."""
        if not self._refresh_token:
            raise AuthenticationError("No refresh token available")
            
        token_data = {
            'client_id': self._client_id,
            'client_secret': self._client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': self._refresh_token
        }
        
        async with self._http_session() as session:
            async with session.post(self.TOKEN_URL, data=token_data) as response:
                if response.status != 200:
                    error_details = await response.text()
                    raise AuthenticationError(f"Failed to refresh token. Status: {response.status}, Details: {error_details}")
                
                token_response = await response.json()
                self._access_token = token_response['access_token']
                self._refresh_token = token_response.get('refresh_token', self._refresh_token)
                expires_in = token_response.get('expires_in', 604800)
                self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    async def _make_api_request(self, endpoint: str, method: str = 'GET', **kwargs) -> Any:
        """Make an authenticated request to the Discord API with automatic token refresh."""
        if not self._is_initialized:
            raise RuntimeError("Discord ingestor not initialized")
            
        if self._token_expires_at and datetime.now(timezone.utc) >= self._token_expires_at - timedelta(minutes=5):
            await self._refresh_access_token()
            
        headers = {
            'Authorization': f'Bearer {self._access_token}',
            'Content-Type': 'application/json'
        }
        
        # Add Bot token authorization if available
        if kwargs.pop('use_bot_auth', False):
            headers['Authorization'] = f'Bot {self._access_token}'
        
        url = f"{self.BASE_API_URL}/{endpoint.lstrip('/')}"
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                async with self._http_session() as session:
                    async with session.request(method, url, headers=headers, **kwargs) as response:
                        if response.status == 429:  # Rate limit
                            retry_after = float(response.headers.get('Retry-After', retry_delay))
                            self.logger.warning({
                                "action": "RATE_LIMIT_HIT",
                                "message": f"Discord API rate limit hit, waiting {retry_after} seconds",
                                "data": {"retry_after": retry_after, "attempt": attempt + 1}
                            })
                            await asyncio.sleep(retry_after)
                            continue
                            
                        if response.status >= 500:  # Server error
                            if attempt < max_retries - 1:
                                await asyncio.sleep(retry_delay * (2 ** attempt))
                                continue
                                
                        if response.status == 401:
                            error_text = await response.text()
                            self.logger.error({
                                "action": "AUTH_ERROR",
                                "message": "Authentication failed",
                                "data": {"error": error_text, "endpoint": endpoint}
                            })
                            raise AuthenticationError(f"Discord authentication failed: {error_text}")
                            
                        response.raise_for_status()
                        return await response.json()
                        
            except aiohttp.ClientError as e:
                if attempt == max_retries - 1:
                    raise DataFetchError(f"Discord API request failed: {str(e)}")
                await asyncio.sleep(retry_delay * (2 ** attempt))
                
        raise DataFetchError("Maximum retries exceeded for Discord API request")

    async def fetch_full_data(self) -> Dict[str, Any]:
        """Fetch all available data from Discord."""
        try:
            async with asyncio.timeout(self._timeout_seconds):
                user_data = await self._make_api_request('users/@me')
                guilds_data = await self._make_api_request('users/@me/guilds')
                
                # Fetch detailed data for each guild using bot token
                detailed_guilds = []
                for guild in guilds_data:
                    try:
                        guild_details = await self._make_api_request(
                            f'guilds/{guild["id"]}',
                            use_bot_auth=True
                        )
                        
                        # Fetch recent messages for each guild
                        channels = await self._make_api_request(
                            f'guilds/{guild["id"]}/channels',
                            use_bot_auth=True
                        )
                        
                        text_channels = [ch for ch in channels if ch['type'] == 0]  # 0 is text channel
                        guild_details['channels'] = []
                        
                        for channel in text_channels[:5]:  # Limit to first 5 text channels
                            try:
                                messages = await self._make_api_request(
                                    f'channels/{channel["id"]}/messages?limit=50',
                                    use_bot_auth=True
                                )
                                channel['recent_messages'] = messages
                                guild_details['channels'].append(channel)
                            except Exception as e:
                                self.logger.warning({
                                    "action": "CHANNEL_FETCH_ERROR",
                                    "message": f"Failed to fetch messages for channel {channel['id']}",
                                    "data": {"channel_id": channel["id"], "error": str(e)}
                                })
                        
                        detailed_guilds.append(guild_details)
                    except Exception as e:
                        self.logger.warning({
                            "action": "GUILD_FETCH_ERROR",
                            "message": f"Failed to fetch details for guild {guild['id']}",
                            "data": {"guild_id": guild["id"], "error": str(e)}
                        })
                
                return {
                    'user': user_data,
                    'guilds': detailed_guilds,
                    'fetched_at': datetime.now(timezone.utc).isoformat()
                }
                
        except asyncio.TimeoutError:
            raise DataFetchError(f"Data fetch timed out after {self._timeout_seconds} seconds")
        except Exception as e:
            raise DataFetchError(f"Failed to fetch Discord data: {str(e)}")

    async def fetch_new_data(self, since: Optional[datetime] = None) -> Dict[str, Any]:
        self.logger.warning("fetch_new_data currently calls fetch_full_data for Discord.")
        # Discord API doesn't easily support fetching profile/guild changes 'since'.
        # For a real implementation needing new data, you'd likely need to compare 
        # fetch_full_data results over time or use the Gateway API (more complex).
        return await self.fetch_full_data()

    async def fetch_data_in_range(self, start: datetime, end: datetime) -> Dict[str, Any]:
        self.logger.warning("fetch_data_in_range currently calls fetch_full_data for Discord.")
        # Similarly, fetching profile/guilds based on a date range isn't standard via REST.
        return await self.fetch_full_data()

    async def healthcheck(self) -> Dict[str, Any]:
        """
        Performs a health check on the Discord ingestor.
        Checks initialization status and verifies API access with a simple call.

        Returns:
            Dict[str, Any]: A dictionary indicating the health status.
        """
        if not self._is_initialized:
            return {
                "status": "uninitialized",
                "details": "Discord ingestor has not been initialized."
            }
        
        if not self._access_token:
             return {
                "status": "unhealthy",
                "details": "Ingestor initialized but no access token found."
            }

        # TODO: Add check for token expiration (self._token_expires_at)

        try:
            # Perform a lightweight API call to verify the token works
            await self._make_api_request('users/@me', retries=1) # Only try once for healthcheck
            return {
                "status": "healthy",
                "details": "Initialized and basic API check successful."
            }
        except AuthenticationError as e:
            self.logger.warning(f"Healthcheck failed due to authentication error: {e}")
            return {
                "status": "unhealthy",
                "details": f"Authentication error during healthcheck: {e}"
            }
        except DataFetchError as e:
             self.logger.warning(f"Healthcheck failed due to data fetch error: {e}")
             return {
                 "status": "unhealthy",
                 "details": f"Data fetch error during healthcheck: {e}"
             }
        except Exception as e:
            self.logger.error(f"Unexpected error during healthcheck: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "details": f"Unexpected error during healthcheck: {str(e)}"
            }

    async def close(self) -> None:
        """Clean up resources when done."""
        await self._cleanup()

# Example usage (for testing within this file, remove later)
# import asyncio
# async def test_run():
#     logging.basicConfig(level=logging.INFO)
#     # Make sure you have a config.yaml with ingestors.discord section
#     # and required client_id, client_secret, redirect_uri
#     # The redirect_uri should be http://localhost:8001/callback (or matching self._port)
#     ingestor = DiscordIngestor()
#     try:
#         await ingestor.initialize()
#         # data = await ingestor.fetch_full_data()
#         # print("Fetched data:", data)
#     except Exception as e:
#         print(f"Test failed: {e}")

# if __name__ == "__main__":
#     asyncio.run(test_run()) 