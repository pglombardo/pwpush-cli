import requests

from pwpush.api.client import absolute_url

API_PROFILE_V2 = "v2"
API_PROFILE_LEGACY = "legacy"

_profile_cache: dict[str, str] = {}


def clear_profile_cache() -> None:
    """Clear profile cache (mainly for tests)."""
    _profile_cache.clear()


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
    if email != "Not Set" and token != "Not Set":
        headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(probe_url, headers=headers, timeout=5)
        _profile_cache[cache_key] = (
            API_PROFILE_V2 if response.status_code == 200 else API_PROFILE_LEGACY
        )
    except requests.exceptions.RequestException:
        _profile_cache[cache_key] = API_PROFILE_LEGACY

    return _profile_cache[cache_key]
