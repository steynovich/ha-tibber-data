"""Tibber Data API client with OAuth2 authentication."""
from __future__ import annotations

import asyncio
import hashlib
import random
import secrets
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

from .models import TibberOAuthSession, TibberHome, TibberDevice


# Retry configuration according to Tibber API specs
RETRY_MAX_ATTEMPTS = 5
RETRY_INITIAL_DELAY = 0.4  # 400 milliseconds
RETRY_BACKOFF_FACTOR = 2
RETRY_MAX_DELAY = 15.0  # 15 seconds
RETRY_JITTER_MAX = 0.25  # 250 milliseconds for Retry-After jitter

# HTTP status codes that should trigger retries (transient errors)
RETRY_STATUS_CODES = {429, 500, 502, 503}

# HTTP status codes that should NOT be retried (permanent errors)
NO_RETRY_STATUS_CODES = {400, 401, 403, 404}


class TibberDataClient:
    """Client for Tibber Data API with OAuth2 authentication."""

    def __init__(
        self,
        client_id: str = "",
        base_url: str = "https://data-api.tibber.com",
        session: Optional[aiohttp.ClientSession] = None,
        access_token: Optional[str] = None,
        oauth_session: Optional[TibberOAuthSession] = None
    ) -> None:
        """Initialize Tibber Data API client."""
        self.client_id = client_id
        self.base_url = base_url.rstrip("/")
        self._session = session
        self._access_token = access_token
        self._oauth_session = oauth_session
        self._session_owned = False  # Track if we created the session

    @property
    def session(self) -> aiohttp.ClientSession:
        """Get aiohttp session."""
        if self._session is None:
            raise RuntimeError("Session not initialized. Call set_session() first.")
        return self._session

    def set_session(self, session: aiohttp.ClientSession) -> None:
        """Set aiohttp session."""
        self._session = session

    def set_oauth_session(self, oauth_session: TibberOAuthSession) -> None:
        """Set OAuth2 session for authenticated requests."""
        self._oauth_session = oauth_session
        self._access_token = oauth_session.access_token

    # OAuth2 Flow Methods

    def generate_pkce_challenge(self) -> tuple[str, str]:
        """Generate PKCE code verifier and challenge."""
        code_verifier = secrets.token_urlsafe(96)  # 128 characters
        code_challenge = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge_b64 = (
            code_challenge.hex().encode().decode()  # Convert to base64url without padding
        )
        return code_verifier, code_challenge_b64

    async def get_authorization_url(
        self,
        client_id: str,
        redirect_uri: str,
        state: str,
        code_challenge: str,
        scopes: List[str]
    ) -> str:
        """Generate OAuth2 authorization URL."""
        if not client_id:
            raise ValueError("Missing required parameter: client_id")
        if not redirect_uri:
            raise ValueError("Missing required parameter: redirect_uri")
        if not code_challenge:
            raise ValueError("PKCE code challenge is required")

        # Validate scopes against Tibber's supported scopes
        valid_scopes = {
            "openid",
            "profile",
            "email",
            "offline_access",
            "data-api-user-read",
            "data-api-homes-read",
            "data-api-device-categories-read"  # Additional device category scopes may be added
        }
        invalid_scopes = set(scopes) - valid_scopes
        if invalid_scopes:
            raise ValueError(f"Invalid scope: {invalid_scopes}")

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256"
        }

        query_string = urllib.parse.urlencode(params)
        return f"https://thewall.tibber.com/connect/authorize?{query_string}"

    async def validate_authorization_request(
        self,
        client_id: str,
        redirect_uri: str,
        code_challenge: str
    ) -> bool:
        """Validate authorization request parameters."""
        if not client_id:
            raise ValueError("Missing required parameter: client_id")
        if not redirect_uri:
            raise ValueError("Missing required parameter: redirect_uri")
        if not code_challenge:
            raise ValueError("Missing required parameter: code_challenge")

        return True

    async def exchange_code_for_token(
        self,
        client_id: str,
        code: str,
        redirect_uri: str,
        code_verifier: str
    ) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        if not client_id:
            raise ValueError("Missing required parameter: client_id")
        if not code:
            raise ValueError("Missing required parameter: code")
        if not redirect_uri:
            raise ValueError("Missing required parameter: redirect_uri")
        if not code_verifier:
            raise ValueError("Missing required parameter: code_verifier")

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "code_verifier": code_verifier
        }

        url = "https://thewall.tibber.com/connect/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with self.session.post(url, data=data, headers=headers) as response:
            response_data = await response.json()

            if response.status == 400:
                error_desc = response_data.get("error_description", "Invalid request")
                if "invalid_grant" in response_data.get("error", ""):
                    raise ValueError("Invalid authorization code")
                raise ValueError(f"Token exchange failed: {error_desc}")

            if response.status == 401:
                raise ValueError("Client authentication failed")

            if response.status != 200:
                raise ValueError(f"Token exchange failed: HTTP {response.status}")

            return response_data

    async def refresh_access_token(
        self,
        client_id: str,
        refresh_token: str
    ) -> Dict[str, Any]:
        """Refresh expired access token using refresh token.

        Tibber refresh tokens are long-lived (~30 days) and may be rotated.
        """
        if not client_id:
            raise ValueError("Missing required parameter: client_id")
        if not refresh_token:
            raise ValueError("Missing required parameter: refresh_token")

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id
        }

        url = "https://thewall.tibber.com/connect/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with self.session.post(url, data=data, headers=headers) as response:
            response_data = await response.json()

            if response.status == 401:
                error_desc = response_data.get("error_description", "Invalid refresh token")
                if "expired" in error_desc.lower():
                    raise ValueError("Refresh token expired - reauthentication required")
                raise ValueError("Invalid refresh token")

            if response.status == 400:
                error_desc = response_data.get("error_description", "Bad request")
                raise ValueError(f"Token refresh failed: {error_desc}")

            if response.status != 200:
                raise ValueError(f"Token refresh failed: HTTP {response.status}")

            return response_data

    def should_refresh_token(
        self,
        expires_at: int,
        current_time: int,
        threshold_seconds: int = 300  # 5 minutes before expiry
    ) -> bool:
        """Check if token should be refreshed.

        Tibber access tokens last ~1 hour, refresh when within 5 minutes of expiry.
        """
        return current_time >= (expires_at - threshold_seconds)

    # API Methods

    def _calculate_retry_delay(self, attempt: int, retry_after: Optional[str] = None) -> float:
        """Calculate retry delay with exponential backoff and full jitter."""
        if retry_after:
            try:
                # Use Retry-After header value + small random jitter (0-250ms)
                base_delay = float(retry_after)
                jitter = random.uniform(0, RETRY_JITTER_MAX)
                return base_delay + jitter
            except (ValueError, TypeError):
                pass  # Fall back to exponential backoff

        # Exponential backoff with full jitter
        exponential_delay = RETRY_INITIAL_DELAY * (RETRY_BACKOFF_FACTOR ** attempt)
        max_delay = min(exponential_delay, RETRY_MAX_DELAY)

        # Full jitter: random value between 0 and max_delay
        return random.uniform(0, max_delay)

    async def _make_authenticated_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make authenticated request to API with retry logic."""
        if not self._access_token:
            raise ValueError("No access token available")

        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json"
        }

        last_exception = None

        for attempt in range(RETRY_MAX_ATTEMPTS):
            try:
                async with self.session.request(
                    method, url, headers=headers, params=params, json=data
                ) as response:
                    # Handle successful responses
                    if response.status == 200:
                        response_data = await response.json()
                        return response_data

                    # Handle permanent errors (do not retry)
                    if response.status in NO_RETRY_STATUS_CODES:
                        response_data = await response.json()

                        if response.status == 401:
                            raise ValueError("Invalid or expired token")
                        elif response.status == 403:
                            raise ValueError("Insufficient permissions")
                        elif response.status == 404:
                            error_msg = response_data.get("message", "Not found")
                            if "home" in error_msg.lower():
                                raise ValueError("Home not found")
                            elif "device" in error_msg.lower():
                                raise ValueError("Device not found")
                            raise ValueError(error_msg)
                        else:  # 400
                            error_msg = response_data.get("message", "Bad request")
                            raise ValueError(f"Invalid request: {error_msg}")

                    # Handle transient errors (retry eligible)
                    if response.status in RETRY_STATUS_CODES:
                        response_data = await response.json()

                        # Get retry delay
                        retry_after = response.headers.get("Retry-After")
                        delay = self._calculate_retry_delay(attempt, retry_after)

                        # Create appropriate exception
                        if response.status == 429:
                            last_exception = ValueError("Rate limit exceeded")
                        else:  # 500, 502, 503
                            error_msg = response_data.get("message", f"Server error (HTTP {response.status})")
                            last_exception = ValueError(f"Transient server error: {error_msg}")

                        # Don't delay on the last attempt
                        if attempt < RETRY_MAX_ATTEMPTS - 1:
                            await asyncio.sleep(delay)
                        continue

                    # Handle other status codes
                    response_data = await response.json()
                    error_msg = response_data.get("message", f"HTTP {response.status}")
                    raise ValueError(f"API request failed: {error_msg}")

            except aiohttp.ClientError as exc:
                # Network errors are retryable
                last_exception = ValueError(f"Network error: {exc}")
                if attempt < RETRY_MAX_ATTEMPTS - 1:
                    delay = self._calculate_retry_delay(attempt)
                    await asyncio.sleep(delay)
                continue

        # If we get here, all retries have been exhausted
        if last_exception:
            raise last_exception
        else:
            raise ValueError("Request failed after all retry attempts")


    async def get_homes(self) -> List[Dict[str, Any]]:
        """Get list of user homes."""
        response = await self._make_authenticated_request("GET", "/v1/homes")
        return response.get("data", [])

    async def get_home_details(self, home_id: str) -> Dict[str, Any]:
        """Get detailed information for specific home."""
        # Validate home ID format
        if not home_id or len(home_id.split("-")) != 5:
            raise ValueError("Invalid home ID format")

        response = await self._make_authenticated_request("GET", f"/v1/homes/{home_id}")
        return response.get("data", {})

    async def get_home_devices(self, home_id: str) -> List[Dict[str, Any]]:
        """Get all devices associated with specific home."""
        response = await self._make_authenticated_request("GET", f"/v1/homes/{home_id}/devices")
        return response.get("data", [])

    async def get_device_details(self, home_id: str, device_id: str) -> Dict[str, Any]:
        """Get detailed information for specific device."""
        endpoint = f"/v1/homes/{home_id}/devices/{device_id}"
        response = await self._make_authenticated_request("GET", endpoint)
        return response.get("data", {})

    async def get_device_history(
        self,
        home_id: str,
        device_id: str,
        from_time: str,
        to_time: str,
        resolution: str = "HOURLY"
    ) -> List[Dict[str, Any]]:
        """Get historical data for device capabilities."""
        # Validate resolution
        valid_resolutions = {"HOURLY", "DAILY"}
        if resolution not in valid_resolutions:
            raise ValueError("Invalid resolution")

        # Validate time order
        try:
            from_dt = datetime.fromisoformat(from_time.replace("Z", "+00:00"))
            to_dt = datetime.fromisoformat(to_time.replace("Z", "+00:00"))
            if from_dt >= to_dt:
                raise ValueError("from_time must be before to_time")
        except ValueError as e:
            if "from_time must be before to_time" in str(e):
                raise
            raise ValueError("Invalid datetime format")

        params = {
            "from": from_time,
            "to": to_time,
            "resolution": resolution
        }

        endpoint = f"/v1/homes/{home_id}/devices/{device_id}/history"
        response = await self._make_authenticated_request("GET", endpoint, params=params)
        return response.get("data", [])

    # High-level methods for Home Assistant integration

    async def get_all_devices(self) -> List[TibberDevice]:
        """Get all devices for all user homes."""
        devices = []
        homes = await self.get_homes()

        for home_data in homes:
            home_id = home_data["id"]
            home_devices = await self.get_home_devices(home_id)

            for device_data in home_devices:
                # Get detailed device information including capabilities
                device_details = await self.get_device_details(home_id, device_data["id"])
                device = TibberDevice.from_api_data(device_details, home_id)
                devices.append(device)

        return devices

    async def get_homes_with_devices(self) -> tuple[List[TibberHome], List[TibberDevice]]:
        """Get all homes and their devices in one call."""
        homes_data = await self.get_homes()
        homes = [TibberHome.from_api_data(home_data) for home_data in homes_data]

        all_devices = []
        for home in homes:
            home_devices = await self.get_home_devices(home.home_id)

            for device_data in home_devices:
                # Get detailed device information
                device_details = await self.get_device_details(home.home_id, device_data["id"])
                device = TibberDevice.from_api_data(device_details, home.home_id)
                all_devices.append(device)

        return homes, all_devices

    async def update_device_states(self, devices: List[TibberDevice]) -> List[TibberDevice]:
        """Update states for multiple devices efficiently."""
        updated_devices = []

        for device in devices:
            try:
                # Get current device state
                device_details = await self.get_device_details(device.home_id, device.device_id)
                updated_device = TibberDevice.from_api_data(device_details, device.home_id)
                updated_devices.append(updated_device)
            except Exception:
                # If device update fails, keep the old device data
                # but mark it as potentially unavailable
                device.online_status = False
                updated_devices.append(device)

        return updated_devices

    async def close(self) -> None:
        """Close the client session if we own it."""
        if self._session and not self._session.closed and self._session_owned:
            await self._session.close()

    async def __aenter__(self) -> TibberDataClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()