"""Pytest configuration and global fixtures."""

import pytest

from pwpush.options import default_config, load_config, user_config


@pytest.fixture(autouse=True)
def isolate_config_file(monkeypatch, tmp_path):
    """
    Redirect user_config_file to a temporary path for all tests.

    This prevents tests from reading or writing to the user's real
    config file at ~/.config/pwpush/config.ini.
    """
    config_file = tmp_path / "config.ini"

    # Redirect the config file path in all modules that import it
    monkeypatch.setattr("pwpush.options.user_config_file", config_file)
    monkeypatch.setattr("pwpush.commands.config.user_config_file", config_file)
    monkeypatch.setattr("pwpush.config_wizard.user_config_file", config_file)

    # Clear and reload the config with defaults to ensure clean state
    user_config.clear()
    user_config.read_dict(default_config)

    yield config_file

    # Cleanup: the tmp_path will be automatically cleaned up by pytest
