from typing import Any

from urllib.parse import urljoin

import requests
import typer
from rich import print as rprint

from pwpush import version as pwpush_version

USER_AGENT = f"pwpush-cli/{pwpush_version}"


def _sanitize_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return a copy of headers with sensitive authentication values masked."""
    sanitized = headers.copy()
    sensitive_keys = ["Authorization", "X-User-Token"]
    for key in sensitive_keys:
        if key in sanitized:
            sanitized[key] = "***REDACTED***"
    return sanitized


def normalize_base_url(url: str) -> str:
    """Normalize an instance URL for safe path joining."""
    return url.rstrip("/")


def build_auth_headers(email: str, token: str) -> dict[str, str]:
    """Build the full set of supported auth headers."""
    valid_email = bool(email.strip()) and email != "Not Set"
    valid_token = bool(token.strip()) and token != "Not Set"
    if not valid_token:
        return {}

    headers = {"Authorization": f"Bearer {token}"}
    if valid_email:
        headers["X-User-Email"] = email
        headers["X-User-Token"] = token

    return headers


def absolute_url(base_url: str, path: str) -> str:
    """Join base URL + API path safely."""
    return urljoin(normalize_base_url(base_url) + "/", path.lstrip("/"))


def send_request(
    method: str,
    *,
    base_url: str,
    path: str,
    email: str,
    token: str,
    post_data: dict[str, Any] | None = None,
    upload_files: dict[str, Any] | None = None,
    timeout: int = 30,
    debug: bool = False,
) -> requests.Response:
    """Send one HTTP request to the configured instance."""
    auth_headers = build_auth_headers(email, token)
    headers = {**auth_headers, "User-Agent": USER_AGENT}
    url = absolute_url(base_url, path)

    if debug:
        safe_headers = _sanitize_headers(headers)
        rprint(f"Communicating with {normalize_base_url(base_url)} as user {email}")
        rprint(f"Making {method} request to {url} with headers {safe_headers}")
        if method == "POST":
            rprint(f"Request body: {post_data}")
            if upload_files is not None:
                rprint("Attaching a file to the upload")

    try:
        if method == "GET":
            return requests.get(url, headers=headers, timeout=timeout)
        if method == "POST":
            return requests.post(
                url,
                headers=headers,
                json=post_data,
                timeout=timeout,
                files=upload_files,
            )
        if method == "DELETE":
            return requests.delete(url, headers=headers, timeout=timeout)
    except requests.exceptions.Timeout:
        rprint(
            "[red]Error: Request timed out. Please check your connection and try again.[/red]"
        )
        raise typer.Exit(1)
    except requests.exceptions.ConnectionError:
        rprint(
            f"[red]Error: Could not connect to {normalize_base_url(base_url)}. Please check the URL and your connection.[/red]"
        )
        raise typer.Exit(1)
    except requests.exceptions.RequestException as e:
        rprint(f"[red]Error: Network request failed: {str(e)}[/red]")
        raise typer.Exit(1)

    rprint(f"[red]Error: Unsupported HTTP method '{method}'.[/red]")
    raise typer.Exit(1)
