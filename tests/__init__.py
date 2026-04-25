"""Test suite for pwpush CLI."""

from unittest.mock import patch

import pytest
import requests


def build_request_mock(body):
    class MockResponse:
        def __init__(self, body):
            self.status_code = 201
            self.body = body

        def json(self):
            return body

    def mock(*args, **kwargs):
        return MockResponse(body)

    return mock


@pytest.fixture
def mock_make_request():
    with (
        patch("pwpush.__main__.current_api_profile", return_value="legacy"),
        patch("pwpush.__main__.make_request") as mock,
        patch(
            "pwpush.commands.push.detect_api_capabilities",
            return_value={"api_version": None, "features": {}},
        ),
    ):
        mock.return_value.status_code = 201
        mock.return_value.json.return_value = {
            "url_token": "super-token",
            "url": "https://pwpush.test/en/p/text-password-url",
        }
        yield mock


@pytest.fixture
def mock_getpass():
    with patch(
        "pwpush.commands.push.getpass.getpass", side_effect=["passphrase", "passphrase"]
    ) as mock:
        yield mock


@pytest.fixture
def mock_create_password():
    with patch(
        "pwpush.commands.push.typer.prompt", side_effect=["secret", "secret"]
    ) as mock:
        yield mock


@pytest.fixture
def mock_generate_password():
    with patch(
        "pwpush.utils.generate_secret", return_value="auto_generated_password"
    ) as mock:
        yield mock


@pytest.fixture
def mock_genpass():
    with patch(
        "pwpush.utils.generate_passphrase", return_value="auto_generated_passphrase"
    ) as mock:
        yield mock
