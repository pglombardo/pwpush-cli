"""Tests for API capability detection."""

from typing import Any

from unittest.mock import MagicMock, patch

from pwpush.api.capabilities import (
    API_PROFILE_LEGACY,
    API_PROFILE_V2,
    clear_capabilities_cache,
    clear_profile_cache,
    detect_api_capabilities,
    detect_api_profile,
    requests_enabled,
)


def test_detect_api_profile_prefers_v2_when_version_endpoint_exists() -> None:
    clear_profile_cache()
    with patch("pwpush.api.capabilities.requests.get") as mock_get:
        response = MagicMock()
        response.status_code = 200
        mock_get.return_value = response

        profile = detect_api_profile(
            base_url="https://example.test",
            email="Not Set",
            token="Not Set",
        )

        assert profile == API_PROFILE_V2


def test_detect_api_profile_falls_back_to_legacy_when_version_missing() -> None:
    clear_profile_cache()
    with patch("pwpush.api.capabilities.requests.get") as mock_get:
        response = MagicMock()
        response.status_code = 404
        mock_get.return_value = response

        profile = detect_api_profile(
            base_url="https://example.test",
            email="Not Set",
            token="Not Set",
        )

        assert profile == API_PROFILE_LEGACY


def test_detect_api_profile_caches_results_per_base_url() -> None:
    clear_profile_cache()
    with patch("pwpush.api.capabilities.requests.get") as mock_get:
        response = MagicMock()
        response.status_code = 200
        mock_get.return_value = response

        first = detect_api_profile(
            base_url="https://example.test",
            email="Not Set",
            token="Not Set",
        )
        second = detect_api_profile(
            base_url="https://example.test",
            email="Not Set",
            token="Not Set",
        )

        assert first == API_PROFILE_V2
        assert second == API_PROFILE_V2
        assert mock_get.call_count == 1


def test_detect_api_profile_uses_bearer_token_without_email() -> None:
    clear_profile_cache()
    with patch("pwpush.api.capabilities.requests.get") as mock_get:
        response = MagicMock()
        response.status_code = 200
        mock_get.return_value = response

        profile = detect_api_profile(
            base_url="https://example.test",
            email="Not Set",
            token="test-token",
        )

        assert profile == API_PROFILE_V2
        assert mock_get.call_args.kwargs["headers"] == {
            "Authorization": "Bearer test-token"
        }


# Tests for requests_enabled function


def test_requests_enabled_with_api_2_1_and_feature_true() -> None:
    """Test requests_enabled returns True for API 2.1 with commercial and requests enabled."""
    capabilities: dict[str, Any] = {
        "api_version": "2.1.0",
        "features": {"commercial": True, "requests": True},
    }
    assert requests_enabled(capabilities) is True


def test_requests_enabled_with_api_2_1_and_feature_false() -> None:
    """Test requests_enabled returns False for API 2.1 with requests disabled."""
    capabilities: dict[str, Any] = {
        "api_version": "2.1.0",
        "features": {"commercial": True, "requests": False},
    }
    assert requests_enabled(capabilities) is False


def test_requests_enabled_with_api_2_1_no_feature_flag() -> None:
    """Test requests_enabled returns False for API 2.1 without requests feature flag."""
    capabilities: dict[str, Any] = {
        "api_version": "2.1.0",
        "features": {"commercial": True},
    }
    assert requests_enabled(capabilities) is False


def test_requests_enabled_with_api_2_1_not_commercial() -> None:
    """Test requests_enabled returns False for API 2.1 without commercial edition."""
    capabilities: dict[str, Any] = {
        "api_version": "2.1.0",
        "features": {"commercial": False, "requests": True},
    }
    assert requests_enabled(capabilities) is False


def test_requests_enabled_with_api_2_0() -> None:
    """Test requests_enabled returns False for API 2.0 (cannot verify commercial edition)."""
    capabilities: dict[str, Any] = {"api_version": "2.0.0", "features": {}}
    assert requests_enabled(capabilities) is False


def test_requests_enabled_with_api_2_0_no_features() -> None:
    """Test requests_enabled returns False for API 2.0 without features (cannot verify commercial)."""
    capabilities: dict[str, Any] = {"api_version": "2.0.0"}
    assert requests_enabled(capabilities) is False


def test_requests_enabled_with_api_1_x() -> None:
    """Test requests_enabled returns False for API 1.x."""
    capabilities: dict[str, Any] = {
        "api_version": "1.0.0",
        "features": {"commercial": True, "requests": True},
    }
    assert requests_enabled(capabilities) is False


def test_requests_enabled_with_legacy_profile() -> None:
    """Test requests_enabled returns False for legacy API."""
    capabilities: dict[str, Any] = {"api_version": None, "features": {}}
    assert requests_enabled(capabilities) is False


def test_requests_enabled_with_none() -> None:
    """Test requests_enabled returns False for None."""
    assert requests_enabled(None) is False


def test_requests_enabled_with_empty_dict() -> None:
    """Test requests_enabled returns False for empty dict."""
    assert requests_enabled({}) is False


def test_requests_enabled_with_invalid_version() -> None:
    """Test requests_enabled returns False for invalid version string."""
    capabilities = {"api_version": "invalid", "features": {"requests": True}}
    assert requests_enabled(capabilities) is False


def test_requests_enabled_with_api_2_2() -> None:
    """Test requests_enabled works with API 2.2+ with commercial edition."""
    capabilities: dict[str, Any] = {
        "api_version": "2.5.0",
        "features": {"commercial": True, "requests": True},
    }
    assert requests_enabled(capabilities) is True


# Tests for detect_api_capabilities


def test_detect_api_capabilities_returns_version_and_features() -> None:
    """Test detect_api_capabilities returns version and features."""
    clear_capabilities_cache()
    with patch("pwpush.api.capabilities.requests.get") as mock_get:
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "api_version": "2.1.0",
            "features": {"requests": True, "email_auto_dispatch": False},
        }
        mock_get.return_value = response

        capabilities = detect_api_capabilities(
            base_url="https://example.test",
            email="Not Set",
            token="Not Set",
        )

        assert capabilities["api_version"] == "2.1.0"
        assert capabilities["features"]["requests"] is True
        assert capabilities["features"]["email_auto_dispatch"] is False


def test_detect_api_capabilities_caches_results() -> None:
    """Test detect_api_capabilities caches results per base_url."""
    clear_capabilities_cache()
    with patch("pwpush.api.capabilities.requests.get") as mock_get:
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"api_version": "2.1.0", "features": {}}
        mock_get.return_value = response

        first = detect_api_capabilities(
            base_url="https://example.test",
            email="Not Set",
            token="Not Set",
        )
        second = detect_api_capabilities(
            base_url="https://example.test",
            email="Not Set",
            token="Not Set",
        )

        assert first["api_version"] == "2.1.0"
        assert second["api_version"] == "2.1.0"
        assert mock_get.call_count == 1  # Should be cached


def test_detect_api_capabilities_returns_empty_on_404() -> None:
    """Test detect_api_capabilities returns empty features on 404."""
    clear_capabilities_cache()
    with patch("pwpush.api.capabilities.requests.get") as mock_get:
        response = MagicMock()
        response.status_code = 404
        mock_get.return_value = response

        capabilities = detect_api_capabilities(
            base_url="https://example.test",
            email="Not Set",
            token="Not Set",
        )

        assert capabilities["api_version"] is None
        assert capabilities["features"] == {}
