"""Push management commands for pwpush CLI (expire, audit, list)."""

from typing import Any

import json as json_module

import typer
from dateutil import parser
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from pwpush.api.endpoints import push_audit_path, push_expire_path, validation_paths
from pwpush.commands.config import user_config
from pwpush.options import cli_options
from pwpush.utils import parse_boolean

console = Console()


def _json_output() -> bool:
    """Check if JSON output is enabled."""
    user_config_json = parse_boolean(user_config["cli"]["json"])
    return cli_options["json"] or user_config_json


def _pretty_output() -> bool:
    """Check if pretty output is enabled."""
    user_config_pretty = parse_boolean(user_config["cli"]["pretty"])
    return cli_options["pretty"] or user_config_pretty


def _current_api_profile() -> str:
    """Get the current API profile."""
    from pwpush.__main__ import current_api_profile

    return current_api_profile()


def _require_api_token(operation: str) -> None:
    """Require a configured API token before authenticated operations."""
    from pwpush.__main__ import require_api_token

    require_api_token(operation)


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


def _update_cli_options(
    json: bool = False,
    verbose: bool = False,
    pretty: bool = False,
    debug: bool = False,
) -> None:
    """Update CLI options from command-line flags."""
    from pwpush.__main__ import update_cli_options

    update_cli_options(json=json, verbose=verbose, pretty=pretty, debug=debug)


def _error_json(message: str, status_code: int | None = None) -> None:
    """Print an error message in JSON format."""
    from pwpush.__main__ import error_json

    error_json(message, status_code)


def expire_cmd(
    ctx: typer.Context,
    url_token: str = typer.Argument(
        "", help="The secret URL token of the push to be expired."
    ),
    json: bool = typer.Option(
        False, "--json", "-j", help="Output results in JSON format."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output."
    ),
    pretty: bool = typer.Option(
        False, "--pretty", "-p", help="Pretty-print JSON output."
    ),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode."),
) -> None:
    """
    Expire a push.
    """
    _update_cli_options(json=json, verbose=verbose, pretty=pretty, debug=debug)

    if not url_token:
        typer.echo(ctx.get_help())
        raise typer.Exit()

    _require_api_token("expire")

    path = push_expire_path(_current_api_profile(), url_token)

    response = _make_request("DELETE", path)

    if response.status_code == 200:
        body = response.json()

        if _json_output():
            # Respect --pretty flag
            dumps_kwargs: dict[str, Any] = {}
            if _pretty_output():
                dumps_kwargs["indent"] = 2
                dumps_kwargs["sort_keys"] = True
            print(json_module.dumps(body, **dumps_kwargs))
    else:
        # Safely parse error response
        error_message = response.text
        try:
            error_body = response.json()
            if isinstance(error_body, dict):
                error_message = error_body.get("error", response.text)
        except (json_module.JSONDecodeError, ValueError):
            pass
        _error_json(error_message, response.status_code)
        raise typer.Exit(1)


def audit_cmd(
    ctx: typer.Context,
    url_token: str = typer.Argument(
        "", help="The secret URL token of the push to audit."
    ),
    json: bool = typer.Option(
        False, "--json", "-j", help="Output results in JSON format."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output."
    ),
    pretty: bool = typer.Option(
        False, "--pretty", "-p", help="Pretty-print JSON output."
    ),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode."),
) -> None:
    """
    Show the audit log for the given push. Requires login with an API token.
    """
    _update_cli_options(json=json, verbose=verbose, pretty=pretty, debug=debug)

    if not url_token:
        typer.echo(ctx.get_help())
        raise typer.Exit()

    _require_api_token("audit")

    if user_config["instance"]["email"] == "Not Set":
        _error_json("You must log into an instance first.")
        raise typer.Exit(1)

    path = push_audit_path(_current_api_profile(), url_token)

    response = _make_request("GET", path)

    if response.status_code == 200:
        body = response.json()

        if _json_output():
            # Respect --pretty flag
            dumps_kwargs: dict[str, Any] = {}
            if _pretty_output():
                dumps_kwargs["indent"] = 2
                dumps_kwargs["sort_keys"] = True
            print(json_module.dumps(body, **dumps_kwargs))
        else:
            from pwpush.api.endpoints import normalize_audit_events

            rprint()
            rprint(f"[bold]=== Audit Log for {url_token}:[/bold]")
            rprint()

            table = Table(
                "IP", "User Agent", "Referrer", "Successful", "When", "Operation"
            )

            for event in normalize_audit_events(body):
                table.add_row(
                    event["ip"],
                    event["user_agent"],
                    event["referrer"],
                    event["successful"],
                    event["created_at"],
                    event["kind"],
                )

            console.print(table)
    else:
        # Safely parse error response
        error_message = response.text
        try:
            error_body = response.json()
            if isinstance(error_body, dict):
                error_message = error_body.get("error", response.text)
        except (json_module.JSONDecodeError, ValueError):
            pass
        _error_json(error_message, response.status_code)
        raise typer.Exit(1)


def list_cmd(
    expired: bool = typer.Option(False, help="Show only expired pushes."),
    json: bool = typer.Option(
        False, "--json", "-j", help="Output results in JSON format."
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output."
    ),
    pretty: bool = typer.Option(
        False, "--pretty", "-p", help="Pretty-print JSON output."
    ),
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug mode."),
) -> None:
    """
    List active pushes. Requires login with an API token.
    """
    _update_cli_options(json=json, verbose=verbose, pretty=pretty, debug=debug)

    _require_api_token("list")

    if user_config["instance"]["email"] == "Not Set":
        _error_json("You must log into an instance first.")
        raise typer.Exit(1)

    paths = validation_paths(_current_api_profile(), expired=expired)
    r = None
    for path in paths:
        response = _make_request("GET", path)
        if response.status_code == 404:
            continue
        r = response
        break

    if r is None:
        _error_json("No compatible list endpoint found on this instance.")
        raise typer.Exit(1)

    if r.status_code == 200:
        pushes = r.json()
        if _json_output():
            # Respect --pretty flag
            dumps_kwargs: dict[str, Any] = {}
            if _pretty_output():
                dumps_kwargs["indent"] = 2
                dumps_kwargs["sort_keys"] = True
            print(json_module.dumps(pushes, **dumps_kwargs))
        else:
            rprint()
            if expired:
                rprint("[bold]=== Expired Pushes:[/bold]")
            else:
                rprint("[bold]=== Active Pushes:[/bold]")
            rprint()

            table = Table(
                "Secret URL Token",
                "Note",
                "Views",
                "Days",
                "Deletable by Viewer",
                "Retrieval Step",
                "Created",
            )
            for push in pushes:
                push["created_at"] = parser.isoparse(push["created_at"]).strftime(
                    "%m/%d/%Y, %H:%M:%S UTC"
                )

                table.add_row(
                    push["url_token"],
                    f'{push["note"]}',
                    f'{push["expire_after_views"] - push["views_remaining"]}/{push["expire_after_views"]}',
                    f'{push["expire_after_days"] - push["days_remaining"]}/{push["expire_after_days"]}',
                    f'{push["deletable_by_viewer"]}',
                    f'{push["retrieval_step"]}',
                    f'{push["created_at"]}',
                )

            console.print(table)
    else:
        # Safely parse error response
        error_message = r.text
        try:
            error_body = r.json()
            if isinstance(error_body, dict):
                error_message = error_body.get("error", r.text)
        except (json_module.JSONDecodeError, ValueError):
            pass
        _error_json(error_message, r.status_code)
        raise typer.Exit(1)
