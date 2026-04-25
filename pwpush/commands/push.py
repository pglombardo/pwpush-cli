"""Push commands for pwpush CLI (push and push-file)."""

from typing import Any

import getpass
import json as json_module
import sys

import typer
from rich import print as rprint
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from pwpush.api.capabilities import detect_api_capabilities, email_notifications_enabled
from pwpush.api.endpoints import (
    adapt_file_payload_for_profile,
    adapt_file_uploads_for_profile,
    adapt_text_payload_for_profile,
    push_create_path,
    push_preview_path,
)
from pwpush.commands.config import user_config
from pwpush.options import cli_options
from pwpush.utils import generate_passphrase, generate_secret, parse_boolean

console = Console()

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


def _json_output() -> bool:
    """Check if JSON output is enabled."""
    user_config_json = parse_boolean(user_config["cli"]["json"])
    return cli_options["json"] or user_config_json


def _pretty_output() -> bool:
    """Check if pretty output is enabled."""
    user_config_pretty = parse_boolean(user_config["cli"]["pretty"])
    return cli_options["pretty"] or user_config_pretty


def _debug_output() -> bool:
    """Check if debug output is enabled."""
    user_config_debug = parse_boolean(user_config["cli"]["debug"])
    return cli_options["debug"] or user_config_debug


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
    on_rate_limit_retry=None,
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
        on_rate_limit_retry=on_rate_limit_retry,
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


def push_cmd(
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
    _update_cli_options(json=json, verbose=verbose, pretty=pretty, debug=debug)

    data: dict[str, dict[str, Any]] = {"password": {}}
    api_profile = _current_api_profile()

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
        passphrase = generate_passphrase(2)
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
        pp_first: str | None = None
        pp_second: str | None = None
        # Rolling out own here as there is no easy way to prompt with a confirmation and at the same time allow it to be omitted
        while True:
            if pp_first is None:
                pp_first = getpass.getpass(
                    "Enter passphrase (If the passphrase is empty, it will be omitted): "
                )

            if pp_first in ("c", "C", ""):
                passphrase = None
                break

            if pp_second is None:
                pp_second = getpass.getpass("Confirm passphrase: ")

            if pp_first == pp_second:
                passphrase = pp_first
                break
            else:
                rprint("[red]Passphrases do not match. Please try again.[/red]")
                pp_first = None
                pp_second = None
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
            debug=_debug_output(),
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

    # Callback to show rate limit retry feedback
    def on_rate_limit_retry(attempt: int, delay: float, response: Any) -> None:
        if not _json_output():
            rprint(
                f"[yellow]Rate limit exceeded. Retrying in {delay:.1f}s (attempt {attempt}/3)...[/yellow]"
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
        response = _make_request(
            "POST",
            create_path,
            post_data=request_data,
            on_rate_limit_retry=on_rate_limit_retry,
        )

        if response.status_code == 201:
            body = response.json()
            preview_path = push_preview_path(api_profile, body["url_token"], kind)
            response = _make_request(
                "GET", preview_path, on_rate_limit_retry=on_rate_limit_retry
            )

            body = response.json()
            if _json_output():
                # Respect --pretty flag
                dumps_kwargs: dict[str, Any] = {}
                if _pretty_output():
                    dumps_kwargs["indent"] = 2
                    dumps_kwargs["sort_keys"] = True
                print(json_module.dumps(body, **dumps_kwargs))
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
            except (json_module.JSONDecodeError, ValueError):
                pass
            _error_json(error_message, response.status_code)
            raise typer.Exit(1)


def push_file_cmd(
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
    _update_cli_options(json=json, verbose=verbose, pretty=pretty, debug=debug)

    _require_api_token("push-file")
    api_profile = _current_api_profile()

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
            _error_json(
                "Email notifications require authentication. "
                "Run 'pwpush login' or set a token with 'pwpush config set token <token>'."
            )
            raise typer.Exit(1)

        # Check if email notifications are supported on this instance
        capabilities = detect_api_capabilities(
            base_url=user_config["instance"]["url"],
            email=user_config["instance"]["email"],
            token=user_config["instance"]["token"],
            debug=_debug_output(),
        )
        if email_notifications_enabled(capabilities):
            if notify:
                data["file_push"]["notify_emails_to"] = notify
            if notify_locale:
                data["file_push"]["notify_emails_to_locale"] = notify_locale
        else:
            if not _json_output():
                rprint(
                    "[yellow]Warning: Email notifications are not enabled on this instance. "
                    "Options ignored.[/yellow]"
                )

    # Callback to show rate limit retry feedback
    def on_rate_limit_retry_file(attempt: int, delay: float, response: Any) -> None:
        if not _json_output():
            rprint(
                f"[yellow]Rate limit exceeded. Retrying in {delay:.1f}s (attempt {attempt}/3)...[/yellow]"
            )

    try:
        with open(payload, "rb") as fd:
            upload_files = {"file_push[files][]": fd}
            create_path = push_create_path(api_profile, "file")
            request_data = adapt_file_payload_for_profile(data, api_profile)
            request_files = adapt_file_uploads_for_profile(upload_files, api_profile)
            response = _make_request(
                "POST",
                create_path,
                upload_files=request_files,
                post_data=request_data,
                on_rate_limit_retry=on_rate_limit_retry_file,
            )
    except FileNotFoundError:
        _error_json(f"File '{payload}' not found.")
        raise typer.Exit(1)
    except PermissionError:
        _error_json(f"Permission denied accessing file '{payload}'.")
        raise typer.Exit(1)
    except Exception as e:
        _error_json(f"Error reading file '{payload}': {str(e)}")
        raise typer.Exit(1)

    if response.status_code == 201:
        body = response.json()
        preview_path = push_preview_path(api_profile, body["url_token"], "file")
        response = _make_request(
            "GET", preview_path, on_rate_limit_retry=on_rate_limit_retry_file
        )

        body = response.json()
        if _json_output():
            # Respect --pretty flag
            dumps_kwargs: dict[str, Any] = {}
            if _pretty_output():
                dumps_kwargs["indent"] = 2
                dumps_kwargs["sort_keys"] = True
            print(json_module.dumps(body, **dumps_kwargs))
        else:
            rprint(body["url"])
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
