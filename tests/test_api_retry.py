"""Test API retry and backoff mechanisms."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from aiohttp import ClientError
from custom_components.tibber_data.api.client import (
    TibberDataClient,
    RETRY_MAX_ATTEMPTS,
    RETRY_INITIAL_DELAY,
    RETRY_BACKOFF_FACTOR,
    RETRY_MAX_DELAY,
    RETRY_JITTER_MAX,
    RETRY_STATUS_CODES,
    NO_RETRY_STATUS_CODES
)


class TestTibberDataClientRetry:
    """Test retry and backoff functionality."""

    @pytest.fixture
    def mock_session(self):
        """Mock aiohttp session."""
        session = Mock()
        return session

    @pytest.fixture
    def client(self, mock_session):
        """Create client with mock session."""
        client = TibberDataClient(
            client_id="test_client_id",
            access_token="test_access_token",
            session=mock_session
        )
        return client

    def test_retry_delay_calculation_exponential_backoff(self, client):
        """Test exponential backoff calculation with full jitter."""
        # Mock random.uniform to return predictable values for testing
        with patch('custom_components.tibber_data.api.client.random.uniform') as mock_random:
            # Test attempt 0 (first retry)
            expected_max_0 = RETRY_INITIAL_DELAY * (RETRY_BACKOFF_FACTOR ** 0)  # 0.4
            mock_random.return_value = 0.2  # Return fixed value
            delay = client._calculate_retry_delay(0)
            assert delay == 0.2
            mock_random.assert_called_with(0, expected_max_0)

            # Test attempt 2
            expected_max_2 = RETRY_INITIAL_DELAY * (RETRY_BACKOFF_FACTOR ** 2)  # 1.6
            mock_random.return_value = 0.8  # Return different fixed value
            delay = client._calculate_retry_delay(2)
            assert delay == 0.8
            mock_random.assert_called_with(0, expected_max_2)

    def test_retry_delay_calculation_max_cap(self, client):
        """Test that retry delay is capped at maximum value."""
        with patch('custom_components.tibber_data.api.client.random.uniform') as mock_random:
            mock_random.return_value = RETRY_MAX_DELAY

            # High attempt number should be capped
            delay = client._calculate_retry_delay(10)
            assert delay == RETRY_MAX_DELAY
            mock_random.assert_called_with(0, RETRY_MAX_DELAY)

    def test_retry_delay_with_retry_after_header(self, client):
        """Test retry delay calculation with Retry-After header."""
        with patch('custom_components.tibber_data.api.client.random.uniform') as mock_random:
            mock_random.return_value = 0.1  # 100ms jitter

            # Test with valid Retry-After header
            delay = client._calculate_retry_delay(0, retry_after="2")
            expected_delay = 2.0 + 0.1  # base delay + jitter
            assert delay == expected_delay
            mock_random.assert_called_with(0, RETRY_JITTER_MAX)

    def test_retry_delay_invalid_retry_after_fallback(self, client):
        """Test fallback to exponential backoff for invalid Retry-After header."""
        with patch('custom_components.tibber_data.api.client.random.uniform') as mock_random:
            mock_random.return_value = 0.5  # Return fixed value

            # Invalid Retry-After header should fall back to exponential backoff
            delay = client._calculate_retry_delay(1, retry_after="invalid")
            expected_max = RETRY_INITIAL_DELAY * (RETRY_BACKOFF_FACTOR ** 1)  # 0.8
            assert delay == 0.5
            mock_random.assert_called_with(0, expected_max)

    @pytest.mark.asyncio
    async def test_successful_request_no_retry(self, client):
        """Test successful request requires no retries."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": "success"})

        mock_session = client.session
        mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await client._make_authenticated_request("GET", "/test")

        assert result == {"data": "success"}
        # Should only make one request
        assert mock_session.request.call_count == 1

    @pytest.mark.asyncio
    async def test_permanent_error_no_retry(self, client):
        """Test that permanent errors (400, 401, 403, 404) are not retried."""
        for status_code in NO_RETRY_STATUS_CODES:
            # Reset mock
            client.session.request.reset_mock()

            # Mock error response
            mock_response = Mock()
            mock_response.status = status_code
            mock_response.json = AsyncMock(return_value={"message": f"Error {status_code}"})

            mock_session = client.session
            mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)

            # Should raise error without retrying
            with pytest.raises(ValueError):
                await client._make_authenticated_request("GET", "/test")

            # Should only make one request (no retries)
            assert mock_session.request.call_count == 1

    @pytest.mark.asyncio
    async def test_transient_error_retries(self, client):
        """Test that transient errors trigger retries."""
        responses = []

        # First 4 attempts fail with 429, 5th succeeds
        for i in range(RETRY_MAX_ATTEMPTS - 1):
            mock_response = Mock()
            mock_response.status = 429
            mock_response.headers = {"Retry-After": "1"}
            mock_response.json = AsyncMock(return_value={"message": "Rate limited"})
            responses.append(mock_response)

        # Final attempt succeeds
        success_response = Mock()
        success_response.status = 200
        success_response.json = AsyncMock(return_value={"data": "success"})
        responses.append(success_response)

        # Mock multiple responses
        async def mock_context_manager(response):
            return response

        mock_session = client.session
        mock_session.request.return_value.__aenter__ = AsyncMock(side_effect=responses)
        mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await client._make_authenticated_request("GET", "/test")

        assert result == {"data": "success"}
        # Should make 5 requests total
        assert mock_session.request.call_count == RETRY_MAX_ATTEMPTS
        # Should sleep 4 times (between retries)
        assert mock_sleep.call_count == RETRY_MAX_ATTEMPTS - 1

    @pytest.mark.asyncio
    async def test_retry_exhaustion_raises_last_exception(self, client):
        """Test that exhausted retries raise the last exception."""
        # Mock all attempts fail with 503
        mock_response = Mock()
        mock_response.status = 503
        mock_response.headers = {}
        mock_response.json = AsyncMock(return_value={"message": "Service unavailable"})

        mock_session = client.session
        mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch('asyncio.sleep', new_callable=AsyncMock):
            with pytest.raises(ValueError, match="Transient server error"):
                await client._make_authenticated_request("GET", "/test")

        # Should make maximum number of attempts
        assert mock_session.request.call_count == RETRY_MAX_ATTEMPTS

    @pytest.mark.asyncio
    async def test_network_error_retries(self, client):
        """Test that network errors trigger retries."""
        mock_session = client.session

        # Mock the first two calls to raise ClientError, third to succeed
        side_effects = [
            ClientError("Network error 1"),
            ClientError("Network error 2"),
        ]

        # Success response for third attempt
        success_response = Mock()
        success_response.status = 200
        success_response.json = AsyncMock(return_value={"data": "success"})

        success_context = Mock()
        success_context.__aenter__ = AsyncMock(return_value=success_response)
        success_context.__aexit__ = AsyncMock(return_value=None)

        # Configure side effects: first two raise exceptions, third returns context manager
        mock_session.request.side_effect = side_effects + [success_context]

        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await client._make_authenticated_request("GET", "/test")

        assert result == {"data": "success"}
        # Should make 3 requests total
        assert mock_session.request.call_count == 3
        # Should sleep 2 times (between retries)
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_after_header_respected(self, client):
        """Test that Retry-After header is respected."""
        # Mock 429 response with Retry-After header
        mock_response = Mock()
        mock_response.status = 429
        mock_response.headers = {"Retry-After": "5"}
        mock_response.json = AsyncMock(return_value={"message": "Rate limited"})

        success_response = Mock()
        success_response.status = 200
        success_response.json = AsyncMock(return_value={"data": "success"})

        responses = [mock_response, success_response]
        mock_session = client.session
        mock_session.request.return_value.__aenter__ = AsyncMock(side_effect=responses)
        mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            with patch('custom_components.tibber_data.api.client.random.uniform', return_value=0.1):
                result = await client._make_authenticated_request("GET", "/test")

        assert result == {"data": "success"}
        # Should sleep with Retry-After value + jitter
        mock_sleep.assert_called_once()
        sleep_duration = mock_sleep.call_args[0][0]
        assert 5.0 <= sleep_duration <= 5.5  # 5 seconds + max 0.25s jitter + margin

    def test_retry_status_codes_configuration(self):
        """Test that retry configuration matches API specs."""
        assert RETRY_MAX_ATTEMPTS == 5
        assert RETRY_INITIAL_DELAY == 0.4
        assert RETRY_BACKOFF_FACTOR == 2
        assert RETRY_MAX_DELAY == 15.0
        assert RETRY_JITTER_MAX == 0.25

        # Test transient error codes (should retry)
        assert 429 in RETRY_STATUS_CODES
        assert 500 in RETRY_STATUS_CODES
        assert 502 in RETRY_STATUS_CODES
        assert 503 in RETRY_STATUS_CODES

        # Test permanent error codes (should not retry)
        assert 400 in NO_RETRY_STATUS_CODES
        assert 401 in NO_RETRY_STATUS_CODES
        assert 403 in NO_RETRY_STATUS_CODES
        assert 404 in NO_RETRY_STATUS_CODES

    @pytest.mark.asyncio
    async def test_specific_error_messages(self, client):
        """Test that specific error messages are preserved."""
        test_cases = [
            (401, "Invalid or expired token"),
            (403, "Insufficient permissions"),
            (404, "Home not found"),  # when message contains "home"
            (429, "Rate limit exceeded"),
        ]

        for status_code, expected_message in test_cases:
            client.session.request.reset_mock()

            mock_response = Mock()
            mock_response.status = status_code
            mock_response.headers = {}

            if status_code == 404:
                mock_response.json = AsyncMock(return_value={"message": "Home not found"})
            else:
                mock_response.json = AsyncMock(return_value={"message": "Generic error"})

            mock_session = client.session
            mock_session.request.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_session.request.return_value.__aexit__ = AsyncMock(return_value=None)

            if status_code in NO_RETRY_STATUS_CODES:
                # Should raise immediately without retry
                with pytest.raises(ValueError, match=expected_message):
                    await client._make_authenticated_request("GET", "/test")
                assert mock_session.request.call_count == 1
            else:
                # Should retry and then raise
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    with pytest.raises(ValueError, match=expected_message):
                        await client._make_authenticated_request("GET", "/test")
                assert mock_session.request.call_count == RETRY_MAX_ATTEMPTS