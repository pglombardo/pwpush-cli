"""Tests for network error handling in api/client.py."""

from unittest.mock import MagicMock, patch

import pytest
import requests
from typer.testing import CliRunner

from pwpush.__main__ import app
from pwpush.api.client import (
    _sanitize_headers,
    build_auth_headers,
    get_retry_delay,
    is_rate_limit_error,
    normalize_base_url,
    send_request,
)

runner = CliRunner()


class TestHeaderSanitization:
    """Tests for _sanitize_headers function."""

    def test_sanitize_headers_masks_authorization(self):
        """Test that Authorization header is masked."""
        headers = {
            "Authorization": "Bearer secret-token",
            "Content-Type": "application/json",
        }
        result = _sanitize_headers(headers)
        assert result["Authorization"] == "***REDACTED***"
        assert result["Content-Type"] == "application/json"

    def test_sanitize_headers_masks_x_user_token(self):
        """Test that X-User-Token header is masked."""
        headers = {"X-User-Token": "secret-token", "X-User-Email": "user@example.com"}
        result = _sanitize_headers(headers)
        assert result["X-User-Token"] == "***REDACTED***"
        assert result["X-User-Email"] == "user@example.com"

    def test_sanitize_headers_preserves_original(self):
        """Test that original headers dict is not modified."""
        headers = {"Authorization": "Bearer secret-token"}
        result = _sanitize_headers(headers)
        assert headers["Authorization"] == "Bearer secret-token"
        assert result["Authorization"] == "***REDACTED***"


class TestNormalizeBaseUrl:
    """Tests for normalize_base_url function."""

    def test_removes_trailing_slash(self):
        """Test that trailing slash is removed."""
        assert normalize_base_url("https://example.com/") == "https://example.com"

    def test_no_trailing_slash_unchanged(self):
        """Test URL without trailing slash is unchanged."""
        assert normalize_base_url("https://example.com") == "https://example.com"

    def test_multiple_trailing_slashes_removed(self):
        """Test that multiple trailing slashes are removed."""
        assert normalize_base_url("https://example.com///") == "https://example.com"


class TestBuildAuthHeaders:
    """Tests for build_auth_headers function."""

    def test_valid_email_and_token(self):
        """Test headers with valid email and token."""
        result = build_auth_headers("user@example.com", "valid-token")
        assert result["Authorization"] == "Bearer valid-token"
        assert result["X-User-Email"] == "user@example.com"
        assert result["X-User-Token"] == "valid-token"

    def test_not_set_token_returns_empty(self):
        """Test that 'Not Set' token returns empty headers."""
        result = build_auth_headers("user@example.com", "Not Set")
        assert result == {}

    def test_empty_token_returns_empty(self):
        """Test that empty token returns empty headers."""
        result = build_auth_headers("user@example.com", "")
        assert result == {}

    def test_whitespace_token_returns_empty(self):
        """Test that whitespace-only token returns empty headers."""
        result = build_auth_headers("user@example.com", "   ")
        assert result == {}

    def test_not_set_email_still_has_authz_header(self):
        """Test that 'Not Set' email still produces Authorization header."""
        result = build_auth_headers("Not Set", "valid-token")
        assert result["Authorization"] == "Bearer valid-token"
        assert "X-User-Email" not in result
        assert "X-User-Token" not in result


class TestSendRequestErrors:
    """Tests for send_request error handling."""

    @patch("pwpush.api.client.requests.get")
    @patch("pwpush.api.client.rprint")
    def test_timeout_error(self, mock_rprint, mock_get):
        """Test that timeout raises typer.Exit."""
        mock_get.side_effect = requests.exceptions.Timeout()

        import typer

        with pytest.raises(typer.Exit) as exc_info:
            send_request(
                "GET",
                base_url="https://example.com",
                path="/api/test",
                email="user@example.com",
                token="token",
            )
        assert exc_info.value.exit_code == 1
        mock_rprint.assert_called_once()
        assert "timed out" in str(mock_rprint.call_args).lower()

    @patch("pwpush.api.client.requests.get")
    @patch("pwpush.api.client.rprint")
    def test_connection_error(self, mock_rprint, mock_get):
        """Test that connection error raises typer.Exit."""
        import typer

        mock_get.side_effect = requests.exceptions.ConnectionError()

        with pytest.raises(typer.Exit) as exc_info:
            send_request(
                "GET",
                base_url="https://example.com",
                path="/api/test",
                email="user@example.com",
                token="token",
            )
        assert exc_info.value.exit_code == 1
        mock_rprint.assert_called_once()
        assert "could not connect" in str(mock_rprint.call_args).lower()

    @patch("pwpush.api.client.requests.get")
    @patch("pwpush.api.client.rprint")
    def test_generic_request_exception(self, mock_rprint, mock_get):
        """Test that generic request exception raises typer.Exit."""
        import typer

        mock_get.side_effect = requests.exceptions.RequestException(
            "Something went wrong"
        )

        with pytest.raises(typer.Exit) as exc_info:
            send_request(
                "GET",
                base_url="https://example.com",
                path="/api/test",
                email="user@example.com",
                token="token",
            )
        assert exc_info.value.exit_code == 1
        mock_rprint.assert_called_once()
        assert "network request failed" in str(mock_rprint.call_args).lower()


class TestSendRequestDebugOutput:
    """Tests for send_request debug output."""

    @patch("pwpush.api.client.requests.get")
    @patch("pwpush.api.client.rprint")
    def test_debug_output_with_auth(self, mock_rprint, mock_get):
        """Test that debug output shows redacted headers."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        send_request(
            "GET",
            base_url="https://example.com",
            path="/api/test",
            email="user@example.com",
            token="secret-token",
            debug=True,
        )

        # Check that debug output was printed
        debug_calls = [str(call) for call in mock_rprint.call_args_list]
        assert any("Communicating with" in str(call) for call in debug_calls)
        assert any("***REDACTED***" in str(call) for call in debug_calls)

    @patch("pwpush.api.client.requests.get")
    @patch("pwpush.api.client.rprint")
    def test_debug_output_ssl_warning(self, mock_rprint, mock_get):
        """Test that debug output shows SSL warning when verify=False."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        send_request(
            "GET",
            base_url="https://example.com",
            path="/api/test",
            email="user@example.com",
            token="token",
            debug=True,
            verify=False,
        )

        debug_calls = [str(call) for call in mock_rprint.call_args_list]
        assert any(
            "SSL certificate verification is disabled" in str(call)
            for call in debug_calls
        )


class TestUnsupportedMethod:
    """Tests for unsupported HTTP method."""

    @patch("pwpush.api.client.rprint")
    def test_unsupported_method_raises_exit(self, mock_rprint):
        """Test that unsupported HTTP method raises typer.Exit."""
        import typer

        with pytest.raises(typer.Exit) as exc_info:
            send_request(
                "PUT",
                base_url="https://example.com",
                path="/api/test",
                email="user@example.com",
                token="token",
            )
        assert exc_info.value.exit_code == 1
        mock_rprint.assert_called_once()
        assert "Unsupported HTTP method" in str(mock_rprint.call_args)


class TestRateLimitDetection:
    """Tests for rate limit error detection."""

    def test_is_rate_limit_error_with_retry_after_header(self):
        """Test that 403 with Retry-After header is detected as rate limit."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_response.headers = {"retry-after": "5"}

        assert is_rate_limit_error(mock_response) is True

    def test_is_rate_limit_error_with_rate_limit_message(self):
        """Test that 403 with 'rate limit' in body is detected."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Rate Limit Exceeded"
        mock_response.headers = {}

        assert is_rate_limit_error(mock_response) is True

    def test_is_rate_limit_error_with_throttled_message(self):
        """Test that 403 with 'throttled' in body is detected."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Request throttled"
        mock_response.headers = {}

        assert is_rate_limit_error(mock_response) is True

    def test_is_rate_limit_error_with_too_many_requests(self):
        """Test that 403 with 'too many requests' in body is detected."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Too many requests"
        mock_response.headers = {}

        assert is_rate_limit_error(mock_response) is True

    def test_is_rate_limit_error_not_403(self):
        """Test that non-403 responses are not rate limit errors."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.headers = {}

        assert is_rate_limit_error(mock_response) is False

    def test_is_rate_limit_error_403_but_not_rate_limit(self):
        """Test that 403 without rate limit indicators is not a rate limit error."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden - Invalid token"
        mock_response.headers = {}

        assert is_rate_limit_error(mock_response) is False


class TestRetryDelayCalculation:
    """Tests for retry delay calculation."""

    def test_get_retry_delay_uses_retry_after_header(self):
        """Test that Retry-After header value is used when present."""
        mock_response = MagicMock()
        mock_response.headers = {"retry-after": "10"}

        delay = get_retry_delay(mock_response, attempt=0)

        assert delay == 10.0

    def test_get_retry_delay_caps_at_max_delay(self):
        """Test that Retry-After values above max are capped."""
        mock_response = MagicMock()
        mock_response.headers = {"retry-after": "100"}  # Above MAX_BACKOFF_DELAY (30)

        delay = get_retry_delay(mock_response, attempt=0)

        assert delay == 30.0  # Should be capped

    def test_get_retry_delay_exponential_backoff(self):
        """Test exponential backoff calculation without header."""
        mock_response = MagicMock()
        mock_response.headers = {}

        # Test that delay increases with attempt number
        delay_0 = get_retry_delay(mock_response, attempt=0, base_delay=1.0)
        delay_1 = get_retry_delay(mock_response, attempt=1, base_delay=1.0)
        delay_2 = get_retry_delay(mock_response, attempt=2, base_delay=1.0)

        # Delay should generally increase (with jitter, so we check ranges)
        assert 1.0 <= delay_0 <= 30.0
        assert 1.0 <= delay_1 <= 30.0
        assert 1.0 <= delay_2 <= 30.0

        # Higher attempts should have higher potential delay
        # (1 * 2^0 = 1, 1 * 2^1 = 2, 1 * 2^2 = 4)
        assert delay_0 < delay_2 + 1  # Allow for jitter variance

    def test_get_retry_delay_minimum_is_base_delay(self):
        """Test that delay is at least the base delay."""
        mock_response = MagicMock()
        mock_response.headers = {}

        # With full jitter, delay could be very small, but we enforce minimum
        delay = get_retry_delay(mock_response, attempt=0, base_delay=2.0)

        assert delay >= 2.0


class TestRateLimitRetryLogic:
    """Tests for rate limit retry behavior in send_request."""

    @patch("pwpush.api.client.requests.post")
    @patch("pwpush.api.client.time.sleep")
    def test_retries_on_rate_limit_and_succeeds(self, mock_sleep, mock_post):
        """Test that request is retried on rate limit and eventually succeeds."""
        # First two calls return 403 rate limit, third succeeds
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 403
        rate_limit_response.text = "Rate Limit Exceeded"
        rate_limit_response.headers = {"retry-after": "1"}

        success_response = MagicMock()
        success_response.status_code = 201
        success_response.json.return_value = {"url": "https://example.com/p/abc"}

        mock_post.side_effect = [
            rate_limit_response,
            rate_limit_response,
            success_response,
        ]

        response = send_request(
            "POST",
            base_url="https://example.com",
            path="/p.json",
            email="user@example.com",
            token="token",
            post_data={"password": {"payload": "secret"}},
        )

        assert response.status_code == 201
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2  # Slept between retries

    @patch("pwpush.api.client.requests.post")
    @patch("pwpush.api.client.time.sleep")
    def test_rate_limit_callback_invoked(self, mock_sleep, mock_post):
        """Test that on_rate_limit_retry callback is called."""
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 403
        rate_limit_response.text = "Rate Limit Exceeded"
        rate_limit_response.headers = {"retry-after": "1"}

        success_response = MagicMock()
        success_response.status_code = 201

        mock_post.side_effect = [rate_limit_response, success_response]

        callback_calls = []

        def callback(attempt, delay, response):
            callback_calls.append((attempt, delay, response.status_code))

        response = send_request(
            "POST",
            base_url="https://example.com",
            path="/p.json",
            email="user@example.com",
            token="token",
            post_data={"password": {"payload": "secret"}},
            on_rate_limit_retry=callback,
        )

        assert len(callback_calls) == 1
        assert callback_calls[0][0] == 1  # attempt number
        assert callback_calls[0][1] == 1.0  # delay from retry-after header
        assert callback_calls[0][2] == 403  # response status

    @patch("pwpush.api.client.requests.post")
    @patch("pwpush.api.client.time.sleep")
    @patch("pwpush.api.client.rprint")
    def test_returns_final_rate_limit_response_after_exhausting_retries(
        self, mock_rprint, mock_sleep, mock_post
    ):
        """Test that final 403 response is returned after all retries fail."""
        import typer

        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 403
        rate_limit_response.text = "Rate Limit Exceeded"
        rate_limit_response.headers = {"retry-after": "1"}

        # All calls return rate limit
        mock_post.return_value = rate_limit_response

        # The push command should handle the error response and exit with code 1
        # Here we're just testing that send_request returns the response
        response = send_request(
            "POST",
            base_url="https://example.com",
            path="/p.json",
            email="user@example.com",
            token="token",
            post_data={"password": {"payload": "secret"}},
            max_retries=2,
        )

        # Should have made 3 requests (initial + 2 retries)
        assert mock_post.call_count == 3
        assert response.status_code == 403
        assert mock_sleep.call_count == 2

    @patch("pwpush.api.client.requests.get")
    @patch("pwpush.api.client.time.sleep")
    def test_no_retry_on_non_rate_limit_403(self, mock_sleep, mock_get):
        """Test that non-rate-limit 403 errors are not retried."""
        forbidden_response = MagicMock()
        forbidden_response.status_code = 403
        forbidden_response.text = "Forbidden - Invalid credentials"
        forbidden_response.headers = {}  # No retry-after header

        mock_get.return_value = forbidden_response

        response = send_request(
            "GET",
            base_url="https://example.com",
            path="/api/test",
            email="user@example.com",
            token="token",
        )

        assert response.status_code == 403
        assert mock_get.call_count == 1  # Only one request, no retries
        assert mock_sleep.call_count == 0  # No sleep, no retries

    @patch("pwpush.api.client.requests.post")
    @patch("pwpush.api.client.time.sleep")
    def test_respects_max_retries_parameter(self, mock_sleep, mock_post):
        """Test that max_retries parameter controls retry count."""
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 403
        rate_limit_response.text = "Rate Limit Exceeded"
        rate_limit_response.headers = {"retry-after": "0.1"}

        mock_post.return_value = rate_limit_response

        send_request(
            "POST",
            base_url="https://example.com",
            path="/p.json",
            email="user@example.com",
            token="token",
            post_data={"password": {"payload": "secret"}},
            max_retries=1,  # Only 1 retry
        )

        # Should have made 2 requests (initial + 1 retry)
        assert mock_post.call_count == 2
        assert mock_sleep.call_count == 1


class TestRateLimitCLIIntegration:
    """Tests for CLI integration with rate limit handling."""

    @patch("pwpush.api.client.requests.post")
    @patch("pwpush.api.client.requests.get")
    @patch("pwpush.api.client.time.sleep")
    def test_push_exits_with_code_1_on_rate_limit_after_retries(
        self, mock_sleep, mock_get, mock_post
    ):
        """Test that push command exits with code 1 when rate limit persists after all retries."""
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 403
        rate_limit_response.text = "Rate Limit Exceeded"
        rate_limit_response.headers = {"retry-after": "0.01"}

        # All POST calls return rate limit
        mock_post.return_value = rate_limit_response

        result = runner.invoke(
            app,
            ["push", "--secret", "test-secret", "--json"],
        )

        # Should exit with code 1 (error)
        assert result.exit_code == 1
        # Should have made multiple requests (initial + retries)
        assert mock_post.call_count > 1

    @patch("pwpush.api.client.requests.post")
    @patch("pwpush.api.client.requests.get")
    @patch("pwpush.api.client.time.sleep")
    def test_push_outputs_error_to_stderr_on_rate_limit(
        self, mock_sleep, mock_get, mock_post
    ):
        """Test that rate limit errors are output properly (not just silently)."""
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 403
        rate_limit_response.text = "Rate Limit Exceeded"
        rate_limit_response.headers = {"retry-after": "0.01"}

        mock_post.return_value = rate_limit_response

        result = runner.invoke(
            app,
            ["push", "--secret", "test-secret", "--json"],
        )

        # Should exit with error
        assert result.exit_code == 1
        # Output should contain error information
        assert (
            "403" in result.output
            or "Rate Limit" in result.output
            or "error" in result.output.lower()
        )

    @patch("pwpush.api.client.requests.post")
    @patch("pwpush.api.client.requests.get")
    @patch("pwpush.api.client.time.sleep")
    def test_push_success_after_rate_limit_retry(self, mock_sleep, mock_get, mock_post):
        """Test that push succeeds when rate limit clears on retry."""
        rate_limit_response = MagicMock()
        rate_limit_response.status_code = 403
        rate_limit_response.text = "Rate Limit Exceeded"
        rate_limit_response.headers = {"retry-after": "0.01"}

        success_response = MagicMock()
        success_response.status_code = 201
        success_response.json.return_value = {"url_token": "abc123"}

        # First call rate limited, second succeeds
        mock_post.side_effect = [rate_limit_response, success_response]

        # Mock the GET request for preview
        preview_response = MagicMock()
        preview_response.status_code = 200
        preview_response.json.return_value = {"url": "https://example.com/p/abc123"}
        mock_get.return_value = preview_response

        result = runner.invoke(
            app,
            ["push", "--secret", "test-secret", "--json"],
        )

        # Should succeed after retry
        assert result.exit_code == 0
        assert mock_post.call_count == 2  # Initial + 1 retry
        assert mock_sleep.call_count == 1  # Slept before retry
