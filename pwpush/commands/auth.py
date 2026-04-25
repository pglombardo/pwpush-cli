"""Authentication commands for pwpush CLI."""

import time

import typer
from rich import print as rprint

from pwpush.api.capabilities import detect_api_profile
from pwpush.api.client import normalize_base_url
from pwpush.api.endpoints import validation_paths
from pwpush.commands.config import save_config, user_config
from pwpush.config_wizard import collect_account_selection


def _current_api_profile(
    *, base_url: str | None = None, email: str | None = None, token: str | None = None
) -> str:
    """Resolve API profile for current or provided credentials."""
    from pwpush.__main__ import current_api_profile

    return current_api_profile(base_url=base_url, email=email, token=token)


def _make_request(
    method,
    path,
    post_data=None,
    upload_files=None,
    *,
    base_url=None,
    email=None,
    token=None,
    timeout=None,
):
    """Make an API request with the given parameters."""
    from pwpush.__main__ import make_request

    return make_request(
        method,
        path,
        post_data=post_data,
        upload_files=upload_files,
        base_url=base_url,
        email=email,
        token=token,
        timeout=timeout,
    )


def login_cmd(
    url: str = typer.Option(user_config["instance"]["url"], prompt=True),
    email: str = typer.Option(user_config["instance"]["email"], prompt=True),
    token: str = typer.Option(user_config["instance"]["token"], prompt=True),
) -> None:
    """
    Login to the registered Password Pusher instance.

    Your email and API token is required for authenticated operations.
    Your API token is available at https://pwpush.com/en/users/token.

    After login, you can use commands like 'list', 'audit', and 'expire'.
    """
    normalized_url = normalize_base_url(url)
    api_profile = _current_api_profile(
        base_url=normalized_url, email=email, token=token
    )
    candidate_paths = validation_paths(api_profile)
    r = None

    for path in candidate_paths:
        response = _make_request(
            "GET",
            path,
            base_url=normalized_url,
            email=email,
            token=token,
            timeout=5,
        )
        # Keep searching when an endpoint doesn't exist on this server.
        if response.status_code == 404:
            continue

        r = response
        break

    if r is None:
        rprint(
            "[red]Could not log in: no compatible authentication endpoint found.[/red]"
        )
        raise typer.Exit(1)

    if r.status_code == 200:
        user_config["instance"]["url"] = normalized_url
        user_config["instance"]["email"] = email
        user_config["instance"]["token"] = token
        user_config["instance"]["api_profile"] = api_profile
        user_config["instance"]["api_profile_checked_at"] = str(int(time.time()))

        # Check for multi-account support and select account if needed
        account_id = collect_account_selection(normalized_url, token)
        if account_id != "Not Set":
            user_config["instance"]["account_id"] = account_id

        save_config()
        rprint()
        rprint("Login successful.  Credentials saved.")
    else:
        rprint("Could not log in:")
        rprint(r)


def logout_cmd() -> None:
    """
    Log out from the registered Password Pusher instance.
    """
    rprint(
        "This will log you out from this command line tool and remove local credentials."
    )
    if confirmation := typer.prompt("Are you sure? [y/n]"):
        user_config["instance"]["email"] = "Not Set"
        user_config["instance"]["token"] = "Not Set"
        user_config["instance"]["account_id"] = "Not Set"
        save_config()
        rprint("Log out successful.")
