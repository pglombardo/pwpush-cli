"""Tests for the configuration wizard."""

import json

from typer.testing import CliRunner

from pwpush.__main__ import app
from pwpush.config_wizard import (
    WizardSettings,
    apply_wizard_settings,
    normalize_instance_url,
)
from pwpush.options import default_config, user_config

runner = CliRunner()


def reset_config_file(monkeypatch, config_file):
    monkeypatch.setattr("pwpush.options.user_config_file", config_file)
    monkeypatch.setattr("pwpush.commands.config.user_config_file", config_file)
    monkeypatch.setattr("pwpush.config_wizard.user_config_file", config_file)
    user_config.clear()
    user_config.read_dict(default_config)


def test_normalize_instance_url_defaults_bare_domains_to_https():
    assert normalize_instance_url("pwpush.example.com/") == "https://pwpush.example.com"


def test_apply_wizard_settings_resets_cached_profile_on_instance_change():
    user_config["instance"]["url"] = "https://old.example"
    user_config["instance"]["api_profile"] = "v2"
    user_config["instance"]["api_profile_checked_at"] = "123"

    settings = WizardSettings(
        url="https://new.example",
        email="Not Set",
        token="Not Set",
        account_id="Not Set",
        expire_after_days="7",
        expire_after_views="10",
        retrieval_step="True",
        deletable_by_viewer="False",
        json="False",
        verbose="True",
        pretty="False",
        debug="False",
    )

    apply_wizard_settings(settings)

    assert user_config["instance"]["url"] == "https://new.example"
    assert user_config["instance"]["api_profile"] == "Not Set"
    assert user_config["instance"]["api_profile_checked_at"] == "0"
    assert user_config["expiration"]["expire_after_days"] == "7"
    assert user_config["expiration"]["expire_after_views"] == "10"
    assert user_config["expiration"]["retrieval_step"] == "True"
    assert user_config["expiration"]["deletable_by_viewer"] == "False"
    assert user_config["cli"]["verbose"] == "True"


def test_config_wizard_saves_us_instance_and_skipped_preferences(monkeypatch, tmp_path):
    config_file = tmp_path / "config.ini"
    reset_config_file(monkeypatch, config_file)

    result = runner.invoke(app, ["config", "wizard"], input="2\nn\nn\nn\n")

    assert result.exit_code == 0
    assert config_file.exists()
    assert user_config["instance"]["url"] == "https://us.pwpush.com"
    assert user_config["instance"]["email"] == "Not Set"
    assert user_config["instance"]["token"] == "Not Set"
    assert user_config["expiration"]["expire_after_days"] == "Not Set"
    assert user_config["expiration"]["expire_after_views"] == "Not Set"
    assert user_config["expiration"]["retrieval_step"] == "Not Set"
    assert user_config["expiration"]["deletable_by_viewer"] == "Not Set"


def test_config_wizard_saves_oss_instance(monkeypatch, tmp_path):
    config_file = tmp_path / "config.ini"
    reset_config_file(monkeypatch, config_file)

    result = runner.invoke(app, ["config", "wizard"], input="3\nn\nn\nn\n")

    assert result.exit_code == 0
    assert user_config["instance"]["url"] == "https://oss.pwpush.com"


def test_config_wizard_saves_custom_instance_and_preferences(monkeypatch, tmp_path):
    config_file = tmp_path / "config.ini"
    reset_config_file(monkeypatch, config_file)

    result = runner.invoke(
        app,
        ["config", "wizard"],
        input=(
            "4\n"
            "pwpush.example.com/\n"
            "y\n"
            "token-value\n"
            "y\n"
            "7\n"
            "10\n"
            "y\n"
            "n\n"
            "y\n"
            "y\n"
            "n\n"
            "y\n"
            "n\n"
        ),
    )

    assert result.exit_code == 0
    assert user_config["instance"]["url"] == "https://pwpush.example.com"
    assert user_config["instance"]["email"] == "Not Set"
    assert user_config["instance"]["token"] == "token-value"
    assert user_config["expiration"]["expire_after_days"] == "7"
    assert user_config["expiration"]["expire_after_views"] == "10"
    assert user_config["expiration"]["retrieval_step"] == "True"
    assert user_config["expiration"]["deletable_by_viewer"] == "False"
    assert user_config["cli"]["json"] == "True"
    assert user_config["cli"]["verbose"] == "False"
    assert user_config["cli"]["pretty"] == "True"
    assert user_config["cli"]["debug"] == "False"


def test_first_run_decline_shows_welcome_without_creating_config(monkeypatch, tmp_path):
    config_file = tmp_path / "config.ini"
    reset_config_file(monkeypatch, config_file)

    result = runner.invoke(app, [], input="n\n")

    assert result.exit_code == 0
    assert "Password Pusher CLI" in result.stdout
    assert not config_file.exists()


def test_first_run_shows_welcome_screen(monkeypatch, tmp_path):
    config_file = tmp_path / "config.ini"
    reset_config_file(monkeypatch, config_file)

    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "Password Pusher CLI" in result.stdout
    assert "Quick Start" in result.stdout
    assert "pwpush config wizard" in result.stdout


def test_no_arg_with_existing_config_does_not_prompt(monkeypatch, tmp_path):
    config_file = tmp_path / "config.ini"
    reset_config_file(monkeypatch, config_file)
    config_file.write_text("[instance]\nurl = https://existing.example\n")

    result = runner.invoke(app, [])

    assert result.exit_code == 0
    assert "Run the setup wizard" not in result.stdout
    assert "Password Pusher CLI" in result.stdout


def test_help_does_not_prompt_or_create_config(monkeypatch, tmp_path):
    config_file = tmp_path / "config.ini"
    reset_config_file(monkeypatch, config_file)

    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.stdout
    assert "COMMAND" in result.stdout
    assert not config_file.exists()


def test_config_help_promotes_wizard_before_direct_edits(monkeypatch, tmp_path):
    config_file = tmp_path / "config.ini"
    reset_config_file(monkeypatch, config_file)

    result = runner.invoke(app, ["config", "--help"])

    assert result.exit_code == 0
    assert "Run the guided setup wizard" in result.stdout
    assert "Directly set a configuration value" in result.stdout
    assert not config_file.exists()


def test_config_show_works_without_existing_file(monkeypatch, tmp_path):
    config_file = tmp_path / "config.ini"
    reset_config_file(monkeypatch, config_file)

    result = runner.invoke(app, ["--json", "config", "show"])
    config = json.loads(result.stdout.strip())

    assert result.exit_code == 0
    assert config["instance"]["url"] == "https://eu.pwpush.com"
    assert not config_file.exists()
