"""Tests for file push error handling and edge cases."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from pwpush.__main__ import app
from pwpush.commands.config import user_config

runner = CliRunner()


class TestFilePushFileNotFound:
    """Tests for file push FileNotFoundError handling."""

    def test_file_not_found_error_json(self, monkeypatch):
        """Test file not found error in JSON mode."""
        monkeypatch.setitem(user_config["instance"], "email", "user@example.test")
        monkeypatch.setitem(user_config["instance"], "token", "token-value")

        with patch("pwpush.__main__.current_api_profile", return_value="legacy"):
            result = runner.invoke(
                app, ["push-file", "--json", "/nonexistent/file.txt"]
            )

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_file_not_found_error_human(self, monkeypatch):
        """Test file not found error in human-readable mode."""
        monkeypatch.setitem(user_config["instance"], "email", "user@example.test")
        monkeypatch.setitem(user_config["instance"], "token", "token-value")

        with patch("pwpush.__main__.current_api_profile", return_value="legacy"):
            result = runner.invoke(app, ["push-file", "/nonexistent/file.txt"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()


class TestFilePushPermissionError:
    """Tests for file push PermissionError handling."""

    def test_permission_denied_error(self, monkeypatch):
        """Test permission denied error handling."""
        monkeypatch.setitem(user_config["instance"], "email", "user@example.test")
        monkeypatch.setitem(user_config["instance"], "token", "token-value")

        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Remove read permissions
            os.chmod(tmp_path, 0o000)

            with patch("pwpush.__main__.current_api_profile", return_value="legacy"):
                result = runner.invoke(app, ["push-file", "--json", tmp_path])

            assert result.exit_code == 1
            assert "permission" in result.output.lower()
        finally:
            # Restore permissions for cleanup
            os.chmod(tmp_path, 0o644)
            os.unlink(tmp_path)


class TestFilePushGenericError:
    """Tests for file push generic error handling."""

    def test_generic_error_with_json(self, monkeypatch):
        """Test generic error handling in JSON mode."""
        monkeypatch.setitem(user_config["instance"], "email", "user@example.test")
        monkeypatch.setitem(user_config["instance"], "token", "token-value")

        # Create a directory with the same name to cause an error
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file path that points to the directory (not a file)
            with patch("pwpush.__main__.current_api_profile", return_value="legacy"):
                result = runner.invoke(app, ["push-file", "--json", tmpdir])

            # This will fail because it's a directory, not a file
            assert result.exit_code == 1


class TestFilePushEmailNotifications:
    """Tests for file push email notifications."""

    def test_file_push_with_notify_unauthenticated(self, monkeypatch):
        """Test that --notify requires authentication for file push."""
        monkeypatch.setitem(user_config["instance"], "email", "user@example.test")
        monkeypatch.setitem(user_config["instance"], "token", "Not Set")

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            tmp.write("test content")
            tmp_path = tmp.name

        try:
            with patch("pwpush.__main__.current_api_profile", return_value="legacy"):
                result = runner.invoke(
                    app,
                    ["push-file", "--notify", "admin@example.com", tmp_path],
                )

            # push-file requires a token even without --notify, so this should fail
            assert result.exit_code == 1
            # Check for either "require" or "API token" in output
            assert (
                "require" in result.output.lower() or "token" in result.output.lower()
            )
        finally:
            os.unlink(tmp_path)

    def test_file_push_with_notify_when_disabled(self, monkeypatch):
        """Test file push notification shows warning when disabled."""
        monkeypatch.setitem(user_config["instance"], "email", "user@example.test")
        monkeypatch.setitem(user_config["instance"], "token", "valid-token")

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            tmp.write("test content")
            tmp_path = tmp.name

        try:
            mock_capabilities = {
                "api_version": "2.1.0",
                "features": {"email_auto_dispatch": False},
            }
            monkeypatch.setattr(
                "pwpush.commands.push.detect_api_capabilities",
                lambda **kwargs: mock_capabilities,
            )

            with patch("pwpush.__main__.current_api_profile", return_value="legacy"):
                with patch("pwpush.__main__.make_request") as mock:
                    mock.return_value = MagicMock()
                    mock.return_value.status_code = 201
                    mock.return_value.json.return_value = {
                        "url_token": "test-token",
                        "url": "https://test.com/f/test",
                    }
                    result = runner.invoke(
                        app,
                        [
                            "push-file",
                            "--notify",
                            "admin@example.com",
                            tmp_path,
                        ],
                    )

            assert result.exit_code == 0
            assert "not enabled" in result.output.lower()
        finally:
            os.unlink(tmp_path)

    def test_file_push_with_notify_when_enabled(self, monkeypatch):
        """Test file push notification when feature is enabled."""
        monkeypatch.setitem(user_config["instance"], "email", "user@example.test")
        monkeypatch.setitem(user_config["instance"], "token", "valid-token")

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            tmp.write("test content")
            tmp_path = tmp.name

        try:
            mock_capabilities = {
                "api_version": "2.1.0",
                "features": {"email_auto_dispatch": True},
            }
            monkeypatch.setattr(
                "pwpush.commands.push.detect_api_capabilities",
                lambda **kwargs: mock_capabilities,
            )

            with patch("pwpush.__main__.current_api_profile", return_value="legacy"):
                with patch("pwpush.__main__.make_request") as mock:
                    mock.return_value = MagicMock()
                    mock.return_value.status_code = 201
                    mock.return_value.json.return_value = {
                        "url_token": "test-token",
                        "url": "https://test.com/f/test",
                    }
                    result = runner.invoke(
                        app,
                        [
                            "push-file",
                            "--notify",
                            "admin@example.com",
                            "--notify-locale",
                            "es",
                            tmp_path,
                        ],
                    )

            assert result.exit_code == 0
        finally:
            os.unlink(tmp_path)


class TestFilePushErrorResponse:
    """Tests for file push API error responses."""

    def test_file_push_non_201_response_json(self, monkeypatch):
        """Test file push with non-201 response in JSON mode."""
        monkeypatch.setitem(user_config["instance"], "email", "user@example.test")
        monkeypatch.setitem(user_config["instance"], "token", "token-value")

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            tmp.write("test content")
            tmp_path = tmp.name

        try:
            with patch("pwpush.__main__.current_api_profile", return_value="legacy"):
                with patch("pwpush.__main__.make_request") as mock:
                    mock.return_value = MagicMock()
                    mock.return_value.status_code = 422
                    mock.return_value.text = "Unprocessable Entity"
                    mock.return_value.json.return_value = {"error": "Invalid file type"}
                    result = runner.invoke(app, ["push-file", "--json", tmp_path])

            assert result.exit_code == 1
            assert "Invalid file type" in result.output
        finally:
            os.unlink(tmp_path)

    def test_file_push_non_201_response_no_json(self, monkeypatch):
        """Test file push with non-201 response that has no JSON body."""
        monkeypatch.setitem(user_config["instance"], "email", "user@example.test")
        monkeypatch.setitem(user_config["instance"], "token", "token-value")

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            tmp.write("test content")
            tmp_path = tmp.name

        try:
            with patch("pwpush.__main__.current_api_profile", return_value="legacy"):
                with patch("pwpush.__main__.make_request") as mock:
                    mock.return_value = MagicMock()
                    mock.return_value.status_code = 500
                    mock.return_value.text = "Internal Server Error"
                    # json() raises exception
                    mock.return_value.json.side_effect = ValueError("Not JSON")
                    result = runner.invoke(app, ["push-file", "--json", tmp_path])

            assert result.exit_code == 1
            assert "Internal Server Error" in result.output
        finally:
            os.unlink(tmp_path)


class TestFilePushWithV2Profile:
    """Tests for file push with v2 API profile."""

    def test_file_push_v2_profile(self, monkeypatch):
        """Test file push with v2 API profile."""
        monkeypatch.setitem(user_config["instance"], "email", "user@example.test")
        monkeypatch.setitem(user_config["instance"], "token", "token-value")

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            tmp.write("test content")
            tmp_path = tmp.name

        try:
            with patch("pwpush.__main__.current_api_profile", return_value="v2"):
                with patch("pwpush.__main__.make_request") as mock:
                    mock.return_value = MagicMock()
                    mock.return_value.status_code = 201
                    mock.return_value.json.return_value = {
                        "url_token": "test-token",
                        "url": "https://test.com/f/test",
                    }
                    result = runner.invoke(app, ["push-file", tmp_path])

            assert result.exit_code == 0
            assert "https://test.com/f/test" in result.output
        finally:
            os.unlink(tmp_path)
