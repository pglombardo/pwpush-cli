import json

from typer.testing import CliRunner

from pwpush.__main__ import app

runner = CliRunner()

# def test_login():
#     result = runner.invoke(app, ["login"], input="\n\n\n")
#     assert "Credentials saved" in result.stdout
#     assert result.exit_code == 0

# def test_logout():
#     result = runner.invoke(app, ["login"], input="Y\n")
#     assert "This will log you out from this command line tool" in result.stdout
#     assert "Log out successful." in result.stdout
#     assert result.exit_code == 0
