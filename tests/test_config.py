import json

from typer.testing import CliRunner

from pwpush.__main__ import app
from pwpush.options import save_config, user_config

runner = CliRunner()


def test_config_defaults_to_show():
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert result.stdout.strip()
    assert "Instance Settings" in result.stdout or '"instance": {' in result.stdout


def test_config_show():
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "Instance Settings" in result.stdout
    assert "Expiration Settings" in result.stdout
    assert "CLI Settings" in result.stdout


def test_config_show_in_json():
    result = runner.invoke(app, ["--json", "on", "config", "show"])
    assert '{"instance": {"url":' in result.stdout
    assert result.exit_code == 0


def test_config_set():
    result = runner.invoke(app, ["config", "set", "--key", "json", "--value", "True"])
    assert "Success" in result.stdout
    assert result.exit_code == 0

    result = runner.invoke(
        app, ["config", "set", "--key", "url", "--value", "https://pwpush.test"]
    )
    assert "Success" in result.stdout
    assert result.exit_code == 0

    result = runner.invoke(app, ["--json", "on", "config", "show"])
    config = json.loads(result.stdout.strip())
    assert config["cli"]["json"] == "True"
    assert config["instance"]["url"] == "https://pwpush.test"


def test_config_unset():
    result = runner.invoke(app, ["config", "unset", "--key", "json"])
    assert "Success" in result.stdout
    assert result.exit_code == 0

    result = runner.invoke(app, ["--json", "on", "config", "show"])
    config = json.loads(result.stdout.strip())
    assert config["cli"]["json"] == "Not Set"


def test_config_set_positional_arguments():
    """Test config set with positional arguments (new default approach)"""
    # Test setting a CLI setting
    result = runner.invoke(app, ["config", "set", "json", "True"])
    assert "Success" in result.stdout
    assert result.exit_code == 0

    # Test setting an instance setting
    result = runner.invoke(app, ["config", "set", "url", "https://test-positional.com"])
    assert "Success" in result.stdout
    assert result.exit_code == 0

    # Verify the settings were applied
    result = runner.invoke(app, ["--json", "on", "config", "show"])
    config = json.loads(result.stdout.strip())
    assert config["cli"]["json"] == "True"
    assert config["instance"]["url"] == "https://test-positional.com"


def test_config_set_flag_arguments():
    """Test config set with --key and --value flags (backward compatibility)"""
    # Test setting a CLI setting
    result = runner.invoke(app, ["config", "set", "--key", "json", "--value", "False"])
    assert "Success" in result.stdout
    assert result.exit_code == 0

    # Test setting an instance setting
    result = runner.invoke(
        app, ["config", "set", "--key", "url", "--value", "https://test-flags.com"]
    )
    assert "Success" in result.stdout
    assert result.exit_code == 0

    # Verify the settings were applied
    result = runner.invoke(app, ["--json", "on", "config", "show"])
    config = json.loads(result.stdout.strip())
    assert config["cli"]["json"] == "False"
    assert config["instance"]["url"] == "https://test-flags.com"


def test_config_set_error_cases():
    """Test error handling for config set command"""

    # Test missing both arguments (positional)
    result = runner.invoke(app, ["config", "set"])
    assert result.exit_code == 1
    assert "Both key and value must be provided" in result.stdout
    assert "Usage: pwpush config set <key> <value>" in result.stdout

    # Test missing one argument (positional)
    result = runner.invoke(app, ["config", "set", "url"])
    assert result.exit_code == 1
    assert "Both key and value must be provided" in result.stdout

    # Test missing --value flag
    result = runner.invoke(app, ["config", "set", "--key", "url"])
    assert result.exit_code == 1
    assert "Both --key and --value must be provided when using flags" in result.stdout

    # Test missing --key flag
    result = runner.invoke(app, ["config", "set", "--value", "https://test.com"])
    assert result.exit_code == 1
    assert "Both --key and --value must be provided when using flags" in result.stdout

    # Test mixing positional and flag arguments
    result = runner.invoke(
        app, ["config", "set", "url", "--key", "email", "--value", "test@example.com"]
    )
    assert result.exit_code == 1
    assert "Cannot mix positional arguments with --key/--value flags" in result.stdout

    # Test invalid key
    result = runner.invoke(app, ["config", "set", "invalid_key", "some_value"])
    assert result.exit_code == 1
    assert "That key was not found in the configuration" in result.stdout
    assert "See 'pwpush config show' for a list of valid keys" in result.stdout


def test_config_set_expiration_settings():
    """Test setting expiration-related configuration values"""
    # Test setting expire_after_days
    result = runner.invoke(app, ["config", "set", "expire_after_days", "7"])
    assert "Success" in result.stdout
    assert result.exit_code == 0

    # Test setting expire_after_views
    result = runner.invoke(
        app, ["config", "set", "--key", "expire_after_views", "--value", "10"]
    )
    assert "Success" in result.stdout
    assert result.exit_code == 0

    # Test setting retrieval_step
    result = runner.invoke(app, ["config", "set", "retrieval_step", "true"])
    assert "Success" in result.stdout
    assert result.exit_code == 0

    # Test setting deletable_by_viewer
    result = runner.invoke(
        app, ["config", "set", "--key", "deletable_by_viewer", "--value", "false"]
    )
    assert "Success" in result.stdout
    assert result.exit_code == 0

    # Verify all settings were applied
    result = runner.invoke(app, ["--json", "on", "config", "show"])
    config = json.loads(result.stdout.strip())
    assert config["expiration"]["expire_after_days"] == "7"
    assert config["expiration"]["expire_after_views"] == "10"
    assert config["expiration"]["retrieval_step"] == "true"
    assert config["expiration"]["deletable_by_viewer"] == "false"


def test_config_delete_confirmed(monkeypatch, tmp_path):
    config_file = tmp_path / "config.ini"
    monkeypatch.setattr("pwpush.options.user_config_file", config_file)
    monkeypatch.setattr("pwpush.commands.config.user_config_file", config_file)

    user_config["instance"]["url"] = "https://delete-test.example"
    save_config()
    assert config_file.exists()

    result = runner.invoke(app, ["config", "delete"], input="y\n")
    assert result.exit_code == 0
    assert "Deleted config file:" in result.stdout
    assert not config_file.exists()


def test_config_delete_aborted(monkeypatch, tmp_path):
    config_file = tmp_path / "config.ini"
    monkeypatch.setattr("pwpush.options.user_config_file", config_file)
    monkeypatch.setattr("pwpush.commands.config.user_config_file", config_file)

    save_config()
    assert config_file.exists()

    result = runner.invoke(app, ["config", "delete"], input="n\n")
    assert result.exit_code != 0
    assert config_file.exists()


def test_config_delete_when_file_missing(monkeypatch, tmp_path):
    config_file = tmp_path / "missing-config.ini"
    monkeypatch.setattr("pwpush.options.user_config_file", config_file)
    monkeypatch.setattr("pwpush.commands.config.user_config_file", config_file)

    assert not config_file.exists()

    result = runner.invoke(app, ["config", "delete"], input="y\n")
    assert result.exit_code == 0
    assert "No config file found at:" in result.stdout
