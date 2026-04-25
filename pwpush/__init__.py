# mypy: disable-error-code="attr-defined"
"""Command Line Interface to Password Pusher - secure information distribution with automatic expiration controls."""

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
                # Try tomllib (Python 3.11+) or tomli (Python 3.10)
                try:
                    import tomllib
                except ImportError:
                    try:
                        import tomli as tomllib
                    except ImportError:
                        # Fallback: simple regex extraction for Python 3.10 without tomli
                        import re

                        content = pyproject_path.read_text()
                        match = re.search(
                            r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE
                        )
                        if match:
                            return match.group(1)
                        return "unknown"

                with open(pyproject_path, "rb") as f:
                    pyproject_data = tomllib.load(f)
                    return pyproject_data.get("project", {}).get("version", "unknown")
        except Exception:
            pass
        return "unknown"


version: str = get_version()
