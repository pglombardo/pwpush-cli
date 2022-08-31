import configparser
import os
from pathlib import Path

import typer

user_config = configparser.ConfigParser()
user_config_dir = Path(typer.get_app_dir("pwpush"))
user_config_file = user_config_dir.joinpath("config.ini")

cli_options = {}
cli_options["json"] = False
cli_options["verbose"] = False
cli_options["debug"] = False

default_config = {}
default_config["instance"] = {}
default_config["instance"]["url"] = "https://pwpush.com"
default_config["instance"]["email"] = "Not Set"
default_config["instance"]["token"] = "Not Set"

default_config["expiration"] = {}
default_config["expiration"]["expire_after_days"] = "Not Set"
default_config["expiration"]["expire_after_views"] = "Not Set"
default_config["expiration"]["retrieval_step"] = "Not Set"
default_config["expiration"]["deletable_by_viewer"] = "Not Set"

default_config["cli"] = {}
default_config["cli"]["json"] = "False"
default_config["cli"]["verbose"] = "False"
default_config["cli"]["pretty"] = "False"
default_config["cli"]["debug"] = "False"


def load_config():
    """
    Load existing config or write out a new default one (and use that)
    """
    if os.path.exists(user_config_file) is True:
        user_config.read(user_config_file)

        validate_user_config()
    else:
        # No config file exists; Write out a new file with default settings

        # Write out default settings to a new config file
        if os.path.exists(user_config_dir) is False:
            Path.mkdir(user_config_dir)

        with open(user_config_file, "x") as file:
            default_config.write(file)


def validate_user_config():
    """
    Validate `user_config` and assure that all default keys are set
    and available.
    """
    if "instance" not in user_config:
        user_config["instance"] = {}
    if "expiration" not in user_config:
        user_config["expiration"] = {}
    if "cli" not in user_config:
        user_config["cli"] = {}

    # Merge the default config into the user config correcting any missing keys
    # This pattern supports Python >=3.5
    user_config["instance"] = {**default_config["instance"], **user_config["instance"]}
    user_config["expiration"] = {
        **default_config["expiration"],
        **user_config["expiration"],
    }
    user_config["cli"] = {**default_config["cli"], **user_config["cli"]}
    save_config()


def save_config():
    """
    Save `user_config` out to file
    """
    # Write out default settings
    with open(user_config_file, "w") as file:
        user_config.write(file)


def json_output() -> bool:
    """
    Determines whether we should output in json.
    """
    if cli_options["json"] == True or user_config["cli"]["json"] is True:
        return True
    return False


def verbose_output() -> bool:
    """
    Determines whether we should provide verbose output.
    """
    if cli_options["verbose"] == True or user_config["cli"]["verbose"] is True:
        return True
    return False


def debug_output() -> bool:
    """
    Determines whether we should provide debug output.
    """
    if cli_options["debug"] == True or user_config["cli"]["debug"] is True:
        return True
    return False


load_config()
