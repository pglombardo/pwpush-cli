import json

from typer.testing import CliRunner

from pwpush.__main__ import app

runner = CliRunner()


def test_basic_push():
    result = runner.invoke(app, ["push", "mypassword"])
    assert result.exit_code == 0
    assert "Instance Settings" in result.stdout
    assert "Expiration Settings" in result.stdout
    assert "CLI Settings" in result.stdout


def test_config_show_in_json():
    result = runner.invoke(app, ["--json", "on", "config", "show"])
    assert '{"instance": {"url":' in result.stdout
    assert result.exit_code == 0
