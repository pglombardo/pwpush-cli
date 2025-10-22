import json

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from pwpush.options import json_output, save_config, user_config
from pwpush.utils import mask_sensitive_value

app = typer.Typer()

console = Console()


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
    Show current configuration values
    """
    # Check both the local flag and the global CLI options
    from pwpush.options import cli_options

    if json_output_flag or json_output() or cli_options.get("json", False):
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
        rprint("To change the above the values see: 'pwpush config set --help'")
        rprint()
        rprint("User config is saved in '%s/config.ini'" % typer.get_app_dir("pwpush"))
        rprint()
    raise typer.Exit()


@app.command()
def set(
    key: str = typer.Option(..., help="The key to set."),
    value: str = typer.Option(..., help="The value to assign."),
) -> None:
    """
    Set a configuration value
    """
    key = key.lower()

    found = False
    for section in user_config.sections():
        if key in user_config[section]:
            user_config[section][key] = str(value)
            found = True

    if found == False:
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
    Unset a configuration value
    """
    found = False
    for section in user_config.sections():
        if key in user_config[section]:
            user_config[section][key] = "Not Set"
            found = True

    if found == False:
        rprint("[red]That key was not found in the configuration.[/red]")
        rprint("See 'pwpush config show' for a list of valid keys.")
        raise typer.Exit(code=1)
    else:
        save_config()
        rprint("Success")
        raise typer.Exit(code=0)
