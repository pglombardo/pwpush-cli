import json

from typer.testing import CliRunner

from pwpush.__main__ import app

runner = CliRunner()


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
