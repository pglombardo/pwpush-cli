# mypy: disable-error-code="attr-defined"
from typing import Any

import getpass
import json
import secrets
import string
import sys
import time
from enum import Enum

import typer
from dateutil import parser
from rich import print as rprint
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from pwpush import version
from pwpush.api.capabilities import (
    detect_api_capabilities,
    detect_api_profile,
    email_notifications_enabled,
)
from pwpush.api.client import normalize_base_url, send_request
from pwpush.api.endpoints import (
    adapt_file_payload_for_profile,
    adapt_file_uploads_for_profile,
    adapt_text_payload_for_profile,
    normalize_audit_events,
    push_audit_path,
    push_create_path,
    push_expire_path,
    push_preview_path,
    validation_paths,
)
from pwpush.commands import config
from pwpush.commands.config import save_config, user_config
from pwpush.config_wizard import run_config_wizard
from pwpush.options import cli_options, config_file_exists
from pwpush.utils import check_secret_conditions, parse_boolean


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


def genpass(length=5):
    """Generate a passphrase"""
    from xkcdpass.xkcd_password import generate_wordlist, generate_xkcdpassword

    wordlist = generate_wordlist(
        wordfile=None, min_length=5, max_length=9, valid_chars="[a-zA-Z1-9]"
    )
    pw = generate_xkcdpassword(
        wordlist,
        interactive=False,
        numwords=length,
        acrostic=False,
        delimiter=" ",
        random_delimiters=True,
        case="random",
    )
    return pw


def generate_secret(length=50):
    """Generate a secure random password"""
    characters = string.ascii_letters + string.digits + string.punctuation
    attempts = 0
    while True:
        # print(attempts)
        secret = "".join(secrets.choice(characters) for _ in range(length))
        if check_secret_conditions(secret, length=length):
            return secret
        attempts += 1


def version_callback(print_version: bool) -> None:
    """Print the version of the package."""
    if print_version:
        console.print(f"[yellow]pwpush[/] version: [bold blue]{version}[/]")
        raise typer.Exit()


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
    json: str = typer.Option(
        False,
        "--json",
        "-j",
        help="Output results in JSON format instead of human-readable text.",
    ),
    verbose: str = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output with additional details and progress information.",
    ),
    pretty: str = typer.Option(
        False,
        "--pretty",
        "-p",
        help="Format JSON output with proper indentation and line breaks.",
    ),
    debug: str = typer.Option(
        False,
        "--debug",
        "-d",
        help="Enable debug mode with detailed request/response information.",
    ),
    help: bool = typer.Option(
        False,
        "--help",
        "-h",
        help="Show this message and exit.",
    ),
    show_version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    # CLI Args override configuration
    cli_options["json"] = parse_boolean(json)
    cli_options["verbose"] = parse_boolean(verbose)
    cli_options["debug"] = parse_boolean(debug)
    cli_options["pretty"] = parse_boolean(pretty)

    # Show welcome screen if no command was provided
    if ctx.invoked_subcommand is None:
        if help:
            show_help_with_config()
        elif not config_file_exists():
            should_run_wizard = typer.confirm(
                "No configuration file found. Run the setup wizard now?",
                default=True,
            )
            if should_run_wizard:
                run_config_wizard()
            else:
                show_welcome_screen()
        else:
            show_welcome_screen()


@app.command()
def login(
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
    api_profile = current_api_profile(base_url=normalized_url, email=email, token=token)
    candidate_paths = validation_paths(api_profile)
    r = None

    for path in candidate_paths:
        response = make_request(
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
        save_config()
        rprint()
        rprint("Login successful.  Credentials saved.")
    else:
        rprint("Could not log in:")
        rprint(r)


@app.command()
def logout() -> None:
    """
    Log out from the registered Password Pusher instance.
    """
    rprint(
        "This will log you out from this command line tool and remove local credentials."
    )
    if confirmation := typer.prompt("Are you sure? [y/n]"):
        user_config["instance"]["email"] = "Not Set"
        user_config["instance"]["token"] = "Not Set"
        save_config()
        rprint("Log out successful.")


HELP_TEXT = """Push a new password, secret note or text.

[dim]Examples:[/]
[code]
pwpush push                                      # Interactive mode
pwpush push --secret "mypassword"                # Direct secret
pwpush push --auto                               # Auto-generate password
pwpush push --secret "data" --deletable          # Allow deletion by viewer
pwpush push --secret "data" --retrieval-step     # Require click-through
pwpush push --secret "https://..." --kind url    # Push as URL
pwpush push --secret "QR data" --kind qr         # Push as QR code
pwpush push --secret "data" --passphrase "pass"  # With passphrase
pwpush push --secret "data" --prompt-passphrase  # Prompt for passphrase
pwpush push --secret "data" --notify "admin@example.com"      # Notify on access (Pro)
pwpush push --secret "data" --notify "a@b.com" --notify-locale "es"  # Spanish notifications
[/code]"""


@app.command(help=HELP_TEXT)
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
    update_cli_options(json=json, verbose=verbose, pretty=pretty, debug=debug)

    data: dict[str, dict[str, Any]] = {"password": {}}
    api_profile = current_api_profile()

    # Validate kind parameter
    valid_kinds = ["text", "url", "qr"]
    if kind not in valid_kinds:
        rprint(
            f"[red]Error: Invalid kind '{kind}'. Must be one of: {', '.join(valid_kinds)}[/red]"
        )
        raise typer.Exit(1)

    # Set the kind in the request data
    data["password"]["kind"] = kind

    # Track if input came from stdin pipe (to disable interactive prompts)
    piped_input = False

    # Priority: 1) --auto, 2) --secret CLI arg, 3) piped stdin, 4) interactive prompt
    if auto:
        secret = generate_secret(50)
        passphrase = genpass(2)
    elif secret is None:
        # Check for piped input (stdin is not a TTY)
        if not sys.stdin.isatty():
            secret = sys.stdin.read().rstrip("\n\r")
            piped_input = True
            # Validate that piped input is not empty
            if secret == "":
                rprint(
                    "[red]Error: No secret provided on stdin. Pipe a non-empty secret, "
                    "use --secret '' to intentionally send an empty secret, or use --auto.[/red]"
                )
                raise typer.Exit(1)
        else:
            secret = getpass.getpass("Enter secret: ")
            piped_input = False

    # Interactive mode: ask if user wants to add a passphrase
    # This happens when secret was prompted (not via --secret or pipe)
    # and --passphrase wasn't provided, and --prompt-passphrase wasn't used
    secret_from_cli = ctx.params.get("secret") is not None
    if (
        not secret_from_cli
        and not piped_input
        and secret is not None
        and passphrase is None
        and not prompt_passphrase
        and not auto
    ):
        add_passphrase = typer.confirm(
            "Would you like to add a passphrase to protect this secret?",
            default=False,
        )
        if add_passphrase:
            while True:
                first = getpass.getpass("Enter passphrase: ")
                if not first:
                    rprint(
                        "[yellow]Passphrase cannot be empty. Try again or press Ctrl+C to cancel.[/yellow]"
                    )
                    continue
                second = getpass.getpass("Confirm passphrase: ")
                if first == second:
                    passphrase = first
                    break
                rprint("[red]Passphrases do not match. Please try again.[/red]")

    # Handle --prompt-passphrase flag (explicit passphrase prompting)
    if prompt_passphrase:
        # User provided --prompt-passphrase flag, prompt for it
        first = None
        second = None
        # Rolling out own here as there is no easy way to prompt with a confirmation and at the same time allow it to be omitted
        while True:
            if first is None:
                first = getpass.getpass(
                    "Enter passphrase (If the passphrase it empty if will be omitted): "
                )

            if first in ("c", "C", ""):
                passphrase = None
                break

            if second is None:
                second = getpass.getpass("Confirm passphrase: ")

            if first is not None and second is not None and first == second:
                passphrase = first
                break
    # If passphrase is None (not provided), leave it as None
    # If passphrase has a value (provided with --passphrase value), use that value

    data["password"]["payload"] = secret

    # Option and user preference processing
    if days:
        data["password"]["expire_after_days"] = days
    elif user_config["expiration"]["expire_after_days"] != "Not Set":
        data["password"]["expire_after_days"] = user_config["expiration"][
            "expire_after_days"
        ]

    if note:
        data["password"]["note"] = note

    if views:
        data["password"]["expire_after_views"] = views
    elif user_config["expiration"]["expire_after_views"] != "Not Set":
        data["password"]["expire_after_views"] = user_config["expiration"][
            "expire_after_views"
        ]

    if deletable is not None:
        data["password"]["deletable_by_viewer"] = deletable
    elif user_config["expiration"]["deletable_by_viewer"] != "Not Set":
        data["password"]["deletable_by_viewer"] = user_config["expiration"][
            "deletable_by_viewer"
        ]

    if retrieval_step is not None:
        data["password"]["retrieval_step"] = retrieval_step
    elif user_config["expiration"]["retrieval_step"] != "Not Set":
        data["password"]["retrieval_step"] = user_config["expiration"]["retrieval_step"]

    if passphrase is not None:
        data["password"]["passphrase"] = passphrase

    # Email notification options require authentication
    if notify or notify_locale:
        token = user_config["instance"]["token"].strip()
        if not token or token == "Not Set":
            rprint(
                "[red]Error: Email notifications require authentication. "
                "Run 'pwpush login' or set a token with 'pwpush config set token <token>'.[/red]"
            )
            raise typer.Exit(1)

        # Check if email notifications are supported on this instance
        capabilities = detect_api_capabilities(
            base_url=user_config["instance"]["url"],
            email=user_config["instance"]["email"],
            token=user_config["instance"]["token"],
            debug=debug_output(),
        )
        if email_notifications_enabled(capabilities):
            if notify:
                data["password"]["notify_emails_to"] = notify
            if notify_locale:
                data["password"]["notify_emails_to_locale"] = notify_locale
        else:
            rprint(
                "[yellow]Warning: Email notifications are not enabled on this instance. "
                "Options ignored.[/yellow]"
            )

    # Lets add a progressbar to notify the something is happing.
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Processing...", total=None)

        create_path = push_create_path(api_profile, kind)
        request_data = adapt_text_payload_for_profile(data, api_profile)
        response = make_request("POST", create_path, post_data=request_data)

        if response.status_code == 201:
            body = response.json()
            preview_path = push_preview_path(api_profile, body["url_token"], kind)
            response = make_request("GET", preview_path)

            body = response.json()
            if json_output():
                # Respect --pretty flag
                dumps_kwargs: dict[str, Any] = {}
                if pretty_output():
                    dumps_kwargs["indent"] = 2
                    dumps_kwargs["sort_keys"] = True
                print(json.dumps(body, **dumps_kwargs))
            else:
                rprint(f"The secret has been pushed to:\n{body['url']}")

            if auto and passphrase:
                rprint(f"Passphrase is: {passphrase}")
        else:
            # Safely parse error response
            error_message = response.text
            try:
                error_body = response.json()
                if isinstance(error_body, dict):
                    error_message = error_body.get("error", response.text)
            except (json.JSONDecodeError, ValueError):
                pass
            error_json(error_message, response.status_code)
            raise typer.Exit(1)


@app.command(name="push-file")
def pushFile(
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
    payload: str = typer.Argument(
        "",
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
    Push a new file. Requires login with an API token.

    Examples:
        pwpush push-file document.pdf                    # Upload a file
        pwpush push-file data.txt --deletable           # Allow deletion by viewer
        pwpush push-file config.json --retrieval-step   # Require click-through
        pwpush push-file backup.zip --days 7 --views 5  # Custom expiration
        pwpush push-file doc.pdf --notify "admin@example.com"      # Notify on access (Pro)
    """
    update_cli_options(json=json, verbose=verbose, pretty=pretty, debug=debug)

    require_api_token("push-file")
    api_profile = current_api_profile()

    data: dict[str, dict[str, Any]] = {"file_push": {}}
    data["file_push"]["payload"] = ""
    data["file_push"]["kind"] = "file"

    # Option and user preference processing
    if days:
        data["file_push"]["expire_after_days"] = days
    elif user_config["expiration"]["expire_after_days"] != "Not Set":
        data["file_push"]["expire_after_days"] = user_config["expiration"][
            "expire_after_days"
        ]

    if views:
        data["file_push"]["expire_after_views"] = views
    elif user_config["expiration"]["expire_after_views"] != "Not Set":
        data["file_push"]["expire_after_views"] = user_config["expiration"][
            "expire_after_views"
        ]

    if deletable is not None:
        data["file_push"]["deletable_by_viewer"] = deletable
    elif user_config["expiration"]["deletable_by_viewer"] != "Not Set":
        data["file_push"]["deletable_by_viewer"] = user_config["expiration"][
            "deletable_by_viewer"
        ]

    if retrieval_step is not None:
        data["file_push"]["retrieval_step"] = retrieval_step
    elif user_config["expiration"]["retrieval_step"] != "Not Set":
        data["file_push"]["retrieval_step"] = user_config["expiration"][
            "retrieval_step"
        ]

    if note:
        data["file_push"]["note"] = note

    # Email notification options require authentication
    if notify or notify_locale:
        token = user_config["instance"]["token"].strip()
        if not token or token == "Not Set":
            error_json(
                "Email notifications require authentication. "
                "Run 'pwpush login' or set a token with 'pwpush config set token <token>'."
            )
            raise typer.Exit(1)

        # Check if email notifications are supported on this instance
        capabilities = detect_api_capabilities(
            base_url=user_config["instance"]["url"],
            email=user_config["instance"]["email"],
            token=user_config["instance"]["token"],
            debug=debug_output(),
        )
        if email_notifications_enabled(capabilities):
            if notify:
                data["file_push"]["notify_emails_to"] = notify
            if notify_locale:
                data["file_push"]["notify_emails_to_locale"] = notify_locale
        else:
            if not json_output():
                rprint(
                    "[yellow]Warning: Email notifications are not enabled on this instance. "
                    "Options ignored.[/yellow]"
                )

    try:
        with open(payload, "rb") as fd:
            upload_files = {"file_push[files][]": fd}
            create_path = push_create_path(api_profile, "file")
            request_data = adapt_file_payload_for_profile(data, api_profile)
            request_files = adapt_file_uploads_for_profile(upload_files, api_profile)
            response = make_request(
                "POST",
                create_path,
                upload_files=request_files,
                post_data=request_data,
            )
    except FileNotFoundError:
        error_json(f"File '{payload}' not found.")
        raise typer.Exit(1)
    except PermissionError:
        error_json(f"Permission denied accessing file '{payload}'.")
        raise typer.Exit(1)
    except Exception as e:
        error_json(f"Error reading file '{payload}': {str(e)}")
        raise typer.Exit(1)

    if response.status_code == 201:
        body = response.json()
        preview_path = push_preview_path(api_profile, body["url_token"], "file")
        response = make_request("GET", preview_path)

        body = response.json()
        if json_output():
            # Respect --pretty flag
            dumps_kwargs: dict[str, Any] = {}
            if pretty_output():
                dumps_kwargs["indent"] = 2
                dumps_kwargs["sort_keys"] = True
            print(json.dumps(body, **dumps_kwargs))
        else:
            rprint(body["url"])
    else:
        # Safely parse error response
        error_message = response.text
        try:
            error_body = response.json()
            if isinstance(error_body, dict):
                error_message = error_body.get("error", response.text)
        except (json.JSONDecodeError, ValueError):
            pass
        error_json(error_message, response.status_code)
        raise typer.Exit(1)


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
    """
    Expire a push.
    """
    update_cli_options(json=json, verbose=verbose, pretty=pretty, debug=debug)

    if not url_token:
        typer.echo(ctx.get_help())
        raise typer.Exit()

    require_api_token("expire")

    path = push_expire_path(current_api_profile(), url_token)

    response = make_request("DELETE", path)

    if response.status_code == 200:
        body = response.json()

        if json_output():
            # Respect --pretty flag
            dumps_kwargs: dict[str, Any] = {}
            if pretty_output():
                dumps_kwargs["indent"] = 2
                dumps_kwargs["sort_keys"] = True
            print(json.dumps(body, **dumps_kwargs))
    else:
        # Safely parse error response
        error_message = response.text
        try:
            error_body = response.json()
            if isinstance(error_body, dict):
                error_message = error_body.get("error", response.text)
        except (json.JSONDecodeError, ValueError):
            pass
        error_json(error_message, response.status_code)
        raise typer.Exit(1)


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
    """
    Show the audit log for the given push. Requires login with an API token.
    """
    update_cli_options(json=json, verbose=verbose, pretty=pretty, debug=debug)

    if not url_token:
        typer.echo(ctx.get_help())
        raise typer.Exit()

    require_api_token("audit")

    if user_config["instance"]["email"] == "Not Set":
        error_json("You must log into an instance first.")
        raise typer.Exit(1)

    path = push_audit_path(current_api_profile(), url_token)

    response = make_request("GET", path)

    if response.status_code == 200:
        body = response.json()

        if json_output():
            # Respect --pretty flag
            dumps_kwargs: dict[str, Any] = {}
            if pretty_output():
                dumps_kwargs["indent"] = 2
                dumps_kwargs["sort_keys"] = True
            print(json.dumps(body, **dumps_kwargs))
        else:
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
        except (json.JSONDecodeError, ValueError):
            pass
        error_json(error_message, response.status_code)
        raise typer.Exit(1)


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
    """
    List active pushes. Requires login with an API token.
    """
    update_cli_options(json=json, verbose=verbose, pretty=pretty, debug=debug)

    require_api_token("list")

    if user_config["instance"]["email"] == "Not Set":
        error_json("You must log into an instance first.")
        raise typer.Exit(1)

    paths = validation_paths(current_api_profile(), expired=expired)
    r = None
    for path in paths:
        response = make_request("GET", path)
        if response.status_code == 404:
            continue
        r = response
        break

    if r is None:
        error_json("No compatible list endpoint found on this instance.")
        raise typer.Exit(1)

    if r.status_code == 200:
        pushes = r.json()
        if json_output():
            # Respect --pretty flag
            dumps_kwargs: dict[str, Any] = {}
            if pretty_output():
                dumps_kwargs["indent"] = 2
                dumps_kwargs["sort_keys"] = True
            print(json.dumps(pushes, **dumps_kwargs))
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
        except (json.JSONDecodeError, ValueError):
            pass
        error_json(error_message, r.status_code)
        raise typer.Exit(1)


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
):
    request_timeout = (
        timeout if timeout is not None else (5 if method == "DELETE" else 30)
    )
    return send_request(
        method,
        base_url=base_url or user_config["instance"]["url"],
        path=path,
        email=email or user_config["instance"]["email"],
        token=token or user_config["instance"]["token"],
        post_data=post_data,
        upload_files=upload_files,
        timeout=request_timeout,
        debug=debug_output(),
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


app.add_typer(
    config.app,
    name="config",
    help="Setup, show, and modify CLI configuration.",
)

if __name__ == "__main__":
    app()
