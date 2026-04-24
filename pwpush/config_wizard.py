from dataclasses import dataclass
from urllib.parse import urlparse

import typer
from rich.console import Console
from rich.table import Table

from pwpush.api.client import normalize_base_url
from pwpush.options import save_config, user_config, user_config_file

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
    table = Table("Option", "Instance", "Description")
    for index, choice in enumerate(HOSTED_INSTANCE_CHOICES, start=1):
        table.add_row(str(index), choice.url, f"{choice.label}: {choice.description}")
    table.add_row("4", "Custom", "Self-hosted OSS or Pro instance")
    console.print(table)

    while True:
        selection = typer.prompt("Choose an instance", default="1").strip()
        if selection in ("1", "2", "3"):
            return HOSTED_INSTANCE_CHOICES[int(selection) - 1].url
        if selection == "4":
            return prompt_custom_instance_url()
        console.print("[red]Please choose 1, 2, 3, or 4.[/red]")


def prompt_custom_instance_url() -> str:
    """Prompt for a custom instance URL until a valid value is provided."""
    while True:
        url = typer.prompt("Custom instance URL, e.g. https://pwpush.example.com")
        try:
            return normalize_instance_url(url)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")


def prompt_optional_int(prompt: str, *, minimum: int, maximum: int) -> str:
    """Prompt for an optional bounded integer config value."""
    while True:
        value = typer.prompt(prompt, default="", show_default=False).strip()
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

    email = NOT_SET
    token = NOT_SET
    if typer.confirm("Do you want to add an API token?", default=False):
        token = typer.prompt("API token", hide_input=True)

    expire_after_days = NOT_SET
    expire_after_views = NOT_SET
    retrieval_step = NOT_SET
    deletable_by_viewer = NOT_SET
    if typer.confirm("Set default expiration preferences?", default=False):
        expire_after_days = prompt_optional_int(
            "Default expiration days, 1-90 (blank for server default)",
            minimum=1,
            maximum=90,
        )
        expire_after_views = prompt_optional_int(
            "Default expiration views, 1-100 (blank for server default)",
            minimum=1,
            maximum=100,
        )
        retrieval_step = bool_config_value(
            "Enable retrieval step by default?",
            default=False,
        )
        deletable_by_viewer = bool_config_value(
            "Allow viewers to delete pushes by default?",
            default=False,
        )

    json = user_config["cli"]["json"]
    verbose = user_config["cli"]["verbose"]
    pretty = user_config["cli"]["pretty"]
    debug = user_config["cli"]["debug"]
    if typer.confirm("Set CLI output preferences?", default=False):
        json = bool_config_value("Output JSON by default?", default=False)
        verbose = bool_config_value("Enable verbose output by default?", default=False)
        pretty = bool_config_value("Pretty-print JSON by default?", default=False)
        debug = bool_config_value("Enable debug output by default?", default=False)

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
