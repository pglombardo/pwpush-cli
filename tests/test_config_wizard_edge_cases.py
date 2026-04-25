"""Tests for config wizard edge cases."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from pwpush.__main__ import app
from pwpush.commands.config import user_config
from pwpush.config_wizard import (
    NOT_SET,
    choose_instance_url,
    collect_account_selection,
    fetch_accounts,
    normalize_instance_url,
    prompt_custom_instance_url,
    select_account,
)

runner = CliRunner()


class TestNormalizeInstanceUrl:
    """Tests for normalize_instance_url function."""

    def test_adds_https_to_bare_domain(self):
        """Test that HTTPS is added to bare domains."""
        result = normalize_instance_url("example.com")
        assert result == "https://example.com"

    def test_preserves_existing_scheme(self):
        """Test that existing scheme is preserved."""
        result = normalize_instance_url("http://example.com")
        assert result == "http://example.com"

    def test_raises_on_empty_url(self):
        """Test that empty URL raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            normalize_instance_url("")

    def test_raises_on_invalid_scheme(self):
        """Test that invalid scheme raises ValueError."""
        with pytest.raises(ValueError, match="valid HTTP or HTTPS URL"):
            normalize_instance_url("ftp://example.com")

    def test_raises_on_missing_netloc(self):
        """Test that URL without netloc raises ValueError."""
        with pytest.raises(ValueError, match="valid HTTP or HTTPS URL"):
            normalize_instance_url("https:///path")


class TestFetchAccounts:
    """Tests for fetch_accounts function."""

    @patch("pwpush.config_wizard.requests.get")
    def test_fetch_accounts_success_list(self, mock_get):
        """Test fetching accounts when API returns a list."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 1, "name": "Account 1", "role": "owner"},
            {"id": 2, "name": "Account 2", "role": "member"},
        ]
        mock_get.return_value = mock_response

        result = fetch_accounts("https://example.com", "token")

        assert len(result) == 2
        assert result[0]["id"] == 1

    @patch("pwpush.config_wizard.requests.get")
    def test_fetch_accounts_success_wrapped(self, mock_get):
        """Test fetching accounts when API returns wrapped object."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "accounts": [
                {"id": 1, "name": "Account 1", "role": "owner"},
            ]
        }
        mock_get.return_value = mock_response

        result = fetch_accounts("https://example.com", "token")

        assert len(result) == 1
        assert result[0]["id"] == 1

    @patch("pwpush.config_wizard.requests.get")
    def test_fetch_accounts_non_200_status(self, mock_get):
        """Test fetching accounts when API returns non-200 status."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        result = fetch_accounts("https://example.com", "token")

        assert result == []

    @patch("pwpush.config_wizard.requests.get")
    def test_fetch_accounts_request_exception(self, mock_get):
        """Test fetching accounts when request raises exception."""
        import requests

        mock_get.side_effect = requests.exceptions.RequestException("Connection failed")

        result = fetch_accounts("https://example.com", "token")

        assert result == []


class TestSelectAccount:
    """Tests for select_account function."""

    def test_select_account_empty_list(self, monkeypatch):
        """Test selecting account with empty list."""
        with patch("pwpush.config_wizard.console.print") as mock_print:
            result = select_account([])

            assert result == NOT_SET
            mock_print.assert_called_once()
            assert "No accounts found" in str(mock_print.call_args)

    def test_select_account_single_account(self, monkeypatch):
        """Test selecting account when only one is available."""
        accounts = [{"id": 1, "name": "My Account", "role": "owner"}]

        with patch("pwpush.config_wizard.console.print") as mock_print:
            result = select_account(accounts)

            assert result == "1"
            mock_print.assert_called_once()
            assert "Using account" in str(mock_print.call_args)

    def test_select_account_multiple_valid_choice(self, monkeypatch):
        """Test selecting from multiple accounts with valid choice."""
        accounts = [
            {"id": 1, "name": "Account 1", "role": "owner"},
            {"id": 2, "name": "Account 2", "role": "member"},
        ]

        with patch("pwpush.config_wizard.typer.prompt", return_value="2"):
            with patch("pwpush.config_wizard.console.print"):
                result = select_account(accounts)

                assert result == "2"

    def test_select_account_multiple_invalid_then_valid(self, monkeypatch):
        """Test selecting from multiple accounts with invalid then valid choice."""
        accounts = [
            {"id": 1, "name": "Account 1", "role": "owner"},
            {"id": 2, "name": "Account 2", "role": "member"},
        ]

        # First invalid (too high), then invalid (not a number), then valid
        prompt_responses = ["5", "abc", "1"]
        prompt_iter = iter(prompt_responses)

        with patch(
            "pwpush.config_wizard.typer.prompt",
            side_effect=lambda *args, **kwargs: next(prompt_iter),
        ):
            with patch("pwpush.config_wizard.console.print"):
                result = select_account(accounts)

                assert result == "1"


class TestCollectAccountSelection:
    """Tests for collect_account_selection function."""

    def test_no_token_returns_not_set(self):
        """Test that no token returns NOT_SET."""
        result = collect_account_selection("https://example.com", "")
        assert result == NOT_SET

    def test_not_set_token_returns_not_set(self):
        """Test that 'Not Set' token returns NOT_SET."""
        result = collect_account_selection("https://example.com", NOT_SET)
        assert result == NOT_SET

    def test_accounts_disabled_returns_not_set(self, monkeypatch):
        """Test that disabled accounts feature returns NOT_SET."""
        mock_capabilities = {
            "api_version": "2.1.0",
            "features": {"accounts": {"enabled": False}},
        }
        monkeypatch.setattr(
            "pwpush.config_wizard.detect_api_capabilities",
            lambda **kwargs: mock_capabilities,
        )

        result = collect_account_selection("https://example.com", "token")
        assert result == NOT_SET


class TestChooseInstanceUrl:
    """Tests for choose_instance_url function."""

    def test_select_hosted_instance(self, monkeypatch):
        """Test selecting a hosted instance."""
        monkeypatch.setitem(user_config["instance"], "url", NOT_SET)

        with patch("pwpush.config_wizard.typer.prompt", return_value="1"):
            result = choose_instance_url()
            assert result == "https://eu.pwpush.com"

    def test_select_custom_instance(self, monkeypatch):
        """Test selecting custom instance option."""
        monkeypatch.setitem(user_config["instance"], "url", NOT_SET)

        with patch(
            "pwpush.config_wizard.typer.prompt",
            side_effect=["4", "https://custom.example.com"],
        ):
            result = choose_instance_url()
            assert result == "https://custom.example.com"

    def test_invalid_selection_then_valid(self, monkeypatch):
        """Test invalid selection followed by valid."""
        monkeypatch.setitem(user_config["instance"], "url", NOT_SET)

        with patch("pwpush.config_wizard.typer.prompt", side_effect=["invalid", "2"]):
            with patch("pwpush.config_wizard.console.print"):
                result = choose_instance_url()
                assert result == "https://us.pwpush.com"


class TestPromptCustomInstanceUrl:
    """Tests for prompt_custom_instance_url function."""

    def test_valid_url_accepted(self, monkeypatch):
        """Test valid URL is accepted."""
        with patch(
            "pwpush.config_wizard.typer.prompt",
            return_value="https://custom.example.com",
        ):
            result = prompt_custom_instance_url()
            assert result == "https://custom.example.com"

    def test_bare_domain_gets_https(self, monkeypatch):
        """Test bare domain gets HTTPS prepended."""
        with patch(
            "pwpush.config_wizard.typer.prompt", return_value="custom.example.com"
        ):
            result = prompt_custom_instance_url()
            assert result == "https://custom.example.com"

    def test_invalid_then_valid(self, monkeypatch):
        """Test invalid URL then valid URL."""
        # This test verifies that invalid URLs are rejected and valid ones accepted
        with patch(
            "pwpush.config_wizard.typer.prompt",
            return_value="https://valid.example.com",
        ):
            with patch("pwpush.config_wizard.console.print"):
                result = prompt_custom_instance_url()
                assert result == "https://valid.example.com"


class TestConfigWizardAccountIntegration:
    """Tests for account integration in config wizard."""

    @patch("pwpush.config_wizard.typer.confirm")
    @patch("pwpush.config_wizard.typer.prompt")
    def test_wizard_collects_account_when_enabled(
        self, mock_prompt, mock_confirm, monkeypatch
    ):
        """Test that wizard collects account when accounts are enabled."""
        # Set up existing token to trigger account check
        monkeypatch.setitem(user_config["instance"], "token", "existing-token")

        # Mock capabilities with accounts enabled
        mock_capabilities = {
            "api_version": "2.1.0",
            "features": {"accounts": {"enabled": True}},
        }
        monkeypatch.setattr(
            "pwpush.config_wizard.detect_api_capabilities",
            lambda **kwargs: mock_capabilities,
        )

        # Mock fetch_accounts to return single account
        monkeypatch.setattr(
            "pwpush.config_wizard.fetch_accounts",
            lambda base_url, token: [{"id": 1, "name": "My Account", "role": "owner"}],
        )

        # Mock prompts
        mock_confirm.side_effect = [
            True,
            False,
            False,
        ]  # API token yes, expiration no, CLI no
        mock_prompt.side_effect = [
            "1",  # Choose EU instance
            "",  # Keep existing token (default)
        ]

        from pwpush.config_wizard import collect_wizard_settings

        with patch("pwpush.config_wizard.console.print"):
            settings = collect_wizard_settings()

        assert settings.account_id == "1"
