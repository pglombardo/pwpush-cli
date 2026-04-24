from unittest.mock import MagicMock, patch

from pwpush.api.capabilities import (
    API_PROFILE_LEGACY,
    API_PROFILE_V2,
    clear_profile_cache,
    detect_api_profile,
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
