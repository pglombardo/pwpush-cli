from dataclasses import dataclass
from urllib.parse import urlparse

import typer
from rich.console import Console
from rich.table import Table

from pwpush.api.client import normalize_base_url
from pwpush.options import save_config, user_config, user_config_file
from pwpush.utils import parse_boolean

NOT_SET = "Not Set"


@dataclass(frozen=True)
class InstanceChoice:
    """A Password Pusher instance offered by the setup wizard."""

    label: str
    url: str
    description: str


@dataclass(frozen=True)
class WizardSettings:
    """Settings collected by the setup wizard."""

    url: str
    email: str
    token: str
    expire_after_days: str
    expire_after_views: str
    retrieval_step: str
    deletable_by_viewer: str
    json: str
    verbose: str
    pretty: str
    debug: str


HOSTED_INSTANCE_CHOICES: tuple[InstanceChoice, ...] = (
    InstanceChoice(
        label="EU hosted",
        url="https://eu.pwpush.com",
        description="Pro features; EU Data Residency",
    ),
    InstanceChoice(
        label="US hosted",
        url="https://us.pwpush.com",
        description="Pro features; US Data Residency",
    ),
    InstanceChoice(
        label="OSS hosted",
        url="https://oss.pwpush.com",
        description="OSS; EU Data Residency; No File Uploads",
    ),
)

console = Console()


def normalize_instance_url(url: str) -> str:
    """Normalize a custom instance URL, defaulting to HTTPS for bare domains."""
    candidate = url.strip()
    if not candidate:
        raise ValueError("Instance URL cannot be empty.")

    if not urlparse(candidate).scheme:
        candidate = f"https://{candidate}"

    parsed = urlparse(candidate)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Instance URL must be a valid HTTP or HTTPS URL.")

    return normalize_base_url(candidate)


def choose_instance_url() -> str:
    """Prompt for the Password Pusher instance URL."""
    existing_url = user_config["instance"]["url"]

    table = Table("Option", "Instance", "Description")
    for index, choice in enumerate(HOSTED_INSTANCE_CHOICES, start=1):
        table.add_row(str(index), choice.url, f"{choice.label}: {choice.description}")
    table.add_row("4", "Custom", "Self-hosted OSS or Pro instance")
    console.print(table)

    # Determine default selection based on existing URL (normalized for comparison)
    default_choice = "1"
    if existing_url and existing_url != NOT_SET:
        normalized_existing = normalize_base_url(existing_url)
        for index, choice in enumerate(HOSTED_INSTANCE_CHOICES, start=1):
            if choice.url == normalized_existing:
                default_choice = str(index)
                break
        # If not a hosted choice, default to Custom (4)
        if (
            default_choice == "1"
            and normalized_existing != HOSTED_INSTANCE_CHOICES[0].url
        ):
            default_choice = "4"

    while True:
        selection = typer.prompt("Choose an instance", default=default_choice).strip()
        if selection in ("1", "2", "3"):
            return HOSTED_INSTANCE_CHOICES[int(selection) - 1].url
        if selection == "4":
            return prompt_custom_instance_url(
                existing_url if existing_url != NOT_SET else None
            )
        console.print("[red]Please choose 1, 2, 3, or 4.[/red]")


def prompt_custom_instance_url(existing_url: str | None = None) -> str:
    """Prompt for a custom instance URL until a valid value is provided."""
    default_url = existing_url if existing_url else ""
    while True:
        url = typer.prompt(
            "Custom instance URL, e.g. https://pwpush.example.com",
            default=default_url,
            show_default=True if existing_url else False,
        )
        try:
            return normalize_instance_url(url)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")


def prompt_optional_int(prompt: str, *, minimum: int, maximum: int) -> str:
    """Prompt for an optional bounded integer config value."""
    return prompt_optional_int_with_default(
        prompt, existing_value="", minimum=minimum, maximum=maximum
    )


def prompt_optional_int_with_default(
    prompt: str, *, existing_value: str, minimum: int, maximum: int
) -> str:
    """Prompt for an optional bounded integer config value with an existing default."""
    while True:
        value = typer.prompt(
            prompt, default=existing_value, show_default=bool(existing_value)
        ).strip()
        if not value:
            return NOT_SET

        try:
            parsed = int(value)
        except ValueError:
            console.print(
                f"[red]Enter a number from {minimum} to {maximum}, or leave blank.[/red]"
            )
            continue

        if minimum <= parsed <= maximum:
            return str(parsed)

        console.print(
            f"[red]Enter a number from {minimum} to {maximum}, or leave blank.[/red]"
        )


def bool_config_value(prompt: str, *, default: bool = False) -> str:
    """Prompt for a required boolean config value stored as a string."""
    return str(typer.confirm(prompt, default=default))


def collect_wizard_settings() -> WizardSettings:
    """Collect all setup wizard settings without mutating global config."""
    url = choose_instance_url()

    # Get existing values for API token
    existing_token = user_config["instance"]["token"]
    has_existing_token = existing_token != NOT_SET and bool(existing_token.strip())

    email = NOT_SET
    token = existing_token if has_existing_token else NOT_SET
    if typer.confirm(
        "Do you want to add an API token?",
        default=has_existing_token,
    ):
        if has_existing_token:
            # Show masked token and allow updating
            masked = (
                existing_token[:4] + "****" + existing_token[-4:]
                if len(existing_token) > 8
                else "****"
            )
            console.print(
                f"[dim]Current token: {masked} (press Enter to keep, or type new token)[/dim]"
            )
        token_input = typer.prompt(
            "API token",
            default=existing_token if has_existing_token else "",
            show_default=False,
            hide_input=True,
        )
        if token_input.strip():
            token = token_input
        else:
            token = existing_token if has_existing_token else NOT_SET

    # Get existing expiration values
    existing_expire_days = user_config["expiration"]["expire_after_days"]
    existing_expire_views = user_config["expiration"]["expire_after_views"]
    existing_retrieval = user_config["expiration"]["retrieval_step"]
    existing_deletable = user_config["expiration"]["deletable_by_viewer"]

    has_existing_expiration = any(
        v != NOT_SET
        for v in [
            existing_expire_days,
            existing_expire_views,
            existing_retrieval,
            existing_deletable,
        ]
    )

    expire_after_days = (
        existing_expire_days if existing_expire_days != NOT_SET else NOT_SET
    )
    expire_after_views = (
        existing_expire_views if existing_expire_views != NOT_SET else NOT_SET
    )
    retrieval_step = existing_retrieval if existing_retrieval != NOT_SET else NOT_SET
    deletable_by_viewer = (
        existing_deletable if existing_deletable != NOT_SET else NOT_SET
    )

    if typer.confirm(
        "Set default expiration preferences?", default=has_existing_expiration
    ):
        days_default = existing_expire_days if existing_expire_days != NOT_SET else ""
        views_default = (
            existing_expire_views if existing_expire_views != NOT_SET else ""
        )

        expire_after_days = prompt_optional_int_with_default(
            "Default expiration days, 1-90 (blank for server default)",
            existing_value=days_default,
            minimum=1,
            maximum=90,
        )
        expire_after_views = prompt_optional_int_with_default(
            "Default expiration views, 1-100 (blank for server default)",
            existing_value=views_default,
            minimum=1,
            maximum=100,
        )
        retrieval_step = bool_config_value(
            "Enable retrieval step by default?",
            default=(
                parse_boolean(existing_retrieval)
                if existing_retrieval != NOT_SET
                else False
            ),
        )
        deletable_by_viewer = bool_config_value(
            "Allow viewers to delete pushes by default?",
            default=(
                parse_boolean(existing_deletable)
                if existing_deletable != NOT_SET
                else False
            ),
        )

    # Get existing CLI output values
    existing_json = user_config["cli"]["json"]
    existing_verbose = user_config["cli"]["verbose"]
    existing_pretty = user_config["cli"]["pretty"]
    existing_debug = user_config["cli"]["debug"]

    json = existing_json if existing_json != NOT_SET else NOT_SET
    verbose = existing_verbose if existing_verbose != NOT_SET else NOT_SET
    pretty = existing_pretty if existing_pretty != NOT_SET else NOT_SET
    debug = existing_debug if existing_debug != NOT_SET else NOT_SET

    has_existing_cli = any(
        v != NOT_SET
        for v in [existing_json, existing_verbose, existing_pretty, existing_debug]
    )

    if typer.confirm("Set CLI output preferences?", default=has_existing_cli):
        json = bool_config_value(
            "Output JSON by default?",
            default=(
                parse_boolean(existing_json) if existing_json != NOT_SET else False
            ),
        )
        verbose = bool_config_value(
            "Enable verbose output by default?",
            default=(
                parse_boolean(existing_verbose)
                if existing_verbose != NOT_SET
                else False
            ),
        )
        pretty = bool_config_value(
            "Pretty-print JSON by default?",
            default=(
                parse_boolean(existing_pretty) if existing_pretty != NOT_SET else False
            ),
        )
        debug = bool_config_value(
            "Enable debug output by default?",
            default=(
                parse_boolean(existing_debug) if existing_debug != NOT_SET else False
            ),
        )

    return WizardSettings(
        url=url,
        email=email,
        token=token,
        expire_after_days=expire_after_days,
        expire_after_views=expire_after_views,
        retrieval_step=retrieval_step,
        deletable_by_viewer=deletable_by_viewer,
        json=json,
        verbose=verbose,
        pretty=pretty,
        debug=debug,
    )


def apply_wizard_settings(settings: WizardSettings) -> None:
    """Apply collected wizard settings to the global user config."""
    previous_url = user_config["instance"]["url"]

    user_config["instance"]["url"] = settings.url
    user_config["instance"]["email"] = settings.email
    user_config["instance"]["token"] = settings.token

    if settings.url != previous_url:
        user_config["instance"]["api_profile"] = NOT_SET
        user_config["instance"]["api_profile_checked_at"] = "0"

    user_config["expiration"]["expire_after_days"] = settings.expire_after_days
    user_config["expiration"]["expire_after_views"] = settings.expire_after_views
    user_config["expiration"]["retrieval_step"] = settings.retrieval_step
    user_config["expiration"]["deletable_by_viewer"] = settings.deletable_by_viewer

    user_config["cli"]["json"] = settings.json
    user_config["cli"]["verbose"] = settings.verbose
    user_config["cli"]["pretty"] = settings.pretty
    user_config["cli"]["debug"] = settings.debug


def run_config_wizard() -> WizardSettings:
    """Run the interactive configuration wizard and persist the result."""
    console.print()
    console.print("[bold blue]Password Pusher CLI Setup[/bold blue]")
    console.print("This wizard will create your local pwpush configuration.")
    console.print()

    settings = collect_wizard_settings()
    apply_wizard_settings(settings)
    save_config()

    console.print()
    console.print(f"[green]Configuration saved to {user_config_file}[/green]")
    console.print()
    return settings
