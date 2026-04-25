"""Tests for critical bug fixes."""

import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from pwpush.__main__ import app
from pwpush.utils import parse_boolean

runner = CliRunner()


def configure_api_credentials() -> None:
    """Configure authenticated command credentials for tests."""
    from pwpush.commands.config import user_config

    user_config["instance"]["email"] = "user@example.test"
    user_config["instance"]["token"] = "token-value"


def clear_api_token() -> None:
    """Clear only the API token for missing-token tests."""
    from pwpush.commands.config import user_config

    user_config["instance"]["email"] = "user@example.test"
    user_config["instance"]["token"] = "Not Set"


@pytest.fixture(autouse=True)
def default_legacy_profile():
    """Keep existing tests deterministic unless explicitly overridden."""
    with patch("pwpush.__main__.current_api_profile", return_value="legacy"):
        yield


def test_parse_boolean():
    """Test the parse_boolean utility function."""
    # Test boolean inputs
    assert parse_boolean(True) is True
    assert parse_boolean(False) is False

    # Test string inputs
    assert parse_boolean("true") is True
    assert parse_boolean("True") is True
    assert parse_boolean("TRUE") is True
    assert parse_boolean("yes") is True
    assert parse_boolean("on") is True
    assert parse_boolean("1") is True

    assert parse_boolean("false") is False
    assert parse_boolean("no") is False
    assert parse_boolean("off") is False
    assert parse_boolean("0") is False
    assert parse_boolean("") is False

    # Test invalid inputs
    assert parse_boolean(None) is False
    assert parse_boolean(123) is False


def test_push_deletable_by_viewer_true():
    """Test that deletable_by_viewer is set to True when --deletable is used."""
    with (
        patch("pwpush.__main__.make_request") as mock_request,
        patch("getpass.getpass") as mock_getpass,
    ):

        # Mock getpass to avoid interactive prompts
        mock_getpass.return_value = ""

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"url_token": "test-token"}

        mock_preview_response = MagicMock()
        mock_preview_response.json.return_value = {
            "url": "https://pwpush.com/en/p/test-token"
        }

        mock_request.side_effect = [mock_response, mock_preview_response]

        # Test with --deletable
        result = runner.invoke(
            app, ["push", "--secret", "test-password", "--deletable"]
        )

        assert result.exit_code == 0

        # Verify the request was made with correct deletable_by_viewer value
        call_args = mock_request.call_args_list[0]
        post_data = call_args[1]["post_data"]
        assert post_data["password"]["deletable_by_viewer"] is True


def test_push_deletable_by_viewer_false():
    """Test that deletable_by_viewer is set to False when --no-deletable is used."""
    with (
        patch("pwpush.__main__.make_request") as mock_request,
        patch("getpass.getpass") as mock_getpass,
    ):

        # Mock getpass to avoid interactive prompts
        mock_getpass.return_value = ""

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"url_token": "test-token"}

        mock_preview_response = MagicMock()
        mock_preview_response.json.return_value = {
            "url": "https://pwpush.com/en/p/test-token"
        }

        mock_request.side_effect = [mock_response, mock_preview_response]

        # Test with --no-deletable
        result = runner.invoke(
            app, ["push", "--secret", "test-password", "--no-deletable"]
        )

        assert result.exit_code == 0

        # Verify the request was made with correct deletable_by_viewer value
        call_args = mock_request.call_args_list[0]
        post_data = call_args[1]["post_data"]
        assert post_data["password"]["deletable_by_viewer"] is False


def test_push_deletable_by_viewer_none():
    """Test that deletable_by_viewer is not set when no flag is provided."""
    # Reset config values to ensure clean test state
    from pwpush.commands.config import user_config

    user_config["expiration"]["deletable_by_viewer"] = "Not Set"
    user_config["expiration"]["retrieval_step"] = "Not Set"

    with (
        patch("pwpush.__main__.make_request") as mock_request,
        patch("getpass.getpass") as mock_getpass,
    ):

        # Mock getpass to avoid interactive prompts
        mock_getpass.return_value = ""

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"url_token": "test-token"}

        mock_preview_response = MagicMock()
        mock_preview_response.json.return_value = {
            "url": "https://pwpush.com/en/p/test-token"
        }

        mock_request.side_effect = [mock_response, mock_preview_response]

        # Test without deletable flag
        result = runner.invoke(app, ["push", "--secret", "test-password"])

        assert result.exit_code == 0

        # Verify the request was made without deletable_by_viewer in payload
        call_args = mock_request.call_args_list[0]
        post_data = call_args[1]["post_data"]
        assert "deletable_by_viewer" not in post_data["password"]


def test_push_retrieval_step_true():
    """Test that retrieval_step is set to True when --retrieval-step is used."""
    with (
        patch("pwpush.__main__.make_request") as mock_request,
        patch("getpass.getpass") as mock_getpass,
    ):

        # Mock getpass to avoid interactive prompts
        mock_getpass.return_value = ""

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"url_token": "test-token"}

        mock_preview_response = MagicMock()
        mock_preview_response.json.return_value = {
            "url": "https://pwpush.com/en/p/test-token"
        }

        mock_request.side_effect = [mock_response, mock_preview_response]

        # Test with --retrieval-step
        result = runner.invoke(
            app, ["push", "--secret", "test-password", "--retrieval-step"]
        )

        assert result.exit_code == 0

        # Verify the request was made with correct retrieval_step value
        call_args = mock_request.call_args_list[0]
        post_data = call_args[1]["post_data"]
        assert post_data["password"]["retrieval_step"] is True


def test_push_retrieval_step_false():
    """Test that retrieval_step is set to False when --no-retrieval-step is used."""
    with (
        patch("pwpush.__main__.make_request") as mock_request,
        patch("getpass.getpass") as mock_getpass,
    ):

        # Mock getpass to avoid interactive prompts
        mock_getpass.return_value = ""

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"url_token": "test-token"}

        mock_preview_response = MagicMock()
        mock_preview_response.json.return_value = {
            "url": "https://pwpush.com/en/p/test-token"
        }

        mock_request.side_effect = [mock_response, mock_preview_response]

        # Test with --no-retrieval-step
        result = runner.invoke(
            app, ["push", "--secret", "test-password", "--no-retrieval-step"]
        )

        assert result.exit_code == 0

        # Verify the request was made with correct retrieval_step value
        call_args = mock_request.call_args_list[0]
        post_data = call_args[1]["post_data"]
        assert post_data["password"]["retrieval_step"] is False


def test_push_retrieval_step_none():
    """Test that retrieval_step is not set when no flag is provided."""
    # Reset config values to ensure clean test state
    from pwpush.commands.config import user_config

    user_config["expiration"]["deletable_by_viewer"] = "Not Set"
    user_config["expiration"]["retrieval_step"] = "Not Set"

    with (
        patch("pwpush.__main__.make_request") as mock_request,
        patch("getpass.getpass") as mock_getpass,
    ):

        # Mock getpass to avoid interactive prompts
        mock_getpass.return_value = ""

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"url_token": "test-token"}

        mock_preview_response = MagicMock()
        mock_preview_response.json.return_value = {
            "url": "https://pwpush.com/en/p/test-token"
        }

        mock_request.side_effect = [mock_response, mock_preview_response]

        # Test without retrieval_step flag
        result = runner.invoke(app, ["push", "--secret", "test-password"])

        assert result.exit_code == 0

        # Verify the request was made without retrieval_step in payload
        call_args = mock_request.call_args_list[0]
        post_data = call_args[1]["post_data"]
        assert "retrieval_step" not in post_data["password"]


def test_push_file_deletable_by_viewer_true():
    """Test that deletable_by_viewer is set to True when --deletable is used in push-file."""
    configure_api_credentials()

    with (
        patch("pwpush.__main__.make_request") as mock_request,
        patch("builtins.open", create=True) as mock_open,
    ):

        # Mock file content
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"url_token": "test-token"}

        mock_preview_response = MagicMock()
        mock_preview_response.json.return_value = {
            "url": "https://pwpush.com/en/f/test-token"
        }

        mock_request.side_effect = [mock_response, mock_preview_response]

        # Test with --deletable
        result = runner.invoke(app, ["push-file", "test-file.txt", "--deletable"])

        assert result.exit_code == 0

        # Verify the request was made with correct deletable_by_viewer value
        call_args = mock_request.call_args_list[0]
        post_data = call_args[1]["post_data"]
        assert post_data["file_push"]["deletable_by_viewer"] is True


def test_push_file_deletable_by_viewer_false():
    """Test that deletable_by_viewer is set to False when --no-deletable is used in push-file."""
    configure_api_credentials()

    with (
        patch("pwpush.__main__.make_request") as mock_request,
        patch("builtins.open", create=True) as mock_open,
    ):

        # Mock file content
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"url_token": "test-token"}

        mock_preview_response = MagicMock()
        mock_preview_response.json.return_value = {
            "url": "https://pwpush.com/en/f/test-token"
        }

        mock_request.side_effect = [mock_response, mock_preview_response]

        # Test with --no-deletable
        result = runner.invoke(app, ["push-file", "test-file.txt", "--no-deletable"])

        assert result.exit_code == 0

        # Verify the request was made with correct deletable_by_viewer value
        call_args = mock_request.call_args_list[0]
        post_data = call_args[1]["post_data"]
        assert post_data["file_push"]["deletable_by_viewer"] is False


def test_push_file_deletable_by_viewer_none():
    """Test that deletable_by_viewer is not set when no flag is provided in push-file."""
    configure_api_credentials()

    # Reset config values to ensure clean test state
    from pwpush.commands.config import user_config

    user_config["expiration"]["deletable_by_viewer"] = "Not Set"
    user_config["expiration"]["retrieval_step"] = "Not Set"

    with (
        patch("pwpush.__main__.make_request") as mock_request,
        patch("builtins.open", create=True) as mock_open,
    ):

        # Mock file content
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"url_token": "test-token"}

        mock_preview_response = MagicMock()
        mock_preview_response.json.return_value = {
            "url": "https://pwpush.com/en/f/test-token"
        }

        mock_request.side_effect = [mock_response, mock_preview_response]

        # Test without deletable flag
        result = runner.invoke(app, ["push-file", "test-file.txt"])

        assert result.exit_code == 0

        # Verify the request was made without deletable_by_viewer in payload
        call_args = mock_request.call_args_list[0]
        post_data = call_args[1]["post_data"]
        assert "deletable_by_viewer" not in post_data["file_push"]


def test_push_file_retrieval_step_true():
    """Test that retrieval_step is set to True when --retrieval-step is used in push-file."""
    configure_api_credentials()

    with (
        patch("pwpush.__main__.make_request") as mock_request,
        patch("builtins.open", create=True) as mock_open,
    ):

        # Mock file content
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"url_token": "test-token"}

        mock_preview_response = MagicMock()
        mock_preview_response.json.return_value = {
            "url": "https://pwpush.com/en/f/test-token"
        }

        mock_request.side_effect = [mock_response, mock_preview_response]

        # Test with --retrieval-step
        result = runner.invoke(app, ["push-file", "test-file.txt", "--retrieval-step"])

        assert result.exit_code == 0

        # Verify the request was made with correct retrieval_step value
        call_args = mock_request.call_args_list[0]
        post_data = call_args[1]["post_data"]
        assert post_data["file_push"]["retrieval_step"] is True


def test_push_file_retrieval_step_false():
    """Test that retrieval_step is set to False when --no-retrieval-step is used in push-file."""
    configure_api_credentials()

    with (
        patch("pwpush.__main__.make_request") as mock_request,
        patch("builtins.open", create=True) as mock_open,
    ):

        # Mock file content
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"url_token": "test-token"}

        mock_preview_response = MagicMock()
        mock_preview_response.json.return_value = {
            "url": "https://pwpush.com/en/f/test-token"
        }

        mock_request.side_effect = [mock_response, mock_preview_response]

        # Test with --no-retrieval-step
        result = runner.invoke(
            app, ["push-file", "test-file.txt", "--no-retrieval-step"]
        )

        assert result.exit_code == 0

        # Verify the request was made with correct retrieval_step value
        call_args = mock_request.call_args_list[0]
        post_data = call_args[1]["post_data"]
        assert post_data["file_push"]["retrieval_step"] is False


def test_push_file_retrieval_step_none():
    """Test that retrieval_step is not set when no flag is provided in push-file."""
    configure_api_credentials()

    # Reset config values to ensure clean test state
    from pwpush.commands.config import user_config

    user_config["expiration"]["deletable_by_viewer"] = "Not Set"
    user_config["expiration"]["retrieval_step"] = "Not Set"

    with (
        patch("pwpush.__main__.make_request") as mock_request,
        patch("builtins.open", create=True) as mock_open,
    ):

        # Mock file content
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"url_token": "test-token"}

        mock_preview_response = MagicMock()
        mock_preview_response.json.return_value = {
            "url": "https://pwpush.com/en/f/test-token"
        }

        mock_request.side_effect = [mock_response, mock_preview_response]

        # Test without retrieval_step flag
        result = runner.invoke(app, ["push-file", "test-file.txt"])

        assert result.exit_code == 0

        # Verify the request was made without retrieval_step in payload
        call_args = mock_request.call_args_list[0]
        post_data = call_args[1]["post_data"]
        assert "retrieval_step" not in post_data["file_push"]


def test_pretty_output_fix():
    """Test that pretty_output function checks the correct config key."""
    from pwpush.__main__ import pretty_output
    from pwpush.options import user_config

    # Test with pretty config set to true
    user_config["cli"]["pretty"] = "true"
    assert pretty_output() is True

    # Test with pretty config set to false
    user_config["cli"]["pretty"] = "false"
    assert pretty_output() is False


def test_file_not_found_error_handling():
    """Test that file not found errors are handled properly."""
    configure_api_credentials()

    result = runner.invoke(app, ["push-file", "nonexistent-file.txt"])

    assert result.exit_code == 1
    assert "File 'nonexistent-file.txt' not found" in result.output


def test_network_error_handling():
    """Test that network errors are handled properly."""
    with (
        patch("pwpush.__main__.make_request") as mock_request,
        patch("getpass.getpass") as mock_getpass,
    ):

        # Mock getpass to avoid interactive prompts
        mock_getpass.return_value = ""

        # Mock network error
        import requests

        mock_request.side_effect = requests.exceptions.ConnectionError(
            "Connection failed"
        )

        result = runner.invoke(app, ["push", "--secret", "test-password"])

        assert result.exit_code == 1
        # The error handling should catch the exception and exit with code 1
        # The exact error message format may vary, so we just check the exit code


def test_list_falls_back_to_modern_active_endpoint() -> None:
    """Test list command retries when the first endpoint is missing."""
    from pwpush.commands.config import user_config

    user_config["instance"]["email"] = "user@example.test"
    user_config["instance"]["token"] = "token-value"

    with (
        patch("pwpush.__main__.current_api_profile", return_value="legacy"),
        patch("pwpush.__main__.make_request") as mock_request,
    ):
        missing_endpoint = MagicMock()
        missing_endpoint.status_code = 404

        success_endpoint = MagicMock()
        success_endpoint.status_code = 200
        success_endpoint.json.return_value = []

        mock_request.side_effect = [missing_endpoint, success_endpoint]

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert mock_request.call_args_list[0].args[1] == "/p/active.json"
        assert mock_request.call_args_list[1].args[1] == "/api/v2/pushes/active"


def test_list_falls_back_to_modern_expired_endpoint() -> None:
    """Test expired list command retries when the first endpoint is missing."""
    from pwpush.commands.config import user_config

    user_config["instance"]["email"] = "user@example.test"
    user_config["instance"]["token"] = "token-value"

    with (
        patch("pwpush.__main__.current_api_profile", return_value="legacy"),
        patch("pwpush.__main__.make_request") as mock_request,
    ):
        missing_endpoint = MagicMock()
        missing_endpoint.status_code = 404

        success_endpoint = MagicMock()
        success_endpoint.status_code = 200
        success_endpoint.json.return_value = []

        mock_request.side_effect = [missing_endpoint, success_endpoint]

        result = runner.invoke(app, ["list", "--expired"])

        assert result.exit_code == 0
        assert mock_request.call_args_list[0].args[1] == "/p/expired.json"
        assert mock_request.call_args_list[1].args[1] == "/api/v2/pushes/expired"


def test_list_prefers_v2_endpoint_when_profile_is_v2() -> None:
    """Test list command starts with v2 endpoint when available."""
    from pwpush.commands.config import user_config

    user_config["instance"]["email"] = "user@example.test"
    user_config["instance"]["token"] = "token-value"

    with (
        patch("pwpush.__main__.current_api_profile", return_value="v2"),
        patch("pwpush.__main__.make_request") as mock_request,
    ):
        success_endpoint = MagicMock()
        success_endpoint.status_code = 200
        success_endpoint.json.return_value = []
        mock_request.return_value = success_endpoint

        result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert mock_request.call_args_list[0].args[1] == "/api/v2/pushes/active"


def test_list_without_api_token_fails_before_request() -> None:
    """Test list requires an API token before any API work."""
    clear_api_token()

    with (
        patch("pwpush.__main__.current_api_profile") as mock_profile,
        patch("pwpush.__main__.make_request") as mock_request,
    ):
        result = runner.invoke(app, ["list"])

        assert result.exit_code == 1
        assert "requires an API token" in result.stdout
        mock_profile.assert_not_called()
        mock_request.assert_not_called()


def test_audit_without_api_token_fails_before_request() -> None:
    """Test audit requires an API token before any API work."""
    clear_api_token()

    with (
        patch("pwpush.__main__.current_api_profile") as mock_profile,
        patch("pwpush.__main__.make_request") as mock_request,
    ):
        result = runner.invoke(app, ["audit", "abc123"])

        assert result.exit_code == 1
        assert "requires an API token" in result.stdout
        mock_profile.assert_not_called()
        mock_request.assert_not_called()


def test_push_uses_v2_paths_and_payload_shape() -> None:
    """Test push command uses v2 endpoint and payload envelope."""
    with (
        patch("pwpush.__main__.current_api_profile", return_value="v2"),
        patch("pwpush.__main__.make_request") as mock_request,
    ):
        create_response = MagicMock()
        create_response.status_code = 201
        create_response.json.return_value = {"url_token": "test-token"}

        preview_response = MagicMock()
        preview_response.status_code = 200
        preview_response.json.return_value = {
            "url": "https://pwpush.com/en/p/test-token"
        }

        mock_request.side_effect = [create_response, preview_response]

        result = runner.invoke(
            app,
            ["push", "--secret", "test-password", "--days", "7", "--kind", "url"],
        )

        assert result.exit_code == 0
        assert mock_request.call_args_list[0].args[1] == "/api/v2/pushes"
        post_data = mock_request.call_args_list[0].kwargs["post_data"]
        assert "push" in post_data
        assert "password" not in post_data
        assert post_data["push"]["expire_after_duration"] == 12
        assert post_data["push"]["kind"] == "url"
        assert (
            mock_request.call_args_list[1].args[1]
            == "/api/v2/pushes/test-token/preview"
        )


def test_push_file_uses_v2_paths_payload_and_upload_key() -> None:
    """Test push-file command uses v2 endpoint and multipart key mapping."""
    configure_api_credentials()

    with (
        patch("pwpush.__main__.current_api_profile", return_value="v2"),
        patch("pwpush.__main__.make_request") as mock_request,
        patch("builtins.open", create=True) as mock_open,
    ):
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        create_response = MagicMock()
        create_response.status_code = 201
        create_response.json.return_value = {"url_token": "file-token"}

        preview_response = MagicMock()
        preview_response.status_code = 200
        preview_response.json.return_value = {
            "url": "https://pwpush.com/en/f/file-token"
        }
        mock_request.side_effect = [create_response, preview_response]

        result = runner.invoke(app, ["push-file", "test-file.txt", "--days", "7"])

        assert result.exit_code == 0
        assert mock_request.call_args_list[0].args[1] == "/api/v2/pushes"
        post_data = mock_request.call_args_list[0].kwargs["post_data"]
        upload_files = mock_request.call_args_list[0].kwargs["upload_files"]
        assert "push" in post_data
        assert post_data["push"]["kind"] == "file"
        assert post_data["push"]["expire_after_duration"] == 12
        assert "push[files][]" in upload_files
        assert "file_push[files][]" not in upload_files
        assert (
            mock_request.call_args_list[1].args[1]
            == "/api/v2/pushes/file-token/preview"
        )


def test_push_file_without_api_token_fails_before_request() -> None:
    """Test push-file requires an API token before any API work."""
    clear_api_token()

    with (
        patch("pwpush.__main__.current_api_profile") as mock_profile,
        patch("pwpush.__main__.make_request") as mock_request,
    ):
        result = runner.invoke(app, ["push-file", "test-file.txt"])

        assert result.exit_code == 1
        assert "requires an API token" in result.stdout
        mock_profile.assert_not_called()
        mock_request.assert_not_called()


def test_expire_uses_v2_endpoint() -> None:
    """Test expire command uses v2 route when profile is v2."""
    from pwpush.commands.config import user_config

    # Set up auth token so we don't fail auth check
    original_token = user_config["instance"]["token"]
    user_config["instance"]["token"] = "test-token"

    try:
        with (
            patch("pwpush.__main__.current_api_profile", return_value="v2"),
            patch("pwpush.__main__.make_request") as mock_request,
        ):
            success_response = MagicMock()
            success_response.status_code = 200
            success_response.json.return_value = {}
            mock_request.return_value = success_response

            result = runner.invoke(app, ["expire", "abc123"])

            assert result.exit_code == 0
            assert mock_request.call_args_list[0].args[1] == "/api/v2/pushes/abc123"
    finally:
        user_config["instance"]["token"] = original_token


def test_expire_without_token_shows_help() -> None:
    """Test expire command shows help instead of making a request without a token."""
    with patch("pwpush.__main__.make_request") as mock_request:
        result = runner.invoke(app, ["expire"])

        assert result.exit_code == 0
        assert "Usage:" in result.stdout
        assert "Expire a push." in result.stdout
        assert "URL_TOKEN" in result.stdout
        mock_request.assert_not_called()


def test_audit_supports_v2_logs_shape() -> None:
    """Test audit command handles v2 logs response shape."""
    from pwpush.commands.config import user_config

    user_config["instance"]["email"] = "user@example.test"
    user_config["instance"]["token"] = "token-value"

    with (
        patch("pwpush.__main__.current_api_profile", return_value="v2"),
        patch("pwpush.__main__.make_request") as mock_request,
    ):
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "logs": [
                {
                    "ip": "127.0.0.1",
                    "user_agent": "pytest",
                    "referrer": None,
                    "kind": "creation",
                    "created_at": "2026-01-01T10:00:00.000Z",
                }
            ]
        }
        mock_request.return_value = success_response

        result = runner.invoke(app, ["audit", "abc123"])

        assert result.exit_code == 0
        assert mock_request.call_args_list[0].args[1] == "/api/v2/pushes/abc123/audit"


def test_audit_without_token_shows_help() -> None:
    """Test audit command shows help instead of checking auth without a token."""
    with patch("pwpush.__main__.make_request") as mock_request:
        result = runner.invoke(app, ["audit"])

        assert result.exit_code == 0
        assert "Usage:" in result.stdout
        assert "Show the audit log for the given push." in result.stdout
        assert "Requires login with an API token." in result.stdout
        assert "URL_TOKEN" in result.stdout
        mock_request.assert_not_called()


def test_audit_help_mentions_api_token_requirement() -> None:
    """Test audit help explains authentication requirements."""
    result = runner.invoke(app, ["audit", "--help"])

    assert result.exit_code == 0
    assert "Requires login with an API token." in result.stdout


def test_version_flag_prints_version() -> None:
    """Test --version flag prints version and exits immediately."""
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "pwpush version:" in result.stdout
    # Should not show welcome screen or prompt for config
    assert "Password Pusher CLI" not in result.stdout
    assert "setup wizard" not in result.stdout.lower()


def test_version_from_pyproject_toml() -> None:
    """Test get_version() reads from pyproject.toml when package not installed."""
    from importlib import metadata as importlib_metadata

    from pwpush import get_version

    with patch.object(
        importlib_metadata,
        "version",
        side_effect=importlib_metadata.PackageNotFoundError,
    ):
        version = get_version()

        # Should successfully read version from pyproject.toml
        assert version != "unknown"
        assert version.count(".") >= 1  # Basic semver check


def test_version_unknown_when_no_package_or_pyproject() -> None:
    """Test get_version() returns 'unknown' when package not installed and pyproject missing."""
    from importlib import metadata as importlib_metadata

    from pwpush import get_version

    with (
        patch.object(
            importlib_metadata,
            "version",
            side_effect=importlib_metadata.PackageNotFoundError,
        ),
        patch("pwpush.Path.exists", return_value=False),
    ):
        version = get_version()

        assert version == "unknown"
