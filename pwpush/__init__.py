# mypy: disable-error-code="attr-defined"
"""Command Line Interface to Password Pusher - secure information distribution with automatic expiration controls."""

import sys
from importlib import metadata as importlib_metadata
from pathlib import Path


def get_version() -> str:
    try:
        return importlib_metadata.version(__name__)
    except importlib_metadata.PackageNotFoundError:
        # Fallback: read version from pyproject.toml when running from source
        try:
            pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
            if pyproject_path.exists():
                import tomllib

                with open(pyproject_path, "rb") as f:
                    pyproject_data = tomllib.load(f)
                    return pyproject_data.get("project", {}).get("version", "unknown")
        except Exception:
            pass
        return "unknown"


version: str = get_version()
