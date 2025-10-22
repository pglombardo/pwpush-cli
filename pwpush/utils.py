"""Utility functions for the pwpush CLI."""


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


def parse_boolean(value: bool | str | None) -> bool:
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
