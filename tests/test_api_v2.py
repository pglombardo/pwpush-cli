"""Tests for API v2 paths and capabilities."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from pwpush.api.capabilities import (
    API_PROFILE_LEGACY,
    API_PROFILE_V2,
    accounts_enabled,
    clear_capabilities_cache,
    clear_profile_cache,
    detect_api_capabilities,
    detect_api_profile,
    email_notifications_enabled,
)
from pwpush.api.endpoints import (
    adapt_file_payload_for_profile,
    adapt_file_uploads_for_profile,
    adapt_text_payload_for_profile,
    normalize_audit_events,
    push_audit_path,
    push_create_path,
    push_expire_path,
    push_preview_path,
    validation_paths,
)


class TestClearCaches:
    """Tests for cache clearing functions."""

    def test_clear_profile_cache(self):
        """Test that profile cache is cleared."""
        # First populate the cache
        with patch("pwpush.api.capabilities.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            detect_api_profile(
                base_url="https://example.com", email="test@test.com", token="token"
            )

        # Clear and verify
        clear_profile_cache()
        # After clearing, a new call should be made
        with patch("pwpush.api.capabilities.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            detect_api_profile(
                base_url="https://example.com", email="test@test.com", token="token"
            )
            assert mock_get.called

    def test_clear_capabilities_cache(self):
        """Test that capabilities cache is cleared."""
        clear_capabilities_cache()
        # After clearing, a new call should be made
        with patch("pwpush.api.capabilities.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"api_version": "2.1.0", "features": {}}
            mock_get.return_value = mock_response
            detect_api_capabilities(
                base_url="https://example.com", email="test@test.com", token="token"
            )
            assert mock_get.called


class TestDetectApiProfileForceRefresh:
    """Tests for force_refresh parameter in detect_api_profile."""

    def test_force_refresh_skips_cache(self):
        """Test that force_refresh=True skips cache lookup."""
        # Clear cache first
        clear_profile_cache()

        with patch("pwpush.api.capabilities.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # First call to populate cache
            detect_api_profile(
                base_url="https://force-refresh-test.com",
                email="test@test.com",
                token="token",
            )

            # Second call with force_refresh should still make a request
            detect_api_profile(
                base_url="https://force-refresh-test.com",
                email="test@test.com",
                token="token",
                force_refresh=True,
            )

            # Should have made 2 requests (one for each call, since force_refresh bypasses cache)
            assert mock_get.call_count == 2


class TestEmailNotificationsEnabled:
    """Tests for email_notifications_enabled function edge cases."""

    def test_version_parsing_edge_cases(self):
        """Test version parsing with various edge cases."""
        # Version with only major.minor (no patch)
        assert email_notifications_enabled(
            {
                "api_version": "2.1",
                "features": {"pushes": {"email_auto_dispatch": True}},
            }
        )

        # Version with extra parts
        assert email_notifications_enabled(
            {
                "api_version": "2.1.0.1",
                "features": {"pushes": {"email_auto_dispatch": True}},
            }
        )

        # Invalid version string
        assert not email_notifications_enabled(
            {
                "api_version": "not-a-version",
                "features": {"pushes": {"email_auto_dispatch": True}},
            }
        )

        # Empty version
        assert not email_notifications_enabled(
            {"api_version": "", "features": {"pushes": {"email_auto_dispatch": True}}}
        )

    def test_missing_api_version(self):
        """Test when api_version is missing."""
        assert not email_notifications_enabled(
            {"features": {"pushes": {"email_auto_dispatch": True}}}
        )

    def test_missing_features(self):
        """Test when features dict is missing."""
        assert not email_notifications_enabled({"api_version": "2.1.0"})


class TestAccountsEnabled:
    """Tests for accounts_enabled function."""

    def test_accounts_enabled_true(self):
        """Test when accounts are enabled."""
        capabilities = {
            "api_version": "2.1.0",
            "features": {"accounts": {"enabled": True}},
        }
        assert accounts_enabled(capabilities)

    def test_accounts_enabled_false(self):
        """Test when accounts are disabled."""
        capabilities = {
            "api_version": "2.1.0",
            "features": {"accounts": {"enabled": False}},
        }
        assert not accounts_enabled(capabilities)

    def test_accounts_enabled_old_api(self):
        """Test with old API version."""
        capabilities = {
            "api_version": "2.0.0",
            "features": {"accounts": {"enabled": True}},
        }
        assert not accounts_enabled(capabilities)

    def test_accounts_enabled_no_accounts_key(self):
        """Test when accounts key is missing."""
        capabilities = {"api_version": "2.1.0", "features": {}}
        assert not accounts_enabled(capabilities)

    def test_accounts_enabled_none_capabilities(self):
        """Test with None capabilities."""
        assert not accounts_enabled(None)

    def test_accounts_enabled_invalid_version(self):
        """Test with invalid version string."""
        capabilities = {
            "api_version": "invalid",
            "features": {"accounts": {"enabled": True}},
        }
        assert not accounts_enabled(capabilities)


class TestDetectApiCapabilitiesDebug:
    """Tests for debug output in detect_api_capabilities."""

    def test_debug_output_on_success(self):
        """Test debug output when API call succeeds."""
        clear_capabilities_cache()

        with patch("pwpush.api.capabilities.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "api_version": "2.1.0",
                "features": {"email_auto_dispatch": True},
            }
            mock_get.return_value = mock_response

            with patch("pwpush.api.capabilities.rprint") as mock_rprint:
                detect_api_capabilities(
                    base_url="https://debug-success-test.com",
                    email="test@test.com",
                    token="token",
                    debug=True,
                )

                mock_rprint.assert_called_once()
                assert "API capabilities detected" in str(mock_rprint.call_args)

    def test_debug_output_on_failure(self):
        """Test debug output when API call fails."""
        clear_capabilities_cache()

        with patch("pwpush.api.capabilities.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            with patch("pwpush.api.capabilities.rprint") as mock_rprint:
                detect_api_capabilities(
                    base_url="https://debug-failure-test.com",
                    email="test@test.com",
                    token="token",
                    debug=True,
                )

                mock_rprint.assert_called_once()
                assert "API capabilities check failed" in str(mock_rprint.call_args)

    def test_debug_output_on_exception(self):
        """Test debug output when request raises exception."""
        clear_capabilities_cache()

        with patch("pwpush.api.capabilities.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException(
                "Connection failed"
            )

            with patch("pwpush.api.capabilities.rprint") as mock_rprint:
                detect_api_capabilities(
                    base_url="https://debug-error-test.com",
                    email="test@test.com",
                    token="token",
                    debug=True,
                )

                mock_rprint.assert_called_once()
                assert "API capabilities check error" in str(mock_rprint.call_args)


class TestValidationPaths:
    """Tests for validation_paths function."""

    def test_v2_expired_paths(self):
        """Test v2 paths for expired pushes."""
        paths = validation_paths(API_PROFILE_V2, expired=True)
        assert "/api/v2/pushes/expired" in paths
        assert "/p/expired.json" in paths

    def test_legacy_active_paths(self):
        """Test legacy paths for active pushes."""
        paths = validation_paths(API_PROFILE_LEGACY, expired=False)
        assert "/p/active.json" in paths
        assert "/en/d/active.json" in paths


class TestPushCreatePath:
    """Tests for push_create_path function."""

    def test_v2_create_path(self):
        """Test v2 push creation path."""
        assert push_create_path(API_PROFILE_V2, "text") == "/api/v2/pushes"
        assert push_create_path(API_PROFILE_V2, "file") == "/api/v2/pushes"

    def test_legacy_text_path(self):
        """Test legacy text push creation path."""
        assert push_create_path(API_PROFILE_LEGACY, "text") == "/p.json"

    def test_legacy_file_path(self):
        """Test legacy file push creation path."""
        assert push_create_path(API_PROFILE_LEGACY, "file") == "/f.json"


class TestPushPreviewPath:
    """Tests for push_preview_path function."""

    def test_v2_preview_path(self):
        """Test v2 preview path."""
        assert (
            push_preview_path(API_PROFILE_V2, "token123", "text")
            == "/api/v2/pushes/token123/preview"
        )

    def test_legacy_text_preview(self):
        """Test legacy text preview path."""
        assert (
            push_preview_path(API_PROFILE_LEGACY, "token123", "text")
            == "/p/token123/preview.json"
        )

    def test_legacy_file_preview(self):
        """Test legacy file preview path."""
        assert (
            push_preview_path(API_PROFILE_LEGACY, "token123", "file")
            == "/f/token123/preview.json"
        )


class TestPushExpirePath:
    """Tests for push_expire_path function."""

    def test_v2_expire_path(self):
        """Test v2 expire path."""
        assert push_expire_path(API_PROFILE_V2, "token123") == "/api/v2/pushes/token123"

    def test_legacy_expire_path(self):
        """Test legacy expire path."""
        assert push_expire_path(API_PROFILE_LEGACY, "token123") == "/p/token123.json"


class TestPushAuditPath:
    """Tests for push_audit_path function."""

    def test_v2_audit_path(self):
        """Test v2 audit path."""
        assert (
            push_audit_path(API_PROFILE_V2, "token123")
            == "/api/v2/pushes/token123/audit"
        )

    def test_legacy_audit_path(self):
        """Test legacy audit path."""
        assert (
            push_audit_path(API_PROFILE_LEGACY, "token123") == "/p/token123/audit.json"
        )


class TestAdaptTextPayloadForProfile:
    """Tests for adapt_text_payload_for_profile function."""

    def test_legacy_payload_unchanged(self):
        """Test that legacy payload is returned unchanged."""
        payload = {"password": {"payload": "secret", "kind": "text"}}
        result = adapt_text_payload_for_profile(payload, API_PROFILE_LEGACY)
        assert result == payload

    def test_v2_basic_conversion(self):
        """Test basic v2 payload conversion."""
        payload = {"password": {"payload": "secret", "kind": "text"}}
        result = adapt_text_payload_for_profile(payload, API_PROFILE_V2)
        assert result == {"push": {"payload": "secret", "kind": "text"}}

    def test_v2_with_all_fields(self):
        """Test v2 conversion with all optional fields."""
        payload = {
            "password": {
                "payload": "secret",
                "kind": "url",
                "expire_after_views": 5,
                "expire_after_days": 7,
                "note": "test note",
                "deletable_by_viewer": True,
                "retrieval_step": False,
                "passphrase": "secret-pass",
                "notify_emails_to": "admin@example.com",
                "notify_emails_to_locale": "en",
            }
        }
        result = adapt_text_payload_for_profile(payload, API_PROFILE_V2)
        push = result["push"]
        assert push["payload"] == "secret"
        assert push["kind"] == "url"
        assert push["expire_after_views"] == 5
        assert push["expire_after_duration"] == 12  # 7 days maps to duration 12
        assert push["note"] == "test note"
        assert push["deletable_by_viewer"] is True
        assert push["retrieval_step"] is False
        assert push["passphrase"] == "secret-pass"
        assert push["notify_emails_to"] == "admin@example.com"
        assert push["notify_emails_to_locale"] == "en"

    def test_v2_unknown_days_mapping(self):
        """Test v2 conversion with unknown days value."""
        payload = {"password": {"payload": "secret", "expire_after_days": 99}}
        result = adapt_text_payload_for_profile(payload, API_PROFILE_V2)
        assert result["push"]["expire_after_days"] == 99
        assert "expire_after_duration" not in result["push"]


class TestAdaptFilePayloadForProfile:
    """Tests for adapt_file_payload_for_profile function."""

    def test_legacy_file_payload_unchanged(self):
        """Test that legacy file payload is returned unchanged."""
        payload = {"file_push": {"payload": "", "kind": "file"}}
        result = adapt_file_payload_for_profile(payload, API_PROFILE_LEGACY)
        assert result == payload

    def test_v2_file_conversion(self):
        """Test v2 file payload conversion."""
        payload = {
            "file_push": {
                "payload": "",
                "kind": "file",
                "expire_after_views": 3,
                "expire_after_days": 1,
            }
        }
        result = adapt_file_payload_for_profile(payload, API_PROFILE_V2)
        assert result["push"]["kind"] == "file"
        assert result["push"]["expire_after_views"] == 3
        assert result["push"]["expire_after_duration"] == 6  # 1 day maps to 6


class TestAdaptFileUploadsForProfile:
    """Tests for adapt_file_uploads_for_profile function."""

    def test_legacy_uploads_unchanged(self):
        """Test that legacy uploads are returned unchanged."""
        uploads = {"file_push[files][]": "file-data"}
        result = adapt_file_uploads_for_profile(uploads, API_PROFILE_LEGACY)
        assert result == uploads

    def test_v2_uploads_renamed(self):
        """Test that v2 uploads are renamed."""
        uploads = {"file_push[files][]": "file-data"}
        result = adapt_file_uploads_for_profile(uploads, API_PROFILE_V2)
        assert result == {"push[files][]": "file-data"}

    def test_v2_unknown_key_unchanged(self):
        """Test unknown keys are unchanged in v2."""
        uploads = {"unknown_key": "file-data"}
        result = adapt_file_uploads_for_profile(uploads, API_PROFILE_V2)
        assert result == uploads


class TestNormalizeAuditEvents:
    """Tests for normalize_audit_events function."""

    def test_legacy_format_with_views(self):
        """Test normalization of legacy format with 'views' key."""
        body = {
            "views": [
                {
                    "ip": "192.168.1.1",
                    "user_agent": "Mozilla/5.0",
                    "referrer": "https://example.com",
                    "successful": True,
                    "created_at": "2024-01-15T10:30:00Z",
                    "kind": 0,
                },
                {
                    "ip": "192.168.1.2",
                    "user_agent": "Mozilla/5.0",
                    "referrer": None,
                    "successful": False,
                    "created_at": "2024-01-15T11:00:00Z",
                    "kind": 1,
                },
            ]
        }
        result = normalize_audit_events(body)
        assert len(result) == 2
        assert result[0]["kind"] == "View"
        assert result[0]["referrer"] == "https://example.com"
        assert result[1]["kind"] == "Manual Deletion"
        assert result[1]["referrer"] == "None"

    def test_v2_format_with_logs(self):
        """Test normalization of v2 format with 'logs' key."""
        body = {
            "logs": [
                {
                    "ip": "192.168.1.1",
                    "user_agent": "Mozilla/5.0",
                    "referrer": "https://example.com",
                    "created_at": "2024-01-15T10:30:00Z",
                    "kind": "password_viewed",
                }
            ]
        }
        result = normalize_audit_events(body)
        assert len(result) == 1
        assert result[0]["kind"] == "Password Viewed"
        assert result[0]["successful"] == "True"

    def test_unknown_kind_in_legacy(self):
        """Test unknown kind value in legacy format."""
        body = {
            "views": [
                {
                    "ip": "192.168.1.1",
                    "user_agent": "Mozilla/5.0",
                    "referrer": None,
                    "successful": True,
                    "created_at": "2024-01-15T10:30:00Z",
                    "kind": 99,
                }
            ]
        }
        result = normalize_audit_events(body)
        assert result[0]["kind"] == "99"

    def test_empty_body(self):
        """Test empty body."""
        result = normalize_audit_events({})
        assert result == []
