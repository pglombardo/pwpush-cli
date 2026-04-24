from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from pwpush.__main__ import app

runner = CliRunner()


def test_login_prefers_v2_endpoint_when_probe_succeeds() -> None:
    with (
        patch("pwpush.__main__.current_api_profile", return_value="v2"),
        patch("pwpush.__main__.make_request") as mock_request,
    ):
        success_endpoint = MagicMock()
        success_endpoint.status_code = 200
        mock_request.return_value = success_endpoint

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
        assert mock_request.call_count == 1
        assert mock_request.call_args_list[0].args[1] == "/api/v2/pushes/active"


def test_login_falls_back_to_legacy_endpoints_when_probe_fails() -> None:
    with (
        patch("pwpush.__main__.current_api_profile", return_value="legacy"),
        patch("pwpush.__main__.make_request") as mock_request,
    ):
        missing_endpoint = MagicMock()
        missing_endpoint.status_code = 404
        success_endpoint = MagicMock()
        success_endpoint.status_code = 200
        mock_request.side_effect = [missing_endpoint, success_endpoint]

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

        assert result.exit_code == 0
        assert mock_request.call_args_list[0].args[1] == "/p/active.json"
        assert mock_request.call_args_list[1].args[1] == "/api/v2/pushes/active"


def test_login_returns_error_when_all_validation_endpoints_missing() -> None:
    with (
        patch("pwpush.__main__.current_api_profile", return_value="legacy"),
        patch("pwpush.__main__.make_request") as mock_request,
    ):
        missing_endpoint = MagicMock()
        missing_endpoint.status_code = 404
        mock_request.side_effect = [
            missing_endpoint,
            missing_endpoint,
            missing_endpoint,
        ]

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
