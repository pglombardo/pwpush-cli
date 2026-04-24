from pwpush.api.client import build_auth_headers


def test_build_auth_headers_uses_bearer_token_without_email() -> None:
    assert build_auth_headers("Not Set", "test-token") == {
        "Authorization": "Bearer test-token"
    }


def test_build_auth_headers_includes_legacy_headers_when_email_is_set() -> None:
    assert build_auth_headers("user@example.test", "test-token") == {
        "Authorization": "Bearer test-token",
        "X-User-Email": "user@example.test",
        "X-User-Token": "test-token",
    }
