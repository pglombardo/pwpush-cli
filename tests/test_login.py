from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from pwpush.__main__ import app

runner = CliRunner()


def test_login_uses_modern_endpoint_before_legacy() -> None:
    with patch("pwpush.__main__.requests.get") as mock_get:
        missing_endpoint = MagicMock()
        missing_endpoint.status_code = 404
        success_endpoint = MagicMock()
        success_endpoint.status_code = 200
        mock_get.side_effect = [missing_endpoint, success_endpoint]

        result = runner.invoke(
            app,
            [
                "login",
                "--url",
                "https://example.test/",
                "--email",
                "user@example.test",
                "--token",
                "test-token",
            ],
        )

        assert result.exit_code == 0
        assert "Credentials saved" in result.stdout
        assert mock_get.call_count == 2
        assert "/p/active.json" in mock_get.call_args_list[0].args[0]
        assert "/api/v2/pushes/active" in mock_get.call_args_list[1].args[0]


def test_login_returns_error_when_all_validation_endpoints_missing() -> None:
    with patch("pwpush.__main__.requests.get") as mock_get:
        missing_endpoint = MagicMock()
        missing_endpoint.status_code = 404
        mock_get.side_effect = [missing_endpoint, missing_endpoint, missing_endpoint]

        result = runner.invoke(
            app,
            [
                "login",
                "--url",
                "https://example.test",
                "--email",
                "user@example.test",
                "--token",
                "test-token",
            ],
        )

        assert result.exit_code == 1
        assert "no compatible authentication endpoint found" in result.stdout
