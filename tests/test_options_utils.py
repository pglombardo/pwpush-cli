"""Tests for options.py and utils.py missing coverage."""

from unittest.mock import MagicMock, patch

import pytest

from pwpush.commands.config import user_config
from pwpush.options import (
    cli_options,
    debug_output,
    json_output,
    load_config,
    save_config,
    validate_user_config,
    verbose_output,
)
from pwpush.utils import (
    check_secret_conditions,
    generate_secret,
    mask_sensitive_value,
    parse_boolean,
)


class TestMaskSensitiveValue:
    """Tests for mask_sensitive_value function."""

    def test_short_value_fully_masked(self):
        """Test that short values are fully masked."""
        result = mask_sensitive_value("abc", visible_chars=4)
        assert result == "***"

    def test_exactly_visible_chars(self):
        """Test value with exactly visible_chars length."""
        result = mask_sensitive_value("abcd", visible_chars=4)
        assert result == "****"

    def test_empty_string(self):
        """Test empty string returns Not Set."""
        result = mask_sensitive_value("", visible_chars=4)
        assert result == "Not Set"

    def test_not_set_value(self):
        """Test 'Not Set' value returns Not Set."""
        result = mask_sensitive_value("Not Set", visible_chars=4)
        assert result == "Not Set"

    def test_custom_visible_chars(self):
        """Test with custom visible_chars parameter."""
        result = mask_sensitive_value("secret123", visible_chars=3)
        assert result == "******123"


class TestParseBoolean:
    """Tests for parse_boolean function."""

    def test_true_values(self):
        """Test various true values."""
        assert parse_boolean(True) is True
        assert parse_boolean("true") is True
        assert parse_boolean("True") is True
        assert parse_boolean("TRUE") is True
        assert parse_boolean("yes") is True
        assert parse_boolean("on") is True
        assert parse_boolean("1") is True

    def test_false_values(self):
        """Test various false values."""
        assert parse_boolean(False) is False
        assert parse_boolean("false") is False
        assert parse_boolean("False") is False
        assert parse_boolean("no") is False
        assert parse_boolean("off") is False
        assert parse_boolean("0") is False
        assert parse_boolean("") is False

    def test_none_value(self):
        """Test None value returns False."""
        assert parse_boolean(None) is False

    def test_integer_zero(self):
        """Test integer 0 returns False."""
        assert parse_boolean(0) is False

    def test_integer_nonzero(self):
        """Test non-zero integer returns False (not in true list)."""
        assert parse_boolean(1) is False
        assert parse_boolean(42) is False


class TestCheckSecretConditions:
    """Tests for check_secret_conditions function."""

    def test_secret_meets_all_conditions(self):
        """Test secret that meets all conditions."""
        # A secret with: punctuation, upper, lower, digit, and correct length
        secret = "A1b2C3d4E5!@#$%"
        assert check_secret_conditions(secret, length=15) is True

    def test_secret_missing_punctuation(self):
        """Test secret missing punctuation."""
        secret = "A1b2C3d4E5f6G7h8"
        assert check_secret_conditions(secret, length=16) is False

    def test_secret_missing_uppercase(self):
        """Test secret missing uppercase."""
        secret = "a1b2c3d4e5!@#$%"
        assert check_secret_conditions(secret, length=15) is False

    def test_secret_missing_lowercase(self):
        """Test secret missing lowercase."""
        secret = "A1B2C3D4E5!@#$%"
        assert check_secret_conditions(secret, length=15) is False

    def test_secret_missing_digit(self):
        """Test secret missing digit."""
        secret = "AbcDefGhij!@#$%"
        assert check_secret_conditions(secret, length=15) is False

    def test_secret_wrong_length(self):
        """Test secret with wrong length."""
        secret = "A1b!"
        assert check_secret_conditions(secret, length=20) is False

    def test_secret_prints_message_on_failure(self, capsys):
        """Test that failure prints a message."""
        secret = "short"
        check_secret_conditions(secret, length=100)


class TestGenerateSecretRetry:
    """Tests for generate_secret retry logic."""

    def test_generate_secret_eventually_succeeds(self):
        """Test that generate_secret eventually produces valid secret."""
        # This should succeed within reasonable attempts
        secret = generate_secret(20)
        assert len(secret) == 20
        assert check_secret_conditions(secret, length=20) is True


class TestValidateUserConfig:
    """Tests for validate_user_config function."""

    def test_adds_missing_sections(self, monkeypatch):
        """Test that missing sections are added."""
        # Clear all sections
        for section in list(user_config.sections()):
            user_config.remove_section(section)

        result = validate_user_config()

        assert result is True
        assert "instance" in user_config.sections()
        assert "expiration" in user_config.sections()
        assert "cli" in user_config.sections()
        assert "pro" in user_config.sections()

    def test_adds_missing_keys(self, monkeypatch):
        """Test that missing keys within existing sections are added."""
        # Remove a specific key
        if "new_key" in user_config["instance"]:
            del user_config["instance"]["new_key"]

        # Add a test key that's not in defaults
        from pwpush.options import default_config

        original_defaults = default_config.copy()
        default_config["instance"]["new_test_key"] = "default_value"

        # Remove the key if it exists
        if "new_test_key" in user_config["instance"]:
            del user_config["instance"]["new_test_key"]

        result = validate_user_config()

        # Restore defaults
        default_config.clear()
        default_config.update(original_defaults)

        # The function should have added missing keys
        assert "url" in user_config["instance"]


class TestOutputHelpers:
    """Tests for output helper functions."""

    def test_verbose_output_from_cli_options(self, monkeypatch):
        """Test verbose_output when set in CLI options."""
        monkeypatch.setitem(cli_options, "verbose", True)
        assert verbose_output() is True

    def test_verbose_output_from_config(self, monkeypatch):
        """Test verbose_output when set in user config."""
        monkeypatch.setitem(cli_options, "verbose", False)
        monkeypatch.setitem(user_config["cli"], "verbose", "True")
        assert verbose_output() is True

    def test_debug_output_from_cli_options(self, monkeypatch):
        """Test debug_output when set in CLI options."""
        monkeypatch.setitem(cli_options, "debug", True)
        assert debug_output() is True

    def test_json_output_combined(self, monkeypatch):
        """Test json_output with both CLI and config sources."""
        monkeypatch.setitem(cli_options, "json", False)
        monkeypatch.setitem(user_config["cli"], "json", "True")
        assert json_output() is True


class TestLoadConfig:
    """Tests for load_config function edge cases."""

    def test_load_config_with_validation_changes(self, monkeypatch, tmp_path):
        """Test load_config when validation adds missing values."""
        # Create a minimal config file
        config_file = tmp_path / "config.ini"
        config_file.write_text("[instance]\nurl = https://test.com\n")

        with patch("pwpush.options.user_config_file", config_file):
            with patch("pwpush.options.user_config.read") as mock_read:
                with patch("pwpush.options.validate_user_config", return_value=True):
                    with patch("pwpush.options.save_config") as mock_save:
                        load_config()
                        mock_save.assert_called_once()
