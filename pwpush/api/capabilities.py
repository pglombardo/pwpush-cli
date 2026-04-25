from typing import Any

import requests
from rich import print as rprint

from pwpush.api.client import absolute_url

API_PROFILE_V2 = "v2"
API_PROFILE_LEGACY = "legacy"

_profile_cache: dict[str, str] = {}
_capabilities_cache: dict[str, dict[str, Any]] = {}


def clear_profile_cache() -> None:
    """Clear profile cache (mainly for tests)."""
    _profile_cache.clear()


def clear_capabilities_cache() -> None:
    """Clear capabilities cache (mainly for tests)."""
    _capabilities_cache.clear()


def detect_api_profile(
    *,
    base_url: str,
    email: str,
    token: str,
    debug: bool = False,
    force_refresh: bool = False,
) -> str:
    """Detect whether API v2 is supported by probing /api/v2/version."""
    cache_key = base_url.rstrip("/")
    if not force_refresh and cache_key in _profile_cache:
        return _profile_cache[cache_key]

    probe_url = absolute_url(base_url, "/api/v2/version")
    headers: dict[str, str] = {}
    if token.strip() and token != "Not Set":
        headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(probe_url, headers=headers, timeout=5)
        _profile_cache[cache_key] = (
            API_PROFILE_V2 if response.status_code == 200 else API_PROFILE_LEGACY
        )
    except requests.exceptions.RequestException:
        _profile_cache[cache_key] = API_PROFILE_LEGACY

    return _profile_cache[cache_key]


def detect_api_capabilities(
    *,
    base_url: str,
    email: str,
    token: str,
    debug: bool = False,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Detect API version and feature flags from /api/v2/version endpoint.

    Returns a dict with:
    - api_version: str | None (e.g., "2.1.0")
    - features: dict[str, bool] (feature flags from the features section)

    The result is cached per base_url to avoid repeated API calls.
    """
    cache_key = base_url.rstrip("/")
    if not force_refresh and cache_key in _capabilities_cache:
        return _capabilities_cache[cache_key]

    probe_url = absolute_url(base_url, "/api/v2/version")
    headers: dict[str, str] = {}
    if token.strip() and token != "Not Set":
        headers = {"Authorization": f"Bearer {token}"}

    result: dict[str, Any] = {"api_version": None, "features": {}}

    try:
        response = requests.get(probe_url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            result["api_version"] = data.get("version")
            result["features"] = data.get("features", {})
            if debug:
                rprint(f"[dim][debug] API capabilities detected: {result}[/dim]")
        elif debug:
            rprint(
                f"[dim][debug] API capabilities check failed: {response.status_code}[/dim]"
            )
    except requests.exceptions.RequestException as e:
        if debug:
            rprint(f"[dim][debug] API capabilities check error: {e}[/dim]")

    _capabilities_cache[cache_key] = result
    return result


def email_notifications_enabled(capabilities: dict[str, Any] | None = None) -> bool:
    """Check if email notifications are supported for pushes.

    Returns True only when:
    - API version >= 2.1
    - features.email_auto_dispatch == true

    Args:
        capabilities: Dict returned by detect_api_capabilities()

    Returns:
        bool: True if email notifications are enabled on this instance
    """
    if not capabilities:
        return False

    version = capabilities.get("api_version")
    if not version:
        return False

    # Parse version string - handle cases like "2.1.0" or "2.1"
    try:
        version_parts = version.split(".")
        major = int(version_parts[0]) if len(version_parts) > 0 else 0
        minor = int(version_parts[1]) if len(version_parts) > 1 else 0

        if major < 2 or (major == 2 and minor < 1):
            return False
    except (ValueError, IndexError):
        return False

    features = capabilities.get("features", {})
    return bool(features.get("email_auto_dispatch", False))
