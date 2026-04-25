"""Tests for __main__.py edge cases and missing coverage."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from pwpush.__main__ import app, error_json
from pwpush.commands.config import user_config
from pwpush.options import cli_options

runner = CliRunner()


class TestWelcomeScreens:
    """Tests for welcome/help screens."""

    def test_welcome_screen_no_config(self, monkeypatch, tmp_path):
        """Test welcome screen when no config exists."""
        # Ensure no config file exists
        monkeypatch.setattr(
            "pwpush.options.user_config_file", tmp_path / "nonexistent.ini"
        )
        monkeypatch.setitem(cli_options, "json", False)

        result = runner.invoke(app, [])

        assert result.exit_code == 0
        assert "Password Pusher CLI" in result.output
        assert "Quick Start" in result.output

    def test_help_with_config_no_login(self, monkeypatch, tmp_path):
        """Test help screen when config exists but not logged in."""
        # Create a config file without login
        config_file = tmp_path / "config.ini"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("""
[instance]
url = https://eu.pwpush.com
email = Not Set
token = Not Set

[expiration]
expire_after_days = Not Set
expire_after_views = Not Set

[cli]
json = False
verbose = False
pretty = False
debug = False
""")
        monkeypatch.setattr("pwpush.options.user_config_file", config_file)

        # Load this config
        from pwpush.options import load_config

        load_config()

        result = runner.invoke(app, [])

        assert result.exit_code == 0
        # When not logged in, should show welcome screen
        assert "Password Pusher CLI" in result.output

    def test_help_with_config_and_login(self, monkeypatch, tmp_path):
        """Test help screen when logged in."""
        # Create a config file with login
        config_file = tmp_path / "config.ini"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("""
[instance]
url = https://eu.pwpush.com
email = user@example.com
token = some-token

[expiration]
expire_after_days = Not Set
expire_after_views = Not Set

[cli]
json = False
verbose = False
pretty = False
debug = False
""")
        monkeypatch.setattr("pwpush.options.user_config_file", config_file)

        from pwpush.options import load_config

        load_config()

        result = runner.invoke(app, [])

        assert result.exit_code == 0
        # When logged in, should show help with config
        assert "Password Pusher CLI" in result.output
        assert "Available Commands" in result.output


class TestErrorJson:
    """Tests for error_json function."""

    def test_error_json_with_status_code(self, monkeypatch):
        """Test error_json with status code."""
        import sys
        from io import StringIO

        monkeypatch.setitem(cli_options, "json", True)

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        try:
            error_json("Something went wrong", 500)
        except SystemExit:
            pass  # Expected
        finally:
            sys.stdout = old_stdout

        output = captured_output.getvalue()
        assert (
            "500" in output
            or "Something went wrong" in output
            or "error" in output.lower()
        )

    def test_error_json_without_status_code(self, monkeypatch):
        """Test error_json without status code."""
        import sys
        from io import StringIO

        monkeypatch.setitem(cli_options, "json", True)

        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        try:
            error_json("Generic error")
        except SystemExit:
            pass  # Expected
        finally:
            sys.stdout = old_stdout

        output = captured_output.getvalue()
        assert "error" in output.lower()

    def test_error_json_pretty_output(self, monkeypatch):
        """Test error_json with pretty output."""
        import sys
        from io import StringIO

        monkeypatch.setitem(cli_options, "json", True)
        monkeypatch.setitem(cli_options, "pretty", True)

        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        try:
            error_json("Pretty error", 400)
        except SystemExit:
            pass  # Expected
        finally:
            sys.stdout = old_stdout

        output = captured_output.getvalue()
        assert "error" in output.lower()

    def test_error_json_human_readable(self, monkeypatch):
        """Test error_json in human-readable mode."""
        import sys
        from io import StringIO

        monkeypatch.setitem(cli_options, "json", False)

        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        try:
            error_json("Human error", 404)
        except SystemExit:
            pass  # Expected
        finally:
            sys.stdout = old_stdout

        output = captured_output.getvalue()
        assert "404" in output or "Human error" in output or "error" in output.lower()


class TestUpdateCliOptions:
    """Tests for update_cli_options function."""

    def test_update_verbose(self, monkeypatch):
        """Test update_cli_options with verbose."""
        from pwpush.__main__ import update_cli_options, verbose_output

        monkeypatch.setitem(cli_options, "verbose", False)

        update_cli_options(verbose=True)

        assert cli_options["verbose"] is True


class TestMakeRequestWithAccountId:
    """Tests for make_request with account_id injection."""

    def test_make_request_adds_account_id(self, monkeypatch):
        """Test that account_id is added to POST requests."""
        monkeypatch.setitem(user_config["instance"], "account_id", "123")

        with patch("pwpush.__main__.send_request") as mock_send:
            mock_send.return_value = MagicMock()
            mock_send.return_value.status_code = 200

            from pwpush.__main__ import make_request

            make_request(
                "POST",
                "/api/test",
                post_data={"payload": "test"},
            )

            # Check that account_id was added
            call_kwargs = mock_send.call_args[1]
            assert call_kwargs["post_data"]["account_id"] == "123"

    def test_make_request_no_account_id_when_not_set(self, monkeypatch):
        """Test that account_id is not added when 'Not Set'."""
        monkeypatch.setitem(user_config["instance"], "account_id", "Not Set")

        with patch("pwpush.__main__.send_request") as mock_send:
            mock_send.return_value = MagicMock()
            mock_send.return_value.status_code = 200

            from pwpush.__main__ import make_request

            make_request(
                "POST",
                "/api/test",
                post_data={"payload": "test"},
            )

            # Check that account_id was NOT added
            call_kwargs = mock_send.call_args[1]
            assert "account_id" not in call_kwargs["post_data"]

    def test_make_request_no_account_id_for_get(self, monkeypatch):
        """Test that account_id is not added for GET requests."""
        monkeypatch.setitem(user_config["instance"], "account_id", "123")

        with patch("pwpush.__main__.send_request") as mock_send:
            mock_send.return_value = MagicMock()
            mock_send.return_value.status_code = 200

            from pwpush.__main__ import make_request

            make_request(
                "GET",
                "/api/test",
            )

            # Check that account_id was NOT added for GET (post_data is None for GET)
            call_kwargs = mock_send.call_args[1]
            post_data = call_kwargs.get("post_data")
            assert post_data is None or "account_id" not in post_data


class TestVersionCallback:
    """Tests for version callback."""

    def test_version_flag(self):
        """Test --version flag."""
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "pwpush" in result.output
        assert "version" in result.output.lower()


class TestPushErrorResponse:
    """Tests for push command error responses."""

    def test_push_non_201_response_json(self, monkeypatch):
        """Test push with non-201 response in JSON mode."""
        with patch("pwpush.__main__.current_api_profile", return_value="legacy"):
            with patch("pwpush.__main__.make_request") as mock:
                mock.return_value = MagicMock()
                mock.return_value.status_code = 422
                mock.return_value.text = "Validation failed"
                mock.return_value.json.return_value = {"error": "Invalid payload"}

                result = runner.invoke(
                    app, ["push", "--secret", "test", "--json", "--passphrase", "pass"]
                )

        assert result.exit_code == 1
        assert "Invalid payload" in result.output

    def test_push_non_201_response_no_json(self, monkeypatch):
        """Test push with non-201 response that has no JSON."""
        with patch("pwpush.__main__.current_api_profile", return_value="legacy"):
            with patch("pwpush.__main__.make_request") as mock:
                mock.return_value = MagicMock()
                mock.return_value.status_code = 500
                mock.return_value.text = "Internal error"
                mock.return_value.json.side_effect = ValueError("Not JSON")

                result = runner.invoke(
                    app, ["push", "--secret", "test", "--passphrase", "pass"]
                )

        assert result.exit_code == 1
        assert "Internal error" in result.output
