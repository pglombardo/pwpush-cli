import json

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from pwpush.config_wizard import run_config_wizard
from pwpush.options import (
    cli_options,
    default_config,
    json_output,
    save_config,
    user_config,
    user_config_file,
)
from pwpush.utils import mask_sensitive_value, parse_boolean

app = typer.Typer(
    rich_markup_mode="markdown",
    context_settings=dict(help_option_names=["-h", "--help"]),
)
__all__ = ["app", "user_config"]

console = Console()


@app.callback(invoke_without_command=True)
def config_commands(
    ctx: typer.Context,
    json_flag: bool = typer.Option(
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
        help="Enable debug mode with detailed request/response information.",
    ),
) -> None:
    """
    Show configuration when no subcommand is provided.

    Run `pwpush config wizard` for guided setup.
    """
    # Only update global CLI options if explicitly set via subcommand
    # This preserves global options set on the parent app (e.g., pwpush --json config)
    if json_flag:
        cli_options["json"] = json_flag
    if verbose:
        cli_options["verbose"] = verbose
    if debug:
        cli_options["debug"] = debug
    if pretty:
        cli_options["pretty"] = pretty

    if ctx.invoked_subcommand is None:
        _show_config(use_json=json_flag or cli_options.get("json", False))


@app.command()
def wizard() -> None:
    """
    Run the guided setup wizard.

    This is the recommended way to choose your Password Pusher instance, add an
    API token, and set default expiration/output preferences.
    """
    run_config_wizard()
    raise typer.Exit(code=0)


@app.command()
def init() -> None:
    """
    Alias for `pwpush config wizard`.
    """
    run_config_wizard()
    raise typer.Exit(code=0)


@app.command()
def show(
    json_output_flag: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output results in JSON format instead of human-readable text.",
    ),
) -> None:
    """
    Show current configuration values.
    """
    _show_config(json_output_flag)


def _show_config(use_json: bool = False) -> None:
    """
    Internal function to show configuration values.
    """
    # Check both the provided flag and the global CLI options
    if use_json or json_output() or cli_options.get("json", False):
        # Create a copy of the config sections and mask sensitive values
        config_data = {}
        for section_name in user_config.sections():
            config_data[section_name] = dict(user_config[section_name])
            # Mask the token in the instance section
            if section_name == "instance" and "token" in config_data[section_name]:
                config_data[section_name]["token"] = mask_sensitive_value(
                    config_data[section_name]["token"]
                )
        print(json.dumps(config_data))
    else:
        rprint()
        rprint("[bold]=== Instance Settings:[/bold]")
        rprint(
            "Specify your credentials and even your private Password Pusher instance here."
        )
        rprint()
        table = Table("Key", "Value", "Description")
        table.add_row(
            "URL",
            user_config["instance"]["url"],
            "The Password Pusher instance to work with.",
        )
        table.add_row(
            "email",
            user_config["instance"]["email"],
            "E-mail address of your account on Password Pusher.",
        )
        table.add_row(
            "token",
            mask_sensitive_value(user_config["instance"]["token"]),
            "API token from your account.  e.g. 'https://pwpush.com/en/users/token'",
        )
        table.add_row(
            "api_profile",
            user_config["instance"]["api_profile"],
            "Cached API profile detected for this instance (v2/legacy).",
        )
        table.add_row(
            "api_profile_ttl_seconds",
            user_config["instance"]["api_profile_ttl_seconds"],
            "How long to trust cached API profile before probing again.",
        )
        console.print(table)

        rprint()
        rprint("[bold]=== Expiration Settings:[/bold]")
        rprint("Pushes created with this tool will have these expiration settings.")
        rprint()
        rprint("If not specified, the application defaults will be used.")
        rprint(
            "Command line options override these settings.  See 'pwpush push --help'"
        )
        rprint()
        table = Table("Key", "Value", "Valid Values", "Description")
        table.add_row(
            "expire_after_days",
            user_config["expiration"]["expire_after_days"],
            "1-90",
            "Number of days each push will be valid for.",
        )
        table.add_row(
            "expire_after_views",
            user_config["expiration"]["expire_after_views"],
            "1-100",
            "Number of views each push will be valid for.",
        )
        table.add_row(
            "retrieval_step",
            user_config["expiration"]["retrieval_step"],
            "true/false",
            "Require users to perform a click through to retrieve a push.",
        )
        table.add_row(
            "deletable_by_viewer",
            user_config["expiration"]["deletable_by_viewer"],
            "true/false",
            "Enables/disables a user from deleting a push payload themselves.",
        )
        console.print(table)

        rprint()
        rprint("[bold]=== Pro Settings:[/bold]")
        rprint(
            "Password Pusher Pro features. These require authentication and Pro instance support."
        )
        rprint()
        table = Table("Key", "Value", "Description")
        table.add_row(
            "notify",
            user_config["pro"]["notify"],
            "Comma-separated emails to notify on push access (Pro feature, requires auth)",
        )
        table.add_row(
            "notify_locale",
            user_config["pro"]["notify_locale"],
            "Locale for notification emails (e.g., en, es, fr)",
        )
        console.print(table)

        rprint()
        rprint("[bold]=== CLI Settings:[/bold]")
        rprint("Behavior settings for this CLI.")
        rprint()
        rprint("Command line options override these settings.  See 'pwpush --help'")
        rprint()
        table = Table("Key", "Value", "Valid Values", "Description")
        table.add_row(
            "json",
            user_config["cli"]["json"],
            "true/false",
            "CLI outputs results in JSON.",
        )
        table.add_row(
            "verbose",
            user_config["cli"]["verbose"],
            "true/false",
            "More verbosity when appropriate.",
        )
        console.print(table)

        rprint()
        rprint("To update these values, run 'pwpush config wizard'.")
        rprint("For direct edits, see 'pwpush config set --help'.")
        rprint()
        rprint("User config is saved in '%s/config.ini'" % typer.get_app_dir("pwpush"))
        rprint()
    raise typer.Exit()


@app.command()
def set(
    key: str | None = typer.Argument(None, help="The key to set."),
    value: str | None = typer.Argument(None, help="The value to assign."),
    key_flag: str | None = typer.Option(
        None, "--key", help="The key to set (alternative to positional argument)."
    ),
    value_flag: str | None = typer.Option(
        None,
        "--value",
        help="The value to assign (alternative to positional argument).",
    ),
) -> None:
    """
    Directly set a configuration value.

    Most users should run `pwpush config wizard` for guided setup. Use this
    command when you know the exact config key to change.
    """
    # Determine which method was used and get the values
    if key_flag is not None or value_flag is not None:
        # Using flag-based approach
        if key_flag is None or value_flag is None:
            rprint(
                "[red]Error: Both --key and --value must be provided when using flags.[/red]"
            )
            raise typer.Exit(1)
        if key is not None or value is not None:
            rprint(
                "[red]Error: Cannot mix positional arguments with --key/--value flags.[/red]"
            )
            raise typer.Exit(1)
        key = key_flag
        value = value_flag
    else:
        # Using positional arguments
        if key is None or value is None:
            rprint("[red]Error: Both key and value must be provided.[/red]")
            rprint("Usage: pwpush config set <key> <value>")
            rprint("   or: pwpush config set --key <key> --value <value>")
            raise typer.Exit(1)
    key = key.lower()

    found = False
    for section in user_config.sections():
        if key in user_config[section]:
            user_config[section][key] = str(value)
            found = True

    if not found:
        rprint("[red]That key was not found in the configuration.[/red]")
        rprint("See 'pwpush config show' for a list of valid keys.")
        raise typer.Exit(code=1)
    else:
        save_config()
        rprint("Success")
        raise typer.Exit(code=0)


@app.command()
def unset(
    key: str = typer.Option(..., help="The key to unset."),
) -> None:
    """
    Directly unset a configuration value.
    """
    found = False
    for section in user_config.sections():
        if key in user_config[section]:
            user_config[section][key] = "Not Set"
            found = True

    if not found:
        rprint("[red]That key was not found in the configuration.[/red]")
        rprint("See 'pwpush config show' for a list of valid keys.")
        raise typer.Exit(code=1)
    else:
        save_config()
        rprint("Success")
        raise typer.Exit(code=0)


@app.command()
def delete() -> None:
    """
    Delete the local configuration file after confirmation.
    """
    typer.confirm(
        f"Delete config file at '{user_config_file}'? This cannot be undone.",
        abort=True,
    )

    if user_config_file.exists():
        try:
            user_config_file.unlink()
            rprint(f"Deleted config file: {user_config_file}")
        except OSError as exc:
            rprint(f"[red]Error: Could not delete config file: {exc}[/red]")
            raise typer.Exit(code=1)
    else:
        rprint(f"No config file found at: {user_config_file}")

    # Keep current process in a valid default state even after deletion.
    user_config.clear()
    user_config.read_dict(default_config)
    raise typer.Exit(code=0)
