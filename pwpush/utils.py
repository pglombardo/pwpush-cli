"""Utility functions for the pwpush CLI."""

from typing import Any

import secrets
import string

from xkcdpass.xkcd_password import generate_wordlist, generate_xkcdpassword


def mask_sensitive_value(value: str, visible_chars: int = 4) -> str:
    """Mask sensitive values like API tokens with asterisks.

    Args:
        value: The sensitive value to mask
        visible_chars: Number of characters to show at the end (default: 4)

    Returns:
        str: The masked value with asterisks

    Examples:
        >>> mask_sensitive_value("abc123def456")
        '********f456'
        >>> mask_sensitive_value("short", 2)
        '***rt'
        >>> mask_sensitive_value("", 4)
        'Not Set'
    """
    if not value or value == "Not Set":
        return "Not Set"

    if len(value) <= visible_chars:
        return "*" * len(value)

    return "*" * (len(value) - visible_chars) + value[-visible_chars:]


def parse_boolean(value: Any) -> bool:
    """Parse a boolean value from string or boolean input.

    Args:
        value: The value to parse (bool, str, or other)

    Returns:
        bool: The parsed boolean value

    Examples:
        >>> parse_boolean(True)
        True
        >>> parse_boolean("true")
        True
        >>> parse_boolean("yes")
        True
        >>> parse_boolean("false")
        False
        >>> parse_boolean(None)
        False
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ["true", "yes", "on", "1"]
    return False


def check_secret_conditions(
    secret: str,
    punctuation: bool = True,
    upper: bool = True,
    digit: bool = True,
    lower: bool = True,
    length: int = 20,
) -> bool:
    """Check if a secret meets conditions."""
    conditions: list[bool] = []

    if punctuation:
        conditions.append(any(s in string.punctuation for s in secret))
    if lower:
        conditions.append(any(s.islower() for s in secret))
    if upper:
        conditions.append(any(s.isupper() for s in secret))
    if digit:
        conditions.append(any(s.isdigit() for s in secret))
    if length:
        conditions.append(len(secret) == length)

    return all(conditions)


def generate_passphrase(length: int = 5) -> str:
    """Generate a passphrase using xkcdpass.

    Args:
        length: Number of words in the passphrase (default: 5)

    Returns:
        str: A randomly generated passphrase
    """
    wordlist = generate_wordlist(
        wordfile=None, min_length=5, max_length=9, valid_chars="[a-zA-Z1-9]"
    )
    return str(
        generate_xkcdpassword(
            wordlist,
            interactive=False,
            numwords=length,
            acrostic=False,
            delimiter=" ",
            random_delimiters=True,
            case="random",
        )
    )


def generate_secret(length: int = 50) -> str:
    """Generate a secure random password.

    Args:
        length: Length of the password (default: 50)

    Returns:
        str: A randomly generated secure password

    Raises:
        RuntimeError: If unable to generate a valid secret after maximum attempts.
    """
    characters = string.ascii_letters + string.digits + string.punctuation
    max_attempts = 1000
    for _ in range(max_attempts):
        secret = "".join(secrets.choice(characters) for _ in range(length))
        if check_secret_conditions(secret, length=length):
            return secret
    raise RuntimeError(f"Failed to generate valid secret after {max_attempts} attempts")
