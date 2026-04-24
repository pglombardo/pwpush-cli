from urllib.parse import urljoin

import requests
import typer
from rich import print as rprint


def normalize_base_url(url: str) -> str:
    """Normalize an instance URL for safe path joining."""
    return url.rstrip("/")


def build_auth_headers(email: str, token: str) -> dict[str, str]:
    """Build the full set of supported auth headers."""
    valid_email = email != "Not Set"
    valid_token = token != "Not Set"
    if not (valid_email and valid_token):
        return {}

    return {
        "X-User-Email": email,
        "X-User-Token": token,
        "Authorization": f"Bearer {token}",
    }


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
    post_data: dict | None = None,
    upload_files: dict | None = None,
    timeout: int = 30,
    debug: bool = False,
):
    """Send one HTTP request to the configured instance."""
    auth_headers = build_auth_headers(email, token)
    url = absolute_url(base_url, path)

    if debug:
        rprint(f"Communicating with {normalize_base_url(base_url)} as user {email}")
        rprint(f"Making {method} request to {url} with headers {auth_headers}")
        if method == "POST":
            rprint(f"Request body: {post_data}")
            if upload_files is not None:
                rprint("Attaching a file to the upload")

    try:
        if method == "GET":
            return requests.get(url, headers=auth_headers, timeout=timeout)
        if method == "POST":
            return requests.post(
                url,
                headers=auth_headers,
                json=post_data,
                timeout=timeout,
                files=upload_files,
            )
        if method == "DELETE":
            return requests.delete(url, headers=auth_headers, timeout=timeout)
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
