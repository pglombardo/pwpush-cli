# type: ignore[attr-defined]
from typing import Optional

import json
from enum import Enum
from pydoc import cli
from random import choice
from secrets import token_urlsafe
from xmlrpc.client import Boolean

import requests
import typer
from dateutil import parser
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from pwpush import version
from pwpush.commands import config
from pwpush.commands.config import save_config, user_config
from pwpush.options import cli_options

console = Console()


class Color(str, Enum):
    white = "white"
    red = "red"
    cyan = "cyan"
    magenta = "magenta"
    yellow = "yellow"
    green = "green"


app = typer.Typer(
    name="pwpush",
    help="Command Line Interface to Password Pusher.",
    add_completion=False,
    rich_markup_mode="markdown",
    pretty_exceptions_show_locals=False,
    context_settings=dict(help_option_names=["-h", "--help"]),
)
console = Console()


def version_callback(print_version: bool) -> None:
    """Print the version of the package."""
    if print_version:
        console.print(f"[yellow]pwpush[/] version: [bold blue]{version}[/]")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def load_cli_options(
    json: str = typer.Option(False, "--json", "-j", help="Output in JSON."),
    verbose: str = typer.Option(
        False, "--verbose", "-v", help="Verbose output where appropriate."
    ),
    pretty: str = typer.Option(
        False, "--pretty", "-p", help="Format JSON to be pretty."
    ),
    debug: str = typer.Option(False, "--debug", "-d", help="Debug mode."),
) -> None:
    # CLI Args override configuration
    cli_options["json"] = json.lower() in ["true", "yes", "on"]
    cli_options["verbose"] = verbose.lower() in ["true", "yes", "on"]
    cli_options["debug"] = debug.lower() in ["true", "yes", "on"]
    cli_options["pretty"] = pretty.lower() in ["true", "yes", "on"]


@app.command()
def login(
    url: str = typer.Option(user_config["instance"]["url"], prompt=True),
    email: str = typer.Option(user_config["instance"]["email"], prompt=True),
    token: str = typer.Option(user_config["instance"]["token"], prompt=True),
) -> None:
    """
    Login to the registered Password Pusher instance.

    Your email and API token is required.
    Your API token is available at https://pwpush.com/en/users/token.
    """
    r = requests.get(url + "/en/d/active", auth=(email, token), timeout=5)

    if r.status_code == 200:
        user_config["instance"]["url"] = url
        user_config["instance"]["email"] = email
        user_config["instance"]["token"] = token
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
    confirmation = typer.prompt("Are you sure? [y/n]")
    if confirmation:
        user_config["instance"]["email"] = "Not Set"
        user_config["instance"]["token"] = "Not Set"
        save_config()
        rprint("Log out successful.")


@app.command()
def push(
    days: int = typer.Option(None, help="Expire after this many days."),
    views: int = typer.Option(None, help="Expire after this many views."),
    deletable: bool = typer.Option(
        None, help="Allow users to delete passwords once retrieved."
    ),
    retrieval_step: bool = typer.Option(
        None,
        help="1-click retrieval step: Helps to avoid chat systems and URL scanners from eating up views.",
    ),
    note: str = typer.Option(
        None,
        help="Reference Note. Encrypted & Visible Only to You. E.g. Employee, Record or Ticket ID etc..  Requires login.",
    ),
    # prompt: bool = typer.Option(False, help="Prompt to enter payload interactively via the CLI."),
    # file: str = typer.Option('', help="Specify a text file that contains the payload.  Note: 1MB max."),
    payload: str = typer.Argument(
        "",
    ),
) -> None:
    """
    Push a new password, secret note or text.
    """
    path = "/p.json"

    data = {}
    data["password"] = {}
    data["password"]["payload"] = payload

    # Option and user preference processing
    if days:
        data["password"]["expire_after_days"] = days
    elif user_config["expiration"]["expire_after_days"] != "Not Set":
        data["password"]["expire_after_days"] = user_config["expiration"][
            "expire_after_days"
        ]

    if views:
        data["password"]["expire_after_views"] = views
    elif user_config["expiration"]["expire_after_views"] != "Not Set":
        data["password"]["expire_after_views"] = user_config["expiration"][
            "expire_after_views"
        ]

    if deletable:
        data["password"]["deletable_by_viewer"] = views
    elif user_config["expiration"]["deletable_by_viewer"] != "Not Set":
        data["password"]["deletable_by_viewer"] = user_config["expiration"][
            "deletable_by_viewer"
        ]

    if retrieval_step:
        data["password"]["retrieval_step"] = views
    elif user_config["expiration"]["retrieval_step"] != "Not Set":
        data["password"]["retrieval_step"] = user_config["expiration"]["retrieval_step"]

    response = make_request("POST", path, post_data=data)

    if response.status_code == 201:
        body = response.json()
        path = "/p/%s/preview.json" % body["url_token"]
        response = make_request("GET", path)

        body = response.json()
        if json_output():
            print(body)
        else:
            rprint(body["url"])
    else:
        rprint("Error:")
        rprint(response.status_code)
        rprint(response.text)


@app.command()
def expire(
    url_token: str = typer.Argument(
        "", help="The secret URL token of the push to be expired."
    )
) -> None:
    """
    Expire a push.
    """
    path = f"/p/{url_token}.json"

    response = make_request("DELETE", path)

    if response.status_code == 200:
        body = response.json()

        if json_output():
            print(body)
    else:
        rprint("Error:")
        rprint(response.status_code)
        rprint(response.text)


@app.command()
def audit(
    url_token: str = typer.Argument(
        "", help="The secret URL token of the push to audit."
    )
) -> None:
    """
    Show the audit log for the given push.
    """
    if user_config["instance"]["email"] == "Not Set":
        rprint("You must log into an instance first.")
        raise typer.Exit(1)

    path = f"/p/{url_token}/audit.json"

    response = make_request("GET", path)

    if response.status_code == 200:
        body = response.json()

        if json_output():
            print(body)
        else:
            rprint()
            rprint(f"[bold]=== Audit Log for {url_token}:[/bold]")
            rprint()

            table = Table(
                "IP", "User Agent", "Referrer", "Successful", "When", "Operation"
            )

            for v in body["views"]:
                if v["referrer"] == "":
                    v["referrer"] = "None"

                if v["kind"] == 0:
                    v["kind"] = "View"
                elif v["kind"] == 1:
                    v["kind"] = "Manual Deletion"

                v["created_at"] = parser.isoparse(v["created_at"]).strftime(
                    "%m/%d/%Y, %H:%M:%S UTC"
                )

                table.add_row(
                    v["ip"],
                    v["user_agent"],
                    v["referrer"],
                    str(v["successful"]),
                    v["created_at"],
                    v["kind"],
                )

            console.print(table)
    else:
        rprint("Error:")
        rprint(response.status_code)
        rprint(response.text)


@app.command()
def list(expired: bool = typer.Option(False, help="Show only expired pushes.")) -> None:
    """
    List active pushes (if logged in).
    """
    if user_config["instance"]["email"] == "Not Set":
        rprint("You must log into an instance first.")
        raise typer.Exit(1)

    path = "/en/d/active.json"
    if expired:
        path = "/en/d/expired.json"

    r = make_request("GET", path)

    if r.status_code == 200:
        if json_output():
            print(r.json())
        else:
            pushes = r.json()

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
                    "%s" % push["note"],
                    "{}/{}".format(
                        push["expire_after_views"] - push["views_remaining"],
                        push["expire_after_views"],
                    ),
                    "{}/{}".format(
                        push["expire_after_days"] - push["days_remaining"],
                        push["expire_after_days"],
                    ),
                    "%s" % push["deletable_by_viewer"],
                    "%s" % push["retrieval_step"],
                    "%s" % push["created_at"],
                )

            console.print(table)
    else:
        rprint("Error:")
        rprint(r.text)


def make_request(method, path, post_data=None):
    debug = debug_output()

    url = user_config["instance"]["url"]
    email = user_config["instance"]["email"]
    token = user_config["instance"]["token"]

    if debug:
        rprint(f"Communicating with {url} as user {email}")

    auth_headers = {}

    valid_email = email != "Not Set"
    valid_token = token != "Not Set"

    if valid_email and valid_token:
        auth_headers["X-User-Email"] = email
        auth_headers["X-User-Token"] = token

    if method == "GET":
        if debug:
            rprint(f"Making GET request to {url + path} with headers {auth_headers}")
        return requests.get(url + path, headers=auth_headers, timeout=5)
    elif method == "POST":
        if debug:
            rprint(
                f"Making JSON POST request to {url + path} with headers {auth_headers} and body {post_data}"
            )
        return requests.post(
            url + path, headers=auth_headers, json=post_data, timeout=5
        )
    elif method == "DELETE":
        if debug:
            rprint(f"Making DELETE request to {url + path} with headers {auth_headers}")
        return requests.delete(url + path, headers=auth_headers, timeout=5)


def json_output() -> Boolean:
    if cli_options["json"] == True or user_config["cli"]["json"] is True:
        return True
    return False


def verbose_output() -> Boolean:
    if cli_options["verbose"] == True or user_config["cli"]["verbose"] is True:
        return True
    return False


def debug_output() -> Boolean:
    if cli_options["debug"] == True or user_config["cli"]["debug"] is True:
        return True
    return False


def pretty_output() -> Boolean:
    if cli_options["pretty"] == True or user_config["cli"]["pretty"] is True:
        return True
    return False


app.add_typer(config.app, name="config", help="Show & modify CLI configuration.")

if __name__ == "__main__":
    app()
