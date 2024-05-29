# type: ignore[attr-defined]
from enum import Enum
import getpass
import secrets
import string

import requests
import typer
from dateutil import parser
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from pwpush import version
from pwpush.commands import config
from pwpush.commands.config import save_config, user_config
from pwpush.options import cli_options


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


def genpass(length=5):
    """Generate a passphrase"""
    from xkcdpass.xkcd_password import generate_xkcdpassword, generate_wordlist

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


def generate_password(length=50):
    """Generate a secure random password"""
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(characters) for _ in range(length))
    return password


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
    cli_options["verbose"] = verbose.lower() in {"true", "yes", "on"}
    cli_options["debug"] = debug.lower() in {"true", "yes", "on"}
    cli_options["pretty"] = pretty.lower() in {"true", "yes", "on"}


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
    r = requests.get(f"{url}/en/d/active", auth=(email, token), timeout=5)

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
    if confirmation := typer.prompt("Are you sure? [y/n]"):
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
    auto: bool = typer.Option(False, help="Auto create password and passphrase"),
    secret: str = typer.Option(None, help="something", hide_input=True, confirmation_prompt=True),
    passphrase: str = typer.Option(None,  help="Add a passphrase"),
    
) -> None:
    """
    Push a new password, secret note or text.
    """
    path = "/p.json"

    data = {"password": {}}

    if auto:
        secret = generate_password(50)
        passphrase = genpass(2)
    
    if not secret:
        secret = typer.prompt("Enter secret", hide_input=True, confirmation_prompt=True)
    if not passphrase:
        first = None
        second = None
        # Rolling out own here as there is no easy way to prompt with a confirmation and at the same time allow it to be omitted
        while True:
            if first is None:
                first = getpass.getpass("Enter passphrase (If the passphrase it empty if will be omitted): ")

            if first in ("c", "C", ""):
                passphrase = None
                break
            
            if second is None:
                second = getpass.getpass("Confirm passphrase: ")
            
            if first is not None and second is not None and first == second:
                passphrase = first
                break
     
    data["password"]["payload"] = secret

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

    if passphrase is not None:
        data["password"]["passphrase"] = passphrase

    # Lets add a progressbar to notify the something is happing.
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Processing...", total=None)

        response = make_request("POST", path, post_data=data)

        if response.status_code == 201:
            body = response.json()
            path = f'/p/{body["url_token"]}/preview.json'
            response = make_request("GET", path)

            body = response.json()
            if json_output():
                print(body)
            else:
                rprint(f"The secret has been pushed to:\n{body['url']}")
            
            if auto and passphrase:
                rprint(f"Passphrase is: {passphrase}")
        else:
            rprint("Error:")
            rprint(response.status_code)
            rprint(response.text)


@app.command(name="push-file")
def pushFile(
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
    payload: str = typer.Argument(
        "",
    ),
) -> None:
    """
    Push a new file.
    """
    path = "/f.json"

    data = {"file_push": {}}
    data["file_push"]["payload"] = ""

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

    if deletable:
        data["file_push"]["deletable_by_viewer"] = views
    elif user_config["expiration"]["deletable_by_viewer"] != "Not Set":
        data["file_push"]["deletable_by_viewer"] = user_config["expiration"][
            "deletable_by_viewer"
        ]

    if retrieval_step:
        data["file_push"]["retrieval_step"] = views
    elif user_config["expiration"]["retrieval_step"] != "Not Set":
        data["file_push"]["retrieval_step"] = user_config["expiration"][
            "retrieval_step"
        ]

    with open(payload, "rb") as fd:
        upload_files = {"file_push[files][]": fd}
        response = make_request("POST", path, upload_files=upload_files, post_data=data)

    if response.status_code == 201:
        body = response.json()
        path = f'/f/{body["url_token"]}/preview.json'
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

    path = "/en/d/expired.json" if expired else "/en/d/active.json"
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
                    f'{push["note"]}',
                    f'{push["expire_after_views"] - push["views_remaining"]}/{push["expire_after_views"]}',
                    f'{push["expire_after_days"] - push["days_remaining"]}/{push["expire_after_days"]}',
                    f'{push["deletable_by_viewer"]}',
                    f'{push["retrieval_step"]}',
                    f'{push["created_at"]}',
                )

            console.print(table)
    else:
        rprint("Error:")
        rprint(r.text)


def make_request(method, path, post_data=None, upload_files=None):
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
        return requests.get(url + path, headers=auth_headers, timeout=30)
    elif method == "POST":
        if debug:
            rprint(
                f"Making JSON POST request to {url + path} with headers {auth_headers} body {post_data}"
            )
            if upload_files is not None:
                rprint("Attaching a file to the upload")
        return requests.post(
            url + path,
            headers=auth_headers,
            json=post_data,
            timeout=30,
            files=upload_files,
        )
    elif method == "DELETE":
        if debug:
            rprint(f"Making DELETE request to {url + path} with headers {auth_headers}")
        return requests.delete(url + path, headers=auth_headers, timeout=5)


def json_output() -> bool:
    user_config_json = user_config["cli"]["json"].lower() in ["true", "yes", "on"]
    return cli_options["json"] == True or user_config_json


def verbose_output() -> bool:
    user_config_verbose = user_config["cli"]["verbose"].lower() in ["true", "yes", "on"]
    return cli_options["verbose"] == True or user_config_verbose


def debug_output() -> bool:
    user_config_debug = user_config["cli"]["debug"].lower() in ["true", "yes", "on"]
    return cli_options["debug"] == True or user_config_debug


def pretty_output() -> bool:
    user_config_pretty = user_config["cli"]["debug"].lower() in ["true", "yes", "on"]
    return cli_options["pretty"] == True or user_config_pretty


app.add_typer(config.app, name="config", help="Show & modify CLI configuration.")

if __name__ == "__main__":
    app()
