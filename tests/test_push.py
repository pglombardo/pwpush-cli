"""Tests for push commands."""

from unittest.mock import patch

import pytest
import requests
from typer.testing import CliRunner

import pwpush
from pwpush.__main__ import app
from pwpush.commands.config import user_config
from pwpush.utils import check_secret_conditions, generate_passphrase, generate_secret

# import the mocks
from tests import *

runner = CliRunner()


def test_push_no_options(mock_make_request):
    """Test push with no options - uses piped input since CliRunner can't simulate TTY."""
    result = runner.invoke(app, ["push"], input="test-secret")
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

    with patch("pwpush.__main__.current_api_profile", return_value="legacy"):
        result = runner.invoke(
            app, ["push", "--secret", "mypassword", "--passphrase", "hello"]
        )
    print(result)
    assert result.exit_code == 0
    assert "https://pwpush.test/en/p/text-password-url\n" in result.stdout


def test_file_push(monkeypatch):
    monkeypatch.setitem(user_config["instance"], "email", "user@example.test")
    monkeypatch.setitem(user_config["instance"], "token", "token-value")

    monkeypatch.setattr(
        requests, "post", build_request_mock({"url_token": "super-token"})
    )
    monkeypatch.setattr(
        requests,
        "get",
        build_request_mock({"url": "https://pwpush.test/en/f/secret-file-url"}),
    )

    with patch("pwpush.__main__.current_api_profile", return_value="legacy"):
        result = runner.invoke(app, ["push-file", "./README.md"])
    assert result.exit_code == 0
    assert "https://pwpush.test/en/f/secret-file-url\n" == result.stdout


def test_config_show_in_json():
    result = runner.invoke(app, ["--json", "config", "show"])
    assert '{"instance": {"url":' in result.stdout
    assert result.exit_code == 0


def test_generate_passphrase():
    pw = generate_passphrase(2)
    assert pw


def test_create_secret():
    pw1 = generate_secret(20)
    assert check_secret_conditions(pw1, length=20)

    pw2 = generate_secret()
    assert check_secret_conditions(pw2, length=50)


def test_push_with_kind_url(mock_make_request):
    result = runner.invoke(
        app,
        [
            "push",
            "--secret",
            "https://example.com",
            "--kind",
            "url",
            "--passphrase",
            "testpass",
        ],
    )
    assert result.exit_code == 0
    assert "The secret has been pushed to" in result.output


def test_push_with_kind_qr(mock_make_request):
    result = runner.invoke(
        app, ["push", "--secret", "QR data", "--kind", "qr", "--passphrase", "testpass"]
    )
    assert result.exit_code == 0
    assert "The secret has been pushed to" in result.output


def test_push_with_invalid_kind():
    result = runner.invoke(
        app,
        ["push", "--secret", "test", "--kind", "invalid", "--passphrase", "testpass"],
    )
    assert result.exit_code == 1
    assert "Invalid kind 'invalid'. Must be one of: text, url, qr" in result.output


def _get_post_call(mock_make_request):
    """Helper to find the POST call from make_request mock by HTTP method."""
    for call in mock_make_request.call_args_list:
        if call[0] and call[0][0] == "POST":
            return call
    return None


def test_push_with_piped_input(mock_make_request):
    """Test that piped input is read from stdin when --secret is not provided."""
    result = runner.invoke(app, ["push"], input="piped-secret-from-stdin")
    assert result.exit_code == 0
    assert "The secret has been pushed to" in result.output
    # Verify make_request was called with the piped secret (first call is POST)
    post_call = _get_post_call(mock_make_request)
    assert post_call is not None
    assert post_call[1]["post_data"]["password"]["payload"] == "piped-secret-from-stdin"


def test_push_with_piped_input_strips_newlines(mock_make_request):
    """Test that trailing newlines are stripped from piped input."""
    # Simulate piped input with trailing newline
    result = runner.invoke(app, ["push"], input="secret-with-newline\n")
    assert result.exit_code == 0
    post_call = _get_post_call(mock_make_request)
    assert post_call is not None
    # Verify the newline was stripped
    assert post_call[1]["post_data"]["password"]["payload"] == "secret-with-newline"


def test_push_with_piped_input_strips_carriage_return(mock_make_request):
    """Test that trailing \r\n is stripped from piped input (Windows style)."""
    result = runner.invoke(app, ["push"], input="secret-with-crlf\r\n")
    assert result.exit_code == 0
    post_call = _get_post_call(mock_make_request)
    assert post_call is not None
    assert post_call[1]["post_data"]["password"]["payload"] == "secret-with-crlf"


def test_push_secret_arg_takes_precedence_over_pipe(mock_make_request):
    """Test that --secret CLI arg takes precedence over piped input."""
    result = runner.invoke(
        app, ["push", "--secret", "cli-secret"], input="piped-secret"
    )
    assert result.exit_code == 0
    post_call = _get_post_call(mock_make_request)
    assert post_call is not None
    # Should use the CLI arg, not the piped input
    assert post_call[1]["post_data"]["password"]["payload"] == "cli-secret"


def test_push_piped_input_with_passphrase_flag(mock_make_request):
    """Test that --passphrase works with piped input."""
    result = runner.invoke(
        app, ["push", "--passphrase", "my-passphrase"], input="piped-secret"
    )
    assert result.exit_code == 0
    post_call = _get_post_call(mock_make_request)
    assert post_call is not None
    assert post_call[1]["post_data"]["password"]["payload"] == "piped-secret"
    assert post_call[1]["post_data"]["password"]["passphrase"] == "my-passphrase"


def test_push_piped_input_skips_interactive_passphrase_prompt(mock_make_request):
    """Test that interactive passphrase confirmation is skipped with piped input."""
    # When piped, we should NOT see interactive passphrase prompts
    # This is verified by the fact that the command succeeds without
    # any getpass or typer.prompt calls being mocked
    result = runner.invoke(app, ["push"], input="piped-secret")
    assert result.exit_code == 0
    assert "The secret has been pushed to" in result.output
    # Ensure no passphrase-related prompts appeared
    assert "Would you like to add a passphrase" not in result.output


def test_push_piped_input_with_kind_url(mock_make_request):
    """Test piped input works with --kind url."""
    result = runner.invoke(
        app, ["push", "--kind", "url"], input="https://example.com/piped"
    )
    assert result.exit_code == 0
    post_call = _get_post_call(mock_make_request)
    assert post_call is not None
    assert (
        post_call[1]["post_data"]["password"]["payload"] == "https://example.com/piped"
    )
    assert post_call[1]["post_data"]["password"]["kind"] == "url"


def test_push_piped_input_with_kind_qr(mock_make_request):
    """Test piped input works with --kind qr."""
    result = runner.invoke(app, ["push", "--kind", "qr"], input="qr-data-from-pipe")
    assert result.exit_code == 0
    post_call = _get_post_call(mock_make_request)
    assert post_call is not None
    assert post_call[1]["post_data"]["password"]["payload"] == "qr-data-from-pipe"
    assert post_call[1]["post_data"]["password"]["kind"] == "qr"


def test_push_piped_input_with_expiration_options(mock_make_request):
    """Test piped input works with expiration options."""
    result = runner.invoke(
        app,
        ["push", "--days", "3", "--views", "5", "--deletable", "--retrieval-step"],
        input="piped-secret",
    )
    assert result.exit_code == 0
    post_call = _get_post_call(mock_make_request)
    assert post_call is not None
    data = post_call[1]["post_data"]["password"]
    assert data["payload"] == "piped-secret"
    assert data["expire_after_days"] == 3
    assert data["expire_after_views"] == 5
    assert data["deletable_by_viewer"] is True
    assert data["retrieval_step"] is True


def test_push_piped_input_multiline(mock_make_request):
    """Test that multiline piped input is preserved (except trailing newlines)."""
    multiline_input = "line1\nline2\nline3\n"
    result = runner.invoke(app, ["push"], input=multiline_input)
    assert result.exit_code == 0
    post_call = _get_post_call(mock_make_request)
    assert post_call is not None
    # Only trailing newlines should be stripped, internal ones preserved
    assert post_call[1]["post_data"]["password"]["payload"] == "line1\nline2\nline3"


def test_push_empty_piped_input_rejected(mock_make_request):
    """Test that empty piped input is rejected with a helpful error."""
    result = runner.invoke(app, ["push"], input="")
    assert result.exit_code == 1
    assert "No secret provided on stdin" in result.output
    # Verify no POST request was made
    post_call = _get_post_call(mock_make_request)
    assert post_call is None


def test_push_with_piped_input_explicit_secret(mock_make_request):
    """Test push with explicit secret via input (piped input path)."""
    result = runner.invoke(app, ["push"], input="explicit-secret")
    assert result.exit_code == 0
    assert "The secret has been pushed to" in result.output
    post_call = _get_post_call(mock_make_request)
    assert post_call is not None
    assert post_call[1]["post_data"]["password"]["payload"] == "explicit-secret"


def test_push_with_notify_unauthenticated(monkeypatch):
    """Test that --notify requires authentication - error when no API token."""
    from pwpush.commands.config import user_config

    # Ensure no token is set
    monkeypatch.setitem(user_config["instance"], "token", "Not Set")

    with (
        patch("pwpush.__main__.current_api_profile", return_value="legacy"),
        patch("pwpush.__main__.make_request") as mock,
    ):
        mock.return_value.status_code = 201
        mock.return_value.json.return_value = {
            "url_token": "super-token",
            "url": "https://pwpush.test/en/p/text-password-url",
        }
        result = runner.invoke(
            app, ["push", "--secret", "test", "--notify", "admin@example.com"]
        )
    assert result.exit_code == 1
    assert "Email notifications require authentication" in result.output


def test_push_with_notify_locale_unauthenticated(monkeypatch):
    """Test that --notify-locale requires authentication - error when no API token."""
    from pwpush.commands.config import user_config

    # Ensure no token is set
    monkeypatch.setitem(user_config["instance"], "token", "Not Set")

    with (
        patch("pwpush.__main__.current_api_profile", return_value="legacy"),
        patch("pwpush.__main__.make_request") as mock,
    ):
        mock.return_value.status_code = 201
        mock.return_value.json.return_value = {
            "url_token": "super-token",
            "url": "https://pwpush.test/en/p/text-password-url",
        }
        result = runner.invoke(
            app, ["push", "--secret", "test", "--notify-locale", "en"]
        )
    assert result.exit_code == 1
    assert "Email notifications require authentication" in result.output


def test_push_with_notify_when_enabled(mock_make_request, monkeypatch):
    """Test push with notification when feature is enabled."""
    # Mock capabilities with feature enabled - pushes.email_auto_dispatch
    mock_capabilities = {
        "api_version": "2.1.0",
        "features": {"pushes": {"email_auto_dispatch": True}},
    }
    monkeypatch.setattr(
        "pwpush.commands.push.detect_api_capabilities",
        lambda **kwargs: mock_capabilities,
    )

    # Set up auth token
    from pwpush.commands.config import user_config

    monkeypatch.setitem(user_config["instance"], "token", "valid-token")

    result = runner.invoke(
        app, ["push", "--secret", "test", "--notify", "admin@example.com"]
    )
    assert result.exit_code == 0
    post_call = _get_post_call(mock_make_request)
    assert post_call is not None
    assert (
        post_call[1]["post_data"]["password"]["notify_emails_to"] == "admin@example.com"
    )


def test_push_with_notify_when_disabled(mock_make_request, monkeypatch):
    """Test push with notification shows warning when feature is disabled."""
    # Mock capabilities with feature disabled - pushes.email_auto_dispatch
    mock_capabilities = {
        "api_version": "2.1.0",
        "features": {"pushes": {"email_auto_dispatch": False}},
    }
    monkeypatch.setattr(
        "pwpush.commands.push.detect_api_capabilities",
        lambda **kwargs: mock_capabilities,
    )

    # Set up auth token
    from pwpush.commands.config import user_config

    monkeypatch.setitem(user_config["instance"], "token", "valid-token")

    result = runner.invoke(
        app, ["push", "--secret", "test", "--notify", "admin@example.com"]
    )
    assert result.exit_code == 0
    assert "Email notifications are not enabled" in result.output
    # Verify notify field is NOT in the payload
    post_call = _get_post_call(mock_make_request)
    assert post_call is not None
    assert "notify_emails_to" not in post_call[1]["post_data"]["password"]


def test_push_with_notify_locale(mock_make_request, monkeypatch):
    """Test push with notification locale."""
    mock_capabilities = {
        "api_version": "2.1.0",
        "features": {"pushes": {"email_auto_dispatch": True}},
    }
    monkeypatch.setattr(
        "pwpush.commands.push.detect_api_capabilities",
        lambda **kwargs: mock_capabilities,
    )

    from pwpush.commands.config import user_config

    monkeypatch.setitem(user_config["instance"], "token", "valid-token")

    result = runner.invoke(
        app,
        [
            "push",
            "--secret",
            "test",
            "--notify",
            "admin@example.com",
            "--notify-locale",
            "es",
        ],
    )
    assert result.exit_code == 0
    post_call = _get_post_call(mock_make_request)
    assert post_call is not None
    assert (
        post_call[1]["post_data"]["password"]["notify_emails_to"] == "admin@example.com"
    )
    assert post_call[1]["post_data"]["password"]["notify_emails_to_locale"] == "es"


def test_email_notifications_enabled_helper():
    """Test the email_notifications_enabled helper function."""
    from pwpush.api.capabilities import email_notifications_enabled

    # Enabled - pushes.email_auto_dispatch
    assert email_notifications_enabled(
        {"api_version": "2.1.0", "features": {"pushes": {"email_auto_dispatch": True}}}
    )

    # Disabled - feature flag false
    assert not email_notifications_enabled(
        {"api_version": "2.1.0", "features": {"pushes": {"email_auto_dispatch": False}}}
    )

    # Disabled - missing pushes section
    assert not email_notifications_enabled({"api_version": "2.1.0", "features": {}})

    # Disabled - missing email_auto_dispatch in pushes
    assert not email_notifications_enabled(
        {"api_version": "2.1.0", "features": {"pushes": {}}}
    )

    # Disabled - old API version
    assert not email_notifications_enabled(
        {"api_version": "2.0.0", "features": {"pushes": {"email_auto_dispatch": True}}}
    )

    # Disabled - None
    assert not email_notifications_enabled(None)

    # Disabled - empty dict
    assert not email_notifications_enabled({})
