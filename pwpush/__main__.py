# mypy: disable-error-code="attr-defined"
from typing import Any

import json
import time
from enum import Enum

import typer
from rich import print as rprint
from rich.console import Console

from pwpush import version
from pwpush.api.capabilities import detect_api_profile
from pwpush.api.client import normalize_base_url, send_request
from pwpush.commands import config
from pwpush.commands.auth import login_cmd, logout_cmd
from pwpush.commands.config import save_config, user_config
from pwpush.commands.manage import audit_cmd, expire_cmd, list_cmd
from pwpush.commands.push import HELP_TEXT as PUSH_HELP_TEXT
from pwpush.commands.push import push_cmd, push_file_cmd
from pwpush.options import cli_options, config_file_exists
from pwpush.utils import parse_boolean


class Color(str, Enum):
    white = "white"
    red = "red"
    cyan = "cyan"
    magenta = "magenta"
    yellow = "yellow"
    green = "green"


app = typer.Typer(
    name="pwpush",
    help="Command Line Interface to Password Pusher - securely share passwords, secrets, and files with expiration controls.",
    add_completion=False,
    rich_markup_mode="rich",
    pretty_exceptions_show_locals=False,
    context_settings=dict(help_option_names=["-h", "--help"]),
)
console = Console()


def show_welcome_screen() -> None:
    """Display a helpful welcome screen with basic usage information."""
    console.print()
    console.print("[bold blue]🔐 Password Pusher CLI[/bold blue]")
    console.print(f"[dim]Version {version}[/dim]")
    console.print(f"[dim]Server: {user_config['instance']['url']}[/dim]")
    console.print(
        "[dim]Setup or change defaults: " "[cyan]pwpush config wizard[/cyan][/dim]"
    )
    console.print()
    console.print("[bold]Quick Start:[/bold]")
    console.print("  [cyan]pwpush config wizard[/cyan]           # Guided setup")
    console.print(
        "  [cyan]pwpush push[/cyan]                    # Push a password (interactive)"
    )
    console.print(
        "  [cyan]pwpush push --auto[/cyan]             # Auto-generate password"
    )
    console.print("  [cyan]pwpush push-file document.pdf[/cyan]  # Upload a file")
    console.print(
        "  [cyan]pwpush login[/cyan]                   # Login for advanced features"
    )
    console.print()
    console.print("[bold]Need Help?[/bold]")
    console.print("  [cyan]pwpush --help[/cyan]                  # Show all commands")
    console.print(
        "  [cyan]pwpush push --help[/cyan]             # Help for specific command"
    )
    console.print()
    console.print(
        "[dim]Secure information distribution with automatic expiration controls.[/dim]"
    )
    console.print()
    console.print("[bold]About:[/bold]")
    console.print("  [dim]Built by Apnotic[/dim]")
    console.print("  [dim]Homepage: [cyan]https://apnotic.com[/cyan][/dim]")
    console.print("  [dim]Password Pusher Pro: [cyan]https://pwpush.com[/cyan][/dim]")
    console.print()


def show_help_with_config() -> None:
    """Display help with configuration information."""
    console.print()
    console.print("[bold blue]🔐 Password Pusher CLI[/bold blue]")
    console.print(f"[dim]Version {version}[/dim]")
    console.print()
    console.print(
        "Command Line Interface to Password Pusher - securely share passwords, secrets, and files with expiration controls."
    )
    console.print()
    console.print("[bold]Getting Started:[/bold]")
    console.print(
        "  [cyan]pwpush config wizard[/cyan]           # Guided setup for instance, token, defaults"
    )
    console.print(
        "  [cyan]pwpush push[/cyan]                    # Push a password or secret interactively"
    )
    console.print(
        "  [cyan]pwpush push --auto[/cyan]             # Generate and push a secure password"
    )
    console.print("  [cyan]pwpush push-file document.pdf[/cyan]  # Upload a file")
    console.print()
    console.print("[bold]Configuration:[/bold]")
    console.print(
        "  [cyan]pwpush config wizard[/cyan]                  # Recommended: guided setup/update"
    )
    console.print(
        "  [cyan]pwpush config[/cyan]                         # View current configuration"
    )
    console.print(
        "  [cyan]pwpush login[/cyan]                          # Add account credentials/API token"
    )
    console.print(
        "  [cyan]pwpush config set <key> <value>[/cyan]        # Advanced: direct config edit"
    )
    console.print(
        "  [cyan]pwpush config delete[/cyan]                  # Delete local config (with confirmation)"
    )
    console.print()
    console.print("[bold]Available Commands:[/bold]")
    console.print(
        "  [cyan]login[/cyan]       Login to the registered Password Pusher instance"
    )
    console.print(
        "  [cyan]logout[/cyan]      Log out from the registered Password Pusher instance"
    )
    console.print("  [cyan]push[/cyan]        Push a new password, secret note or text")
    console.print("  [cyan]push-file[/cyan]   Push a new file")
    console.print("  [cyan]expire[/cyan]      Expire a push")
    console.print("  [cyan]audit[/cyan]       Show the audit log for the given push")
    console.print("  [cyan]list[/cyan]        List active pushes (if logged in)")
    console.print(
        "  [cyan]config[/cyan]      Setup, show, and modify CLI configuration"
    )
    console.print()
    console.print("[bold]Global Options:[/bold]")
    console.print("  [cyan]--json, -j[/cyan]     Output results in JSON format")
    console.print("  [cyan]--verbose, -v[/cyan]  Enable verbose output")
    console.print("  [cyan]--pretty, -p[/cyan]   Format JSON output with indentation")
    console.print("  [cyan]--debug, -d[/cyan]    Enable debug mode")
    console.print("  [cyan]--help, -h[/cyan]     Show this help message")
    console.print()
    console.print("[bold]Need More Help?[/bold]")
    console.print("  [cyan]pwpush <command> --help[/cyan]  # Help for specific command")
    console.print(
        "  [cyan]pwpush config --help[/cyan]     # Configuration wizard and direct edits"
    )
    console.print()


def current_api_profile(
    *, base_url: str | None = None, email: str | None = None, token: str | None = None
) -> str:
    """Resolve API profile for current or provided credentials."""
    from pwpush.api.client import normalize_base_url

    resolved_base_url = normalize_base_url(base_url or user_config["instance"]["url"])
    resolved_email = email or user_config["instance"]["email"]
    resolved_token = token or user_config["instance"]["token"]

    instance_settings = user_config["instance"]
    configured_base_url = normalize_base_url(instance_settings["url"])
    persisted_profile = instance_settings.get("api_profile", "Not Set")

    try:
        persisted_checked_at = int(instance_settings.get("api_profile_checked_at", "0"))
    except ValueError:
        persisted_checked_at = 0

    try:
        ttl_seconds = int(instance_settings.get("api_profile_ttl_seconds", "3600"))
    except ValueError:
        ttl_seconds = 3600
    ttl_seconds = max(ttl_seconds, 0)

    now = int(time.time())
    within_ttl = (now - persisted_checked_at) < ttl_seconds
    can_use_persisted = (
        resolved_base_url == configured_base_url
        and persisted_profile in ("v2", "legacy")
        and persisted_checked_at > 0
        and within_ttl
    )

    if can_use_persisted:
        return persisted_profile

    detected_profile = detect_api_profile(
        base_url=resolved_base_url,
        email=resolved_email,
        token=resolved_token,
        debug=debug_output(),
    )

    if resolved_base_url == configured_base_url:
        instance_settings["api_profile"] = detected_profile
        instance_settings["api_profile_checked_at"] = str(now)
        save_config()

    return detected_profile


def require_api_token(operation: str) -> None:
    """Require a configured API token before authenticated operations."""
    token = user_config["instance"]["token"].strip()
    if not token or token == "Not Set":
        if json_output():
            print(
                json.dumps(
                    {
                        "error": f"'{operation}' requires an API token. "
                        "Run 'pwpush login' or set one with 'pwpush config set token <token>'."
                    }
                )
            )
        else:
            rprint(
                f"[red]Error: '{operation}' requires an API token. "
                "Run 'pwpush login' or set one with 'pwpush config set token <token>'.[/red]"
            )
        raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def load_cli_options(
    ctx: typer.Context,
    json: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output results in JSON format instead of human-readable text.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output with additional details and progress information.",
    ),
    pretty: bool = typer.Option(
        False,
        "--pretty",
        "-p",
        help="Format JSON output with proper indentation and line breaks.",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug mode with detailed request/response logging.",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version information and exit.",
        callback=lambda v: version_callback(v) if v else None,
        is_eager=True,
    ),
) -> None:
    """Password Pusher CLI - securely share passwords, secrets, and files.

    This tool allows you to push passwords, secrets, and files to Password Pusher
    instances with automatic expiration controls. All pushes expire after a set
    number of days or views, ensuring your sensitive data doesn't linger.
    """
    # Only show welcome screen when no subcommand is invoked
    if ctx.invoked_subcommand is None:
        if config_file_exists():
            # Check if login is configured (email and token are set)
            email_set = (
                user_config["instance"]["email"] != "Not Set"
                and user_config["instance"]["email"].strip() != ""
            )
            token_set = (
                user_config["instance"]["token"] != "Not Set"
                and user_config["instance"]["token"].strip() != ""
            )

            if email_set and token_set:
                show_help_with_config()
            else:
                show_welcome_screen()
        else:
            show_welcome_screen()

    cli_options["json"] = json
    cli_options["verbose"] = verbose
    cli_options["pretty"] = pretty
    cli_options["debug"] = debug


def version_callback(print_version: bool) -> None:
    """Print the version of the package."""
    if print_version:
        console.print(f"[yellow]pwpush[/] version: [bold blue]{version}[/]")
        raise typer.Exit()


def update_cli_options(
    json: bool = False,
    verbose: bool = False,
    pretty: bool = False,
    debug: bool = False,
) -> None:
    """Update global CLI options from command arguments."""
    if json:
        cli_options["json"] = json
    if verbose:
        cli_options["verbose"] = verbose
    if debug:
        cli_options["debug"] = debug
    if pretty:
        cli_options["pretty"] = pretty


def error_json(message: str, status_code: int | None = None) -> None:
    """Print error message in JSON format if --json is set, otherwise use rprint."""
    if json_output():
        error_obj: dict[str, Any] = {"error": message}
        if status_code is not None:
            error_obj["status_code"] = status_code
        # Respect --pretty flag for JSON error output
        dumps_kwargs: dict[str, Any] = {}
        if pretty_output():
            dumps_kwargs["indent"] = 2
            dumps_kwargs["sort_keys"] = True
        print(json.dumps(error_obj, **dumps_kwargs))
    else:
        if status_code is not None:
            rprint(f"[red]Error {status_code}: {message}[/red]")
        else:
            rprint(f"[red]Error: {message}[/red]")


def make_request(
    method,
    path,
    post_data=None,
    upload_files=None,
    *,
    base_url=None,
    email=None,
    token=None,
    timeout=None,
    on_rate_limit_retry=None,
):
    request_timeout = (
        timeout if timeout is not None else (5 if method == "DELETE" else 30)
    )
    # Add account_id to POST data if configured and present
    resolved_post_data = post_data
    account_id = user_config["instance"].get("account_id", "Not Set")
    if (
        method == "POST"
        and post_data is not None
        and account_id
        and account_id != "Not Set"
    ):
        resolved_post_data = {**post_data, "account_id": account_id}

    return send_request(
        method,
        base_url=base_url or user_config["instance"]["url"],
        path=path,
        email=email or user_config["instance"]["email"],
        token=token or user_config["instance"]["token"],
        post_data=resolved_post_data,
        upload_files=upload_files,
        timeout=request_timeout,
        debug=debug_output(),
        on_rate_limit_retry=on_rate_limit_retry,
    )


def json_output() -> bool:
    user_config_json = parse_boolean(user_config["cli"]["json"])
    return cli_options["json"] or user_config_json


def verbose_output() -> bool:
    user_config_verbose = parse_boolean(user_config["cli"]["verbose"])
    return cli_options["verbose"] or user_config_verbose


def debug_output() -> bool:
    user_config_debug = parse_boolean(user_config["cli"]["debug"])
    return cli_options["debug"] or user_config_debug


def pretty_output() -> bool:
    user_config_pretty = parse_boolean(user_config["cli"]["pretty"])
    return cli_options["pretty"] or user_config_pretty


# Import and re-export generate_secret and generate_passphrase for backward compatibility
# These are used by tests
from pwpush.utils import generate_passphrase, generate_secret


# Register commands from command modules
@app.command()
def login(
    url: str = typer.Option(user_config["instance"]["url"], prompt=True),
    email: str = typer.Option(user_config["instance"]["email"], prompt=True),
    token: str = typer.Option(user_config["instance"]["token"], prompt=True),
) -> None:
    """Login to the registered Password Pusher instance."""
    login_cmd(url=url, email=email, token=token)


@app.command()
def logout() -> None:
    """Log out from the registered Password Pusher instance."""
    logout_cmd()


@app.command(help=PUSH_HELP_TEXT)
def push(
    ctx: typer.Context,
    days: int | None = typer.Option(None, help="Expire after this many days."),
    views: int | None = typer.Option(None, help="Expire after this many views."),
    deletable: bool | None = typer.Option(
        None, help="Allow users to delete passwords once retrieved."
    ),
    retrieval_step: bool | None = typer.Option(
        None,
        help="1-click retrieval step: Helps to avoid chat systems and URL scanners from eating up views.",
    ),
    note: str | None = typer.Option(
        None,
        help="Reference Note. Encrypted & Visible Only to You. E.g. Employee, Record or Ticket ID etc..  Requires login.",
    ),
    auto: bool = typer.Option(False, help="Auto create password and passphrase"),
    secret: str | None = typer.Option(
        None,
        help="The secret text/password to push (will prompt if not provided)",
    ),
    passphrase: str | None = typer.Option(
        None,
        help="Optional passphrase to protect the secret",
    ),
    prompt_passphrase: bool = typer.Option(
        False,
        "--prompt-passphrase",
        help="Prompt for passphrase interactively",
    ),
    kind: str = typer.Option(
        "text",
        help="The kind of push to create. Options: text, url, qr. Default: text",
    ),
    notify: str | None = typer.Option(
        None,
        "--notify",
        help="Comma-separated email addresses to notify when this push is accessed. Requires authentication and a Pro instance with email notifications enabled.",
    ),
    notify_locale: str | None = typer.Option(
        None,
        "--notify-locale",
        help="Locale for notification emails (e.g., 'en', 'es', 'fr', 'de'). Only used when --notify is set.",
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
    """Push a new password, secret note or text."""
    push_cmd(
        ctx=ctx,
        days=days,
        views=views,
        deletable=deletable,
        retrieval_step=retrieval_step,
        note=note,
        auto=auto,
        secret=secret,
        passphrase=passphrase,
        prompt_passphrase=prompt_passphrase,
        kind=kind,
        notify=notify,
        notify_locale=notify_locale,
        json=json,
        verbose=verbose,
        pretty=pretty,
        debug=debug,
    )


@app.command(name="push-file")
def push_file(
    days: int | None = typer.Option(None, help="Expire after this many days."),
    views: int | None = typer.Option(None, help="Expire after this many views."),
    deletable: bool | None = typer.Option(
        None, help="Allow users to delete passwords once retrieved."
    ),
    retrieval_step: bool | None = typer.Option(
        None,
        help="1-click retrieval step: Helps to avoid chat systems and URL scanners from eating up views.",
    ),
    note: str | None = typer.Option(
        None,
        help="Reference Note. Encrypted & Visible Only to You. E.g. Employee, Record or Ticket ID etc..  Requires login.",
    ),
    notify: str | None = typer.Option(
        None,
        "--notify",
        help="Comma-separated email addresses to notify when this file is accessed. Requires authentication and a Pro instance with email notifications enabled.",
    ),
    notify_locale: str | None = typer.Option(
        None,
        "--notify-locale",
        help="Locale for notification emails (e.g., 'en', 'es', 'fr', 'de'). Only used when --notify is set.",
    ),
    payload: str = typer.Argument(""),
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
    """Push a new file. Requires login with an API token."""
    push_file_cmd(
        days=days,
        views=views,
        deletable=deletable,
        retrieval_step=retrieval_step,
        note=note,
        notify=notify,
        notify_locale=notify_locale,
        payload=payload,
        json=json,
        verbose=verbose,
        pretty=pretty,
        debug=debug,
    )


@app.command()
def expire(
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
    """Expire a push."""
    expire_cmd(
        ctx=ctx,
        url_token=url_token,
        json=json,
        verbose=verbose,
        pretty=pretty,
        debug=debug,
    )


@app.command()
def audit(
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
    """Show the audit log for the given push. Requires login with an API token."""
    audit_cmd(
        ctx=ctx,
        url_token=url_token,
        json=json,
        verbose=verbose,
        pretty=pretty,
        debug=debug,
    )


@app.command()
def list(
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
    """List active pushes. Requires login with an API token."""
    list_cmd(
        expired=expired,
        json=json,
        verbose=verbose,
        pretty=pretty,
        debug=debug,
    )


# Register config subcommands
app.add_typer(
    config.app,
    name="config",
    help="Setup, show, and modify CLI configuration.",
)

if __name__ == "__main__":
    app()
