"""Tests for network error handling in api/client.py."""

from unittest.mock import MagicMock, patch

import pytest
import requests
from typer.testing import CliRunner

from pwpush.__main__ import app
from pwpush.api.client import (
    _sanitize_headers,
    build_auth_headers,
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
