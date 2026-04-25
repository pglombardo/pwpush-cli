"""Request commands for pwpush CLI (creating requests for others to send secrets)."""

from typing import Any

import json as json_module

import typer
from rich import print as rprint
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from pwpush.api.capabilities import (
    detect_api_capabilities,
    request_email_notifications_enabled,
    requests_enabled,
)
from pwpush.api.endpoints import (
    adapt_request_payload_for_profile,
    adapt_request_uploads_for_profile,
    request_create_path,
    request_preview_path,
)
from pwpush.commands.config import user_config
from pwpush.options import cli_options
from pwpush.utils import parse_boolean

console = Console()

HELP_TEXT = """Create a request for someone to send you a secret.

[dim]Examples:[/]
[code]
pwpush request "Send me the production password" --notify "colleague@example.com"
pwpush request --content ./instructions.txt --notify "team@example.com"
pwpush request "Send me the signed contract" --attach-file ./template.pdf --notify "vendor@example.com"
pwpush request "Need the API key" --notify "admin@example.com" --days 7 --views 5
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


def request_cmd(
    ctx: typer.Context,
    text: str = "",
    content: str | None = None,
    attach_file: str | None = None,
    notify: str | None = None,
    notify_locale: str | None = None,
    days: int | None = None,
    views: int | None = None,
    deletable: bool | None = None,
    retrieval_step: bool | None = None,
    note: str | None = None,
    name: str | None = None,
    json: bool = False,
    verbose: bool = False,
    pretty: bool = False,
    debug: bool = False,
) -> None:
    """Create a request for someone to send you a secret."""
    _update_cli_options(json=json, verbose=verbose, pretty=pretty, debug=debug)

    # Requests API always requires authentication
    _require_api_token("request")

    api_profile = _current_api_profile()

    # Check if requests API is available on this instance
    capabilities = detect_api_capabilities(
        base_url=user_config["instance"]["url"],
        email=user_config["instance"]["email"],
        token=user_config["instance"]["token"],
        debug=_debug_output(),
    )

    if not requests_enabled(capabilities):
        if _json_output():
            _error_json(
                "The Requests API is not available on this instance. "
                "This feature requires Password Pusher Pro with API version 2.0 or greater."
            )
        else:
            rprint(
                "[red]Error: The Requests API is not available on this instance.[/red]"
            )
            rprint(
                "[red]This feature requires Password Pusher Pro with API version 2.0 or greater.[/red]"
            )
        raise typer.Exit(1)

    # Validate content input: either positional text OR --content file (mutually exclusive)
    if text and content:
        _error_json(
            "Cannot specify both positional text and --content file. Choose one."
        )
        raise typer.Exit(1)

    # Determine the request payload content
    request_content = ""
    if content:
        # Read content from file
        try:
            with open(content, encoding="utf-8") as f:
                request_content = f.read()
        except FileNotFoundError:
            _error_json(f"Content file '{content}' not found.")
            raise typer.Exit(1)
        except PermissionError:
            _error_json(f"Permission denied accessing content file '{content}'.")
            raise typer.Exit(1)
        except Exception as e:
            _error_json(f"Error reading content file '{content}': {str(e)}")
            raise typer.Exit(1)
    else:
        request_content = text

    # Validate that we have some content
    if not request_content and not attach_file:
        _error_json("Request must include either text content or a file attachment.")
        raise typer.Exit(1)

    # Build the request payload
    data: dict[str, dict[str, Any]] = {"request": {}}
    data["request"]["payload"] = request_content

    # Add notification email (required for requests)
    # Check if email notifications are supported on this instance
    if notify or notify_locale:
        if request_email_notifications_enabled(capabilities):
            if notify:
                data["request"]["notify_emails_to"] = notify
            if notify_locale:
                data["request"]["notify_emails_to_locale"] = notify_locale
        else:
            if not _json_output():
                rprint(
                    "[yellow]Warning: Email notifications are not enabled on this instance. "
                    "Options ignored.[/yellow]"
                )

    # Add expiration options
    if days:
        data["request"]["expire_after_days"] = days
    elif user_config["expiration"]["expire_after_days"] != "Not Set":
        data["request"]["expire_after_days"] = user_config["expiration"][
            "expire_after_days"
        ]

    if views:
        data["request"]["expire_after_views"] = views
    elif user_config["expiration"]["expire_after_views"] != "Not Set":
        data["request"]["expire_after_views"] = user_config["expiration"][
            "expire_after_views"
        ]

    # Add other options
    if deletable is not None:
        data["request"]["deletable_by_viewer"] = deletable
    elif user_config["expiration"]["deletable_by_viewer"] != "Not Set":
        data["request"]["deletable_by_viewer"] = user_config["expiration"][
            "deletable_by_viewer"
        ]

    if retrieval_step is not None:
        data["request"]["retrieval_step"] = retrieval_step
    elif user_config["expiration"]["retrieval_step"] != "Not Set":
        data["request"]["retrieval_step"] = user_config["expiration"]["retrieval_step"]

    if note:
        data["request"]["note"] = note

    if name:
        data["request"]["name"] = name

    # Callback to show rate limit retry feedback
    def on_rate_limit_retry(attempt: int, delay: float, response: Any) -> None:
        if not _json_output():
            rprint(
                f"[yellow]Rate limit exceeded. Retrying in {delay:.1f}s (attempt {attempt}/3)...[/yellow]"
            )

    # Create the request with progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Creating request...", total=None)

        create_path = request_create_path(api_profile)
        request_data = adapt_request_payload_for_profile(data, api_profile)

        # Handle file attachment if provided
        upload_files = None
        if attach_file:
            try:
                file_handle = open(attach_file, "rb")
                upload_files = {"request[files][]": file_handle}
                request_files = adapt_request_uploads_for_profile(
                    upload_files, api_profile
                )
            except FileNotFoundError:
                _error_json(f"Attachment file '{attach_file}' not found.")
                raise typer.Exit(1)
            except PermissionError:
                _error_json(
                    f"Permission denied accessing attachment file '{attach_file}'."
                )
                raise typer.Exit(1)
            except Exception as e:
                _error_json(f"Error reading attachment file '{attach_file}': {str(e)}")
                raise typer.Exit(1)
        else:
            request_files = None

        try:
            response = _make_request(
                "POST",
                create_path,
                post_data=request_data,
                upload_files=request_files,
                on_rate_limit_retry=on_rate_limit_retry,
            )
        finally:
            # Clean up file handle if opened
            if upload_files and "request[files][]" in upload_files:
                try:
                    upload_files["request[files][]"].close()
                except Exception:
                    pass

    if response.status_code == 201:
        body = response.json()
        preview_path = request_preview_path(api_profile, body["url_token"])
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
            rprint(f"Request created successfully:\n{body['url']}")
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
