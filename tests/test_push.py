import requests
from typer.testing import CliRunner

from pwpush.__main__ import app

runner = CliRunner()


def build_request_mock(body):
    class MockResponse(object):
        def __init__(self, body):
            self.status_code = 201
            self.body = body

        def json(self):
            return body

    def mock(*args, **kwargs):
        return MockResponse(body)

    return mock


def test_basic_push(monkeypatch):
    monkeypatch.setattr(
        requests, "post", build_request_mock({"url_token": "super-token"})
    )
    monkeypatch.setattr(
        requests,
        "get",
        build_request_mock({"url": "https://pwpush.test/en/p/text-password-url"}),
    )

    result = runner.invoke(app, ["push", "mypassword"])
    assert result.exit_code == 0
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

    result = runner.invoke(app, ["push", "mypassword", "--passphrase", "hello"])
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
