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
    with patch("pwpush.__main__.make_request") as mock:
        mock.return_value.status_code = 201
        mock.return_value.json.return_value = {
            "url_token": "super-token",
            "url": "https://pwpush.test/en/p/text-password-url",
        }
        yield mock


@pytest.fixture
def mock_getpass():
    with patch(
        "pwpush.__main__.getpass.getpass", side_effect=["passphrase", "passphrase"]
    ) as mock:
        yield mock


@pytest.fixture
def mock_create_password():
    with patch(
        "pwpush.__main__.typer.prompt", side_effect=["secret", "secret"]
    ) as mock:
        yield mock


@pytest.fixture
def mock_generate_password():
    with patch(
        "pwpush.__main__.generate_password", return_value="auto_generated_password"
    ) as mock:
        yield mock


@pytest.fixture
def mock_genpass():
    with patch(
        "pwpush.__main__.genpass", return_value="auto_generated_passphrase"
    ) as mock:
        yield mock
