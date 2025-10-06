"""Tests for critical bug fixes."""

import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from pwpush.__main__ import app, parse_boolean

runner = CliRunner()


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


def test_push_deletable_by_viewer_fix():
    """Test that deletable_by_viewer is set correctly in push command."""
    with patch("pwpush.__main__.make_request") as mock_request:
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"url_token": "test-token"}

        mock_preview_response = MagicMock()
        mock_preview_response.json.return_value = {
            "url": "https://pwpush.com/en/p/test-token"
        }

        mock_request.side_effect = [mock_response, mock_preview_response]

        # Test with deletable=True
        result = runner.invoke(
            app, ["push", "--secret", "test-password", "--deletable", "true"]
        )

        assert result.exit_code == 0

        # Verify the request was made with correct deletable_by_viewer value
        call_args = mock_request.call_args_list[0]
        post_data = call_args[1]["post_data"]
        assert post_data["password"]["deletable_by_viewer"] is True


def test_push_retrieval_step_fix():
    """Test that retrieval_step is set correctly in push command."""
    with patch("pwpush.__main__.make_request") as mock_request:
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"url_token": "test-token"}

        mock_preview_response = MagicMock()
        mock_preview_response.json.return_value = {
            "url": "https://pwpush.com/en/p/test-token"
        }

        mock_request.side_effect = [mock_response, mock_preview_response]

        # Test with retrieval_step=True
        result = runner.invoke(
            app, ["push", "--secret", "test-password", "--retrieval-step", "true"]
        )

        assert result.exit_code == 0

        # Verify the request was made with correct retrieval_step value
        call_args = mock_request.call_args_list[0]
        post_data = call_args[1]["post_data"]
        assert post_data["password"]["retrieval_step"] is True


def test_push_file_deletable_by_viewer_fix():
    """Test that deletable_by_viewer is set correctly in push-file command."""
    with patch("pwpush.__main__.make_request") as mock_request, patch(
        "builtins.open", create=True
    ) as mock_open:

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

        # Test with deletable=True
        result = runner.invoke(
            app, ["push-file", "test-file.txt", "--deletable", "true"]
        )

        assert result.exit_code == 0

        # Verify the request was made with correct deletable_by_viewer value
        call_args = mock_request.call_args_list[0]
        post_data = call_args[1]["post_data"]
        assert post_data["file_push"]["deletable_by_viewer"] is True


def test_push_file_retrieval_step_fix():
    """Test that retrieval_step is set correctly in push-file command."""
    with patch("pwpush.__main__.make_request") as mock_request, patch(
        "builtins.open", create=True
    ) as mock_open:

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

        # Test with retrieval_step=True
        result = runner.invoke(
            app, ["push-file", "test-file.txt", "--retrieval-step", "true"]
        )

        assert result.exit_code == 0

        # Verify the request was made with correct retrieval_step value
        call_args = mock_request.call_args_list[0]
        post_data = call_args[1]["post_data"]
        assert post_data["file_push"]["retrieval_step"] is True


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
    result = runner.invoke(app, ["push-file", "nonexistent-file.txt"])

    assert result.exit_code == 1
    assert "File 'nonexistent-file.txt' not found" in result.output


def test_network_error_handling():
    """Test that network errors are handled properly."""
    with patch("pwpush.__main__.make_request") as mock_request:
        # Mock network error
        import requests

        mock_request.side_effect = requests.exceptions.ConnectionError(
            "Connection failed"
        )

        result = runner.invoke(app, ["push", "--secret", "test-password"])

        assert result.exit_code == 1
        assert "Could not connect to" in result.output
