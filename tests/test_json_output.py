"""Tests for JSON output across all commands."""

import json
import re
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from pwpush.__main__ import app
from pwpush.options import cli_options, default_config, json_output, user_config

runner = CliRunner()


def strip_ansi(text: str) -> str:
    """Strip ANSI escape sequences from text."""
    ansi_escape = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


@pytest.fixture(autouse=True)
def reset_cli_options():
    """Reset cli_options before each test to avoid state leakage."""
    # Store original values
    original_options = dict(cli_options)
    # Reset to defaults
    cli_options.clear()
    cli_options.update(
        {"json": False, "verbose": False, "pretty": False, "debug": False}
    )
    yield
    # Restore original values after test
    cli_options.clear()
    cli_options.update(original_options)


class TestJsonFlag:
    """Test --json flag produces valid JSON output."""

    def test_config_show_with_json_flag(self):
        """Test config show outputs valid JSON with --json flag."""
        result = runner.invoke(app, ["config", "show", "--json"])

        assert result.exit_code == 0
        # Should be valid JSON
        output = json.loads(result.stdout)
        assert "instance" in output
        assert "cli" in output

    def test_version_flag_outputs_text(self):
        """Test --version flag outputs text (not JSON)."""
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "pwpush version:" in result.stdout


class TestJsonErrorOutput:
    """Test JSON error output when --json flag is set."""

    def test_list_error_json_not_logged_in(self, monkeypatch, tmp_path):
        """Test list outputs JSON error when not logged in with --json flag."""
        # Isolate config to ensure no token is set
        config_file = tmp_path / "config.ini"
        monkeypatch.setattr("pwpush.options.user_config_file", config_file)
        monkeypatch.setattr("pwpush.commands.config.user_config_file", config_file)

        user_config.clear()
        user_config.read_dict(default_config)

        result = runner.invoke(app, ["list", "--json"])

        assert result.exit_code == 1
        # Should be valid JSON with error field
        output = json.loads(result.stdout)
        assert "error" in output

    def test_audit_error_json_not_logged_in(self, monkeypatch, tmp_path):
        """Test audit outputs JSON error when not logged in with --json flag."""
        config_file = tmp_path / "config.ini"
        monkeypatch.setattr("pwpush.options.user_config_file", config_file)
        monkeypatch.setattr("pwpush.commands.config.user_config_file", config_file)

        user_config.clear()
        user_config.read_dict(default_config)

        result = runner.invoke(app, ["audit", "abc123", "--json"])

        assert result.exit_code == 1
        # Should be valid JSON with error field
        output = json.loads(result.stdout)
        assert "error" in output

    def test_list_error_json_includes_status_code(self, monkeypatch, tmp_path):
        """Test JSON error includes status_code when applicable."""
        config_file = tmp_path / "config.ini"
        monkeypatch.setattr("pwpush.options.user_config_file", config_file)
        monkeypatch.setattr("pwpush.commands.config.user_config_file", config_file)

        user_config.clear()
        user_config.read_dict(default_config)
        # Set up a token so we don't get auth error
        user_config["instance"]["token"] = "test-token"
        user_config["instance"]["email"] = "test@test.com"

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "not-found"}
        mock_response.text = "not-found"

        with patch("pwpush.__main__.make_request", return_value=mock_response):
            result = runner.invoke(app, ["expire", "invalid-token", "--json"])

            assert result.exit_code == 1
            output = json.loads(result.stdout)
            assert "error" in output
            assert "status_code" in output
            assert output["status_code"] == 404


class TestConfigJsonSetting:
    """Test that config json=True makes commands respect JSON output."""

    def test_json_output_helper_returns_true_when_config_set(
        self, monkeypatch, tmp_path
    ):
        """Test json_output() returns True when config has json=True."""
        config_file = tmp_path / "config.ini"
        monkeypatch.setattr("pwpush.options.user_config_file", config_file)
        monkeypatch.setattr("pwpush.commands.config.user_config_file", config_file)

        from pwpush.options import save_config

        user_config["cli"]["json"] = "True"
        save_config()

        assert json_output() is True

    def test_json_output_helper_returns_false_when_config_not_set(
        self, monkeypatch, tmp_path
    ):
        """Test json_output() returns False when config has json=False."""
        config_file = tmp_path / "config.ini"
        monkeypatch.setattr("pwpush.options.user_config_file", config_file)
        monkeypatch.setattr("pwpush.commands.config.user_config_file", config_file)

        from pwpush.options import save_config

        user_config["cli"]["json"] = "False"
        save_config()
        # Ensure CLI options don't override
        cli_options["json"] = False

        assert json_output() is False

    def test_cli_options_override_config(self):
        """Test that CLI --json flag overrides config setting."""
        # Set config to False via CLI options
        cli_options["json"] = False
        assert json_output() is False

        # Set CLI option to True
        cli_options["json"] = True
        assert json_output() is True


class TestAllCommandsHaveJsonOption:
    """Test that all relevant commands have --json option."""

    def test_push_has_json_option(self):
        """Test push command has --json option in help."""
        result = runner.invoke(app, ["push", "--help"])
        assert result.exit_code == 0
        assert "--json" in strip_ansi(result.stdout)

    def test_push_file_has_json_option(self):
        """Test push-file command has --json option in help."""
        result = runner.invoke(app, ["push-file", "--help"])
        assert result.exit_code == 0
        assert "--json" in strip_ansi(result.stdout)

    def test_list_has_json_option(self):
        """Test list command has --json option in help."""
        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0
        assert "--json" in strip_ansi(result.stdout)

    def test_audit_has_json_option(self):
        """Test audit command has --json option in help."""
        result = runner.invoke(app, ["audit", "--help"])
        assert result.exit_code == 0
        assert "--json" in strip_ansi(result.stdout)

    def test_expire_has_json_option(self):
        """Test expire command has --json option in help."""
        result = runner.invoke(app, ["expire", "--help"])
        assert result.exit_code == 0
        assert "--json" in strip_ansi(result.stdout)

    def test_config_has_json_option(self):
        """Test config command has --json option in help."""
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "--json" in strip_ansi(result.stdout)


class TestPrettyJsonOutput:
    """Test --pretty flag affects JSON output formatting."""

    def test_error_json_pretty_outputs_indented_json(self, monkeypatch, tmp_path):
        """Test error JSON --pretty outputs indented JSON."""
        config_file = tmp_path / "config.ini"
        monkeypatch.setattr("pwpush.options.user_config_file", config_file)
        monkeypatch.setattr("pwpush.commands.config.user_config_file", config_file)

        user_config.clear()
        user_config.read_dict(default_config)

        # Trigger an auth error with --json --pretty
        result = runner.invoke(app, ["list", "--json", "--pretty"])

        assert result.exit_code == 1
        # Pretty printed JSON should have newlines and indentation
        assert "\n" in result.stdout
        # Should still be valid JSON
        output = json.loads(result.stdout)
        assert "error" in output
