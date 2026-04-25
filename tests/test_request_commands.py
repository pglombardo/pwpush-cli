"""Tests for request commands."""

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from pwpush.__main__ import app
from pwpush.commands.config import user_config

# import the mocks
from tests import *

runner = CliRunner()


@pytest.fixture
def mock_request_enabled():
    """Mock requests_enabled to return True."""
    with (
        patch(
            "pwpush.commands.request.requests_enabled",
            return_value=True,
        ),
        patch(
            "pwpush.commands.request.request_email_notifications_enabled",
            return_value=True,
        ),
    ):
        yield


@pytest.fixture
def mock_request_disabled():
    """Mock requests_enabled to return False."""
    with patch(
        "pwpush.commands.request.requests_enabled",
        return_value=False,
    ):
        yield


@pytest.fixture
def mock_request_make_request():
    """Mock make_request for request commands with v2 API profile."""
    with (
        patch("pwpush.__main__.current_api_profile", return_value="v2"),
        patch("pwpush.__main__.make_request") as mock,
        patch(
            "pwpush.commands.request.detect_api_capabilities",
            return_value={
                "api_version": "2.1.0",
                "edition": "commercial",
                "features": {"requests": {"enabled": True}},
            },
        ),
    ):
        mock.return_value.status_code = 201
        mock.return_value.json.return_value = {
            "url_token": "request-token",
            "url": "https://pwpush.test/en/r/request-url",
        }
        yield mock


def _get_post_call(mock_make_request):
    """Helper to find the POST call from make_request mock by HTTP method.

    Returns a tuple of (positional_args, keyword_args) for the POST call.
    """
    for call in mock_make_request.call_args_list:
        args = call[0] if call[0] else ()
        kwargs = call[1] if call[1] else {}
        # Check if this is a POST call (first positional arg is method)
        if args and args[0] == "POST":
            return (args, kwargs)
        # Also check kwargs for method
        if kwargs.get("method") == "POST":
            return (args, kwargs)
    return None


def _get_request_data_from_call(post_call):
    """Extract request data from a mock call.

    Handles both positional and keyword argument formats.
    """
    if post_call is None:
        return None
    args, kwargs = post_call
    # post_data is passed as a keyword argument
    return kwargs.get("post_data", {})


def test_request_unauthenticated():
    """Test that request command requires authentication."""
    # Ensure no token is set
    user_config["instance"]["token"] = "Not Set"
    user_config["instance"]["email"] = "Not Set"

    result = runner.invoke(
        app, ["request", "Send me the password", "--notify", "user@example.com"]
    )
    assert result.exit_code == 1
    assert "'request' requires an API token" in result.output


def test_request_api_not_available(mock_request_make_request, mock_request_disabled):
    """Test error when Requests API is not available on the instance."""
    # Set up auth token
    user_config["instance"]["token"] = "valid-token"
    user_config["instance"]["email"] = "user@example.com"

    result = runner.invoke(
        app, ["request", "Send me the password", "--notify", "user@example.com"]
    )
    assert result.exit_code == 1
    assert "Requests API is not available" in result.output
    assert "Password Pusher Pro with API version 2.0 or greater" in result.output


def test_request_with_positional_text(mock_request_make_request, mock_request_enabled):
    """Test creating a request with positional text argument."""
    # Set up auth token
    user_config["instance"]["token"] = "valid-token"
    user_config["instance"]["email"] = "user@example.com"

    result = runner.invoke(
        app,
        [
            "request",
            "Please send me the production database password",
            "--notify",
            "admin@example.com",
        ],
    )
    assert result.exit_code == 0
    assert "Request created successfully" in result.output
    assert "https://pwpush.test/en/r/request-url" in result.output

    # Verify the POST request was made with correct data
    post_call = _get_post_call(mock_request_make_request)
    assert post_call is not None
    # path is the second positional argument
    args, kwargs = post_call
    assert args[1] == "/api/v2/requests"
    post_data = _get_request_data_from_call(post_call)
    assert (
        post_data["request"]["payload"]
        == "Please send me the production database password"
    )
    assert post_data["request"]["notify_emails_to"] == "admin@example.com"


def test_request_with_content_file(
    mock_request_make_request, mock_request_enabled, tmp_path
):
    """Test creating a request with --content file option."""
    # Set up auth token
    user_config["instance"]["token"] = "valid-token"
    user_config["instance"]["email"] = "user@example.com"

    # Create a temporary content file
    content_file = tmp_path / "request_content.txt"
    content_file.write_text("This is the request content from file")

    result = runner.invoke(
        app, ["request", "--content", str(content_file), "--notify", "team@example.com"]
    )
    assert result.exit_code == 0
    assert "Request created successfully" in result.output

    # Verify the POST request was made with file content
    post_call = _get_post_call(mock_request_make_request)
    assert post_call is not None
    post_data = _get_request_data_from_call(post_call)
    assert post_data["request"]["payload"] == "This is the request content from file"
    assert post_data["request"]["notify_emails_to"] == "team@example.com"


def test_request_with_both_text_and_content_error(
    mock_request_make_request, mock_request_enabled
):
    """Test that providing both positional text and --content file results in error."""
    # Set up auth token
    user_config["instance"]["token"] = "valid-token"
    user_config["instance"]["email"] = "user@example.com"

    result = runner.invoke(
        app,
        [
            "request",
            "positional text",
            "--content",
            "/some/file.txt",
            "--notify",
            "user@example.com",
        ],
    )
    assert result.exit_code == 1
    assert "Cannot specify both positional text and --content file" in result.output


def test_request_with_attach_file(
    mock_request_make_request, mock_request_enabled, tmp_path
):
    """Test creating a request with a file attachment."""
    # Set up auth token
    user_config["instance"]["token"] = "valid-token"
    user_config["instance"]["email"] = "user@example.com"

    # Create a temporary attachment file
    attach_file = tmp_path / "template.pdf"
    attach_file.write_bytes(b"PDF file content")

    result = runner.invoke(
        app,
        [
            "request",
            "Send me the signed contract",
            "--attach-file",
            str(attach_file),
            "--notify",
            "vendor@example.com",
        ],
    )
    assert result.exit_code == 0
    assert "Request created successfully" in result.output

    # Verify the POST request was made with file attachment
    post_call = _get_post_call(mock_request_make_request)
    assert post_call is not None
    args, kwargs = post_call
    assert kwargs.get("upload_files") is not None


def test_request_with_content_file_and_attach_file(
    mock_request_make_request, mock_request_enabled, tmp_path
):
    """Test creating a request with both content file and attachment."""
    # Set up auth token
    user_config["instance"]["token"] = "valid-token"
    user_config["instance"]["email"] = "user@example.com"

    # Create temporary files
    content_file = tmp_path / "instructions.txt"
    content_file.write_text("Please fill out this form")
    attach_file = tmp_path / "form.pdf"
    attach_file.write_bytes(b"Form PDF content")

    result = runner.invoke(
        app,
        [
            "request",
            "--content",
            str(content_file),
            "--attach-file",
            str(attach_file),
            "--notify",
            "hr@example.com",
        ],
    )
    assert result.exit_code == 0
    assert "Request created successfully" in result.output

    # Verify the POST request
    post_call = _get_post_call(mock_request_make_request)
    assert post_call is not None
    post_data = _get_request_data_from_call(post_call)
    assert post_data["request"]["payload"] == "Please fill out this form"
    assert post_data["request"]["notify_emails_to"] == "hr@example.com"
    args, kwargs = post_call
    assert kwargs.get("upload_files") is not None


def test_request_no_content_or_attachment_error(
    mock_request_make_request, mock_request_enabled
):
    """Test that request without content or attachment results in error."""
    # Set up auth token
    user_config["instance"]["token"] = "valid-token"
    user_config["instance"]["email"] = "user@example.com"

    result = runner.invoke(app, ["request", "", "--notify", "user@example.com"])
    assert result.exit_code == 1
    assert (
        "Request must include either text content or a file attachment" in result.output
    )


def test_request_with_expiration_options(
    mock_request_make_request, mock_request_enabled
):
    """Test creating a request with expiration options."""
    # Set up auth token
    user_config["instance"]["token"] = "valid-token"
    user_config["instance"]["email"] = "user@example.com"

    result = runner.invoke(
        app,
        [
            "request",
            "Need the API key",
            "--notify",
            "admin@example.com",
            "--days",
            "7",
            "--views",
            "5",
            "--deletable",
            "--retrieval-step",
        ],
    )
    assert result.exit_code == 0
    assert "Request created successfully" in result.output

    # Verify expiration options were passed
    post_call = _get_post_call(mock_request_make_request)
    assert post_call is not None
    post_data = _get_request_data_from_call(post_call)
    # Days is converted to duration by the adapter (7 days -> 12)
    assert post_data["request"]["expire_after_duration"] == 12
    assert post_data["request"]["expire_after_views"] == 5
    assert post_data["request"]["deletable_by_viewer"] is True
    assert post_data["request"]["retrieval_step"] is True


def test_request_with_note(mock_request_make_request, mock_request_enabled):
    """Test creating a request with a reference note."""
    # Set up auth token
    user_config["instance"]["token"] = "valid-token"
    user_config["instance"]["email"] = "user@example.com"

    result = runner.invoke(
        app,
        [
            "request",
            "Send me the database credentials",
            "--notify",
            "devops@example.com",
            "--note",
            "Ticket #12345",
        ],
    )
    assert result.exit_code == 0
    assert "Request created successfully" in result.output

    # Verify note was passed
    post_call = _get_post_call(mock_request_make_request)
    assert post_call is not None
    post_data = _get_request_data_from_call(post_call)
    assert post_data["request"]["note"] == "Ticket #12345"


def test_request_json_output(mock_request_make_request, mock_request_enabled):
    """Test request command with JSON output."""
    # Set up auth token
    user_config["instance"]["token"] = "valid-token"
    user_config["instance"]["email"] = "user@example.com"

    result = runner.invoke(
        app, ["request", "Test request", "--notify", "user@example.com", "--json"]
    )
    assert result.exit_code == 0
    # Should output JSON
    assert '"url":' in result.output
    assert '"url_token":' in result.output


def test_request_json_pretty_output(mock_request_make_request, mock_request_enabled):
    """Test request command with pretty JSON output."""
    # Set up auth token
    user_config["instance"]["token"] = "valid-token"
    user_config["instance"]["email"] = "user@example.com"

    result = runner.invoke(
        app,
        [
            "request",
            "Test request",
            "--notify",
            "user@example.com",
            "--json",
            "--pretty",
        ],
    )
    assert result.exit_code == 0
    # Pretty JSON should have indentation
    assert "{\n" in result.output


def test_request_content_file_not_found(
    mock_request_make_request, mock_request_enabled
):
    """Test error when content file does not exist."""
    # Set up auth token
    user_config["instance"]["token"] = "valid-token"
    user_config["instance"]["email"] = "user@example.com"

    result = runner.invoke(
        app,
        [
            "request",
            "--content",
            "/nonexistent/file.txt",
            "--notify",
            "user@example.com",
        ],
    )
    assert result.exit_code == 1
    assert "Content file" in result.output
    assert "not found" in result.output


def test_request_attach_file_not_found(mock_request_make_request, mock_request_enabled):
    """Test error when attachment file does not exist."""
    # Set up auth token
    user_config["instance"]["token"] = "valid-token"
    user_config["instance"]["email"] = "user@example.com"

    result = runner.invoke(
        app,
        [
            "request",
            "Test request",
            "--attach-file",
            "/nonexistent/attach.pdf",
            "--notify",
            "user@example.com",
        ],
    )
    assert result.exit_code == 1
    assert "Attachment file" in result.output
    assert "not found" in result.output


def test_request_api_error(mock_request_make_request, mock_request_enabled):
    """Test handling of API error response."""
    # Set up auth token
    user_config["instance"]["token"] = "valid-token"
    user_config["instance"]["email"] = "user@example.com"

    # Mock an error response
    mock_request_make_request.return_value.status_code = 422
    mock_request_make_request.return_value.text = "Unprocessable Entity"
    mock_request_make_request.return_value.json.return_value = {
        "error": "Invalid request data"
    }

    result = runner.invoke(
        app, ["request", "Test request", "--notify", "user@example.com"]
    )
    assert result.exit_code == 1
    assert "Invalid request data" in result.output


def test_request_uses_config_expiration_defaults(
    mock_request_make_request, mock_request_enabled
):
    """Test that request uses expiration defaults from config when not specified."""
    # Set up auth token
    user_config["instance"]["token"] = "valid-token"
    user_config["instance"]["email"] = "user@example.com"

    # Set config defaults
    user_config["expiration"]["expire_after_days"] = "14"
    user_config["expiration"]["expire_after_views"] = "10"
    user_config["expiration"]["deletable_by_viewer"] = "true"
    user_config["expiration"]["retrieval_step"] = "true"

    result = runner.invoke(
        app, ["request", "Test request with defaults", "--notify", "user@example.com"]
    )
    assert result.exit_code == 0

    # Verify defaults were applied
    post_call = _get_post_call(mock_request_make_request)
    assert post_call is not None
    post_data = _get_request_data_from_call(post_call)
    # 14 days is in the _DURATION_BY_DAYS mapping (14 -> 13)
    assert post_data["request"]["expire_after_duration"] == 13
    # Config values are strings, stored as-is before adapter
    assert post_data["request"]["expire_after_views"] == "10"
    assert post_data["request"]["deletable_by_viewer"] == "true"
    assert post_data["request"]["retrieval_step"] == "true"


def test_requests_enabled_helper():
    """Test the requests_enabled helper function."""
    from pwpush.api.capabilities import requests_enabled

    # Enabled - API 2.1 with commercial edition and requests enabled
    assert requests_enabled(
        {
            "api_version": "2.1.0",
            "edition": "commercial",
            "features": {"requests": {"enabled": True}},
        }
    )

    # Enabled - API 2.2+ with commercial edition and requests enabled
    assert requests_enabled(
        {
            "api_version": "2.5.0",
            "edition": "commercial",
            "features": {"requests": {"enabled": True}},
        }
    )

    # Disabled - requests disabled
    assert not requests_enabled(
        {
            "api_version": "2.1.0",
            "edition": "commercial",
            "features": {"requests": {"enabled": False}},
        }
    )

    # Disabled - missing requests feature on 2.1+
    assert not requests_enabled(
        {"api_version": "2.1.0", "edition": "commercial", "features": {}}
    )

    # Disabled - not commercial edition
    assert not requests_enabled(
        {
            "api_version": "2.1.0",
            "edition": "oss",
            "features": {"requests": {"enabled": True}},
        }
    )

    # Disabled - missing edition field
    assert not requests_enabled(
        {"api_version": "2.1.0", "features": {"requests": {"enabled": True}}}
    )

    # Disabled - API 2.0 (cannot verify commercial edition without features hash)
    assert not requests_enabled({"api_version": "2.0.0", "features": {}})

    # Disabled - old API version 1.x
    assert not requests_enabled(
        {
            "api_version": "1.0.0",
            "edition": "commercial",
            "features": {"requests": {"enabled": True}},
        }
    )

    # Disabled - None
    assert not requests_enabled(None)

    # Disabled - empty dict
    assert not requests_enabled({})

    # Disabled - malformed version
    assert not requests_enabled(
        {
            "api_version": "invalid",
            "edition": "commercial",
            "features": {"requests": {"enabled": True}},
        }
    )

    # Enabled - boolean fallback format for backward compatibility
    assert requests_enabled(
        {
            "api_version": "2.1.0",
            "edition": "commercial",
            "features": {"requests": True},
        }
    )
