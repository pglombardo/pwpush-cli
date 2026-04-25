"""Tests for config command edge cases."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from pwpush.__main__ import app
from pwpush.commands.config import user_config

runner = CliRunner()


class TestConfigCallbackFlags:
    """Tests for config callback flag handling."""

    def test_config_callback_sets_json(self):
        """Test that config callback sets json flag."""
        result = runner.invoke(app, ["--json", "config", "show"])

        assert result.exit_code == 0
        # Should output JSON
        assert '"instance"' in result.output

    def test_config_callback_sets_verbose(self):
        """Test that config callback sets verbose flag."""
        result = runner.invoke(app, ["--verbose", "config"])

        # Should not error
        assert result.exit_code == 0

    def test_config_callback_sets_debug(self):
        """Test that config callback sets debug flag."""
        result = runner.invoke(app, ["--debug", "config"])

        assert result.exit_code == 0


class TestConfigInitCommand:
    """Tests for config init command."""

    @patch("pwpush.commands.config.run_config_wizard")
    def test_init_command_runs_wizard(self, mock_wizard):
        """Test that init command runs the wizard."""
        result = runner.invoke(app, ["config", "init"])

        assert result.exit_code == 0
        mock_wizard.assert_called_once()


class TestConfigSetMixedArgs:
    """Tests for config set with mixed positional and flag arguments."""

    def test_config_set_flag_only_key_error(self):
        """Test error when only --key provided without --value."""
        result = runner.invoke(app, ["config", "set", "--key", "url"])

        assert result.exit_code == 1
        assert "Both --key and --value must be provided" in result.output

    def test_config_set_flag_only_value_error(self):
        """Test error when only --value provided without --key."""
        result = runner.invoke(app, ["config", "set", "--value", "https://test.com"])

        assert result.exit_code == 1
        assert "Both --key and --value must be provided" in result.output

    def test_config_set_valid_with_flags(self):
        """Test valid config set with --key and --value flags."""
        result = runner.invoke(
            app, ["config", "set", "--key", "url", "--value", "https://test.com"]
        )

        assert result.exit_code == 0
        assert "Success" in result.output


class TestConfigUnset:
    """Tests for config unset command."""

    def test_unset_existing_key(self, monkeypatch):
        """Test unsetting an existing key."""
        # Set a value first
        user_config["instance"]["test_key"] = "test_value"

        result = runner.invoke(app, ["config", "unset", "--key", "test_key"])

        assert result.exit_code == 0
        assert "Success" in result.output
        assert user_config["instance"]["test_key"] == "Not Set"

    def test_unset_nonexistent_key(self):
        """Test unsetting a non-existent key."""
        result = runner.invoke(app, ["config", "unset", "--key", "nonexistent_key_xyz"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()


class TestConfigDelete:
    """Tests for config delete command."""

    def test_delete_config_confirmed(self, monkeypatch, tmp_path):
        """Test deleting config file with confirmation."""
        # Create a config file
        config_file = tmp_path / "config.ini"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("[instance]\nurl = https://test.com\n")

        monkeypatch.setattr("pwpush.commands.config.user_config_file", config_file)

        result = runner.invoke(app, ["config", "delete"], input="y\n")

        assert result.exit_code == 0
        assert "Deleted config file" in result.output or not config_file.exists()

    def test_delete_config_no_file(self, monkeypatch, tmp_path):
        """Test deleting when config file doesn't exist."""
        config_file = tmp_path / "nonexistent" / "config.ini"

        monkeypatch.setattr("pwpush.commands.config.user_config_file", config_file)

        result = runner.invoke(app, ["config", "delete"], input="y\n")

        # Should handle gracefully
        assert result.exit_code == 0 or "No config file found" in result.output

    def test_delete_config_os_error(self, monkeypatch, tmp_path):
        """Test delete when OS error occurs."""
        config_file = tmp_path / "config.ini"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("[instance]\nurl = https://test.com\n")

        # Make file unreadable/un-deletable by changing permissions or mocking
        monkeypatch.setattr("pwpush.commands.config.user_config_file", config_file)

        with patch.object(Path, "unlink", side_effect=OSError("Permission denied")):
            result = runner.invoke(app, ["config", "delete"], input="y\n")

            assert result.exit_code == 1
            assert "could not delete" in result.output.lower()
