"""Utility functions for the pwpush CLI."""


def parse_boolean(value) -> bool:
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
