from unittest.mock import patch

import pytest
import requests
from typer.testing import CliRunner

import pwpush
from pwpush.__main__ import app, generate_password, genpass

# import the mocks
from tests import *

runner = CliRunner()


def test_push_no_options(
    mock_make_request,
    mock_create_password,
    mock_generate_password,
    mock_getpass,
    mock_genpass,
):
    result = runner.invoke(app, "push")
    assert result.exit_code == 0
    assert "The secret has been pushed to" in result.output


def test_push_auto(mock_make_request):
    result = runner.invoke(app, ["push", "--auto"])
    assert result.exit_code == 0
    assert "Passphrase is:" in result.stdout
    assert "https://pwpush.test/en/p/text-password-url\n" in result.stdout


def test_basic_push_passphrase(monkeypatch):
    monkeypatch.setattr(
        requests, "post", build_request_mock({"url_token": "super-token"})
    )
    monkeypatch.setattr(
        requests,
        "get",
        build_request_mock({"url": "https://pwpush.test/en/p/text-password-url"}),
    )

    result = runner.invoke(
        app, ["push", "--secret", "mypassword", "--passphrase", "hello"]
    )
    print(result)
    assert result.exit_code == 0
    assert "https://pwpush.test/en/p/text-password-url\n" in result.stdout


def test_file_push(monkeypatch):
    monkeypatch.setattr(
        requests, "post", build_request_mock({"url_token": "super-token"})
    )
    monkeypatch.setattr(
        requests,
        "get",
        build_request_mock({"url": "https://pwpush.test/en/f/secret-file-url"}),
    )

    result = runner.invoke(app, ["push-file", "./README.md"])
    assert result.exit_code == 0
    assert "https://pwpush.test/en/f/secret-file-url\n" == result.stdout


def test_config_show_in_json():
    result = runner.invoke(app, ["--json", "on", "config", "show"])
    assert '{"instance": {"url":' in result.stdout
    assert result.exit_code == 0


def test_genpass():
    pw = genpass(2)
    assert pw


def test_create_password():
    pw1 = generate_password(20)
    assert len(pw1) == 20

    pw2 = generate_password()
    assert len(pw2) == 50


def test_push_with_kind_url(mock_make_request):
    result = runner.invoke(
        app, ["push", "--secret", "https://example.com", "--kind", "url"]
    )
    assert result.exit_code == 0
    assert "The secret has been pushed to" in result.output


def test_push_with_kind_qr(mock_make_request):
    result = runner.invoke(app, ["push", "--secret", "QR data", "--kind", "qr"])
    assert result.exit_code == 0
    assert "The secret has been pushed to" in result.output


def test_push_with_invalid_kind():
    result = runner.invoke(app, ["push", "--secret", "test", "--kind", "invalid"])
    assert result.exit_code == 1
    assert "Invalid kind 'invalid'. Must be one of: text, url, qr" in result.output
