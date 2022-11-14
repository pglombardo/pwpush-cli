import json

from typer.testing import CliRunner

from pwpush.__main__ import app

runner = CliRunner()


def test_basic_push():
    result = runner.invoke(app, ["push", "mypassword"])
    assert result.exit_code == 0
    assert "https://pwpush.com/en/p/" in result.stdout


def test_config_show_in_json():
    result = runner.invoke(app, ["--json", "on", "config", "show"])
    assert '{"instance": {"url":' in result.stdout
    assert result.exit_code == 0
