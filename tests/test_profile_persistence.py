import time
from unittest.mock import patch

from pwpush.__main__ import current_api_profile
from pwpush.options import user_config


def _instance_backup() -> dict[str, str]:
    return {
        "url": user_config["instance"]["url"],
        "email": user_config["instance"]["email"],
        "token": user_config["instance"]["token"],
        "api_profile": user_config["instance"]["api_profile"],
        "api_profile_checked_at": user_config["instance"]["api_profile_checked_at"],
        "api_profile_ttl_seconds": user_config["instance"]["api_profile_ttl_seconds"],
    }


def _restore_instance(values: dict[str, str]) -> None:
    for key, value in values.items():
        user_config["instance"][key] = value


def test_current_api_profile_uses_persisted_profile_within_ttl() -> None:
    backup = _instance_backup()
    try:
        user_config["instance"]["url"] = "https://example.test"
        user_config["instance"]["api_profile"] = "v2"
        user_config["instance"]["api_profile_checked_at"] = str(int(time.time()))
        user_config["instance"]["api_profile_ttl_seconds"] = "3600"

        with patch("pwpush.__main__.detect_api_profile") as detect_mock:
            profile = current_api_profile()
            assert profile == "v2"
            detect_mock.assert_not_called()
    finally:
        _restore_instance(backup)


def test_current_api_profile_refreshes_expired_persisted_profile() -> None:
    backup = _instance_backup()
    try:
        user_config["instance"]["url"] = "https://example.test"
        user_config["instance"]["api_profile"] = "legacy"
        user_config["instance"]["api_profile_checked_at"] = str(int(time.time()) - 7200)
        user_config["instance"]["api_profile_ttl_seconds"] = "60"

        with (
            patch(
                "pwpush.__main__.detect_api_profile", return_value="v2"
            ) as detect_mock,
            patch("pwpush.__main__.save_config") as save_mock,
        ):
            profile = current_api_profile()
            assert profile == "v2"
            detect_mock.assert_called_once()
            save_mock.assert_called_once()
            assert user_config["instance"]["api_profile"] == "v2"
    finally:
        _restore_instance(backup)
