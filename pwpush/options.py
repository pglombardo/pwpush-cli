from typing import Any

import configparser
import os
from pathlib import Path

import typer

from pwpush.utils import parse_boolean

user_config = configparser.ConfigParser()
user_config_dir = Path(typer.get_app_dir("pwpush"))
user_config_file = user_config_dir.joinpath("config.ini")

cli_options = {
    "json": False,
    "verbose": False,
    "pretty": False,
    "debug": False,
    "insecure": False,
}
default_config: dict[str, dict[str, Any]] = {"instance": {}}
default_config["instance"]["url"] = "https://eu.pwpush.com"
default_config["instance"]["email"] = "Not Set"
default_config["instance"]["token"] = "Not Set"
default_config["instance"]["api_profile"] = "Not Set"
default_config["instance"]["api_profile_checked_at"] = "0"
default_config["instance"]["api_profile_ttl_seconds"] = "3600"

default_config["expiration"] = {
    "expire_after_days": "Not Set",
    "expire_after_views": "Not Set",
    "retrieval_step": "Not Set",
    "deletable_by_viewer": "Not Set",
}
default_config["cli"] = {
    "json": "False",
    "verbose": "False",
    "pretty": "False",
    "debug": "False",
}

default_config["pro"] = {
    "notify": "Not Set",
    "notify_locale": "Not Set",
}


def config_file_exists() -> bool:
    """
    Check whether the user configuration file exists.
    """
    return user_config_file.exists()


def load_config() -> None:
    """
    Load existing config or defaults without creating a config file.
    """
    user_config.clear()
    if config_file_exists():
        user_config.read(user_config_file)

        if validate_user_config():
            save_config()
    else:
        # No config file exists; use defaults in memory until explicitly saved.
        user_config.read_dict(default_config)


def validate_user_config() -> bool:
    """
    Validate `user_config` and assure that all default keys are set
    and available. Returns True when missing values were added.
    """
    changed = False

    if "instance" not in user_config:
        user_config["instance"] = {}
        changed = True
    if "expiration" not in user_config:
        user_config["expiration"] = {}
        changed = True
    if "cli" not in user_config:
        user_config["cli"] = {}
        changed = True
    if "pro" not in user_config:
        user_config["pro"] = {}
        changed = True

    for section, defaults in default_config.items():
        for key, value in defaults.items():
            if key not in user_config[section]:
                user_config[section][key] = str(value)
                changed = True

    return changed


def save_config() -> None:
    """
    Save `user_config` out to file with restricted permissions (owner read/write only).
    """
    user_config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(user_config_file, "w") as file:
        user_config.write(file)
    # Restrict permissions to owner read/write only (0o600) to protect API tokens
    os.chmod(user_config_file, 0o600)


def json_output() -> bool:
    """
    Determines whether we should output in json.
    """
    return cli_options["json"] or parse_boolean(user_config["cli"]["json"])


def verbose_output() -> bool:
    """
    Determines whether we should provide verbose output.
    """
    return cli_options["verbose"] or parse_boolean(user_config["cli"]["verbose"])


def debug_output() -> bool:
    """
    Determines whether we should provide debug output.
    """
    return cli_options["debug"] or parse_boolean(user_config["cli"]["debug"])


load_config()
