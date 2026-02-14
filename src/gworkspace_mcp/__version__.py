"""Version information for gworkspace-mcp."""

from pathlib import Path


def _get_version() -> str:
    """Get version from VERSION file or fallback to hardcoded."""
    # Try package-level VERSION file first
    pkg_version = Path(__file__).parent / "VERSION"
    if pkg_version.exists():
        return pkg_version.read_text().strip()

    # Try project root VERSION file
    root_version = Path(__file__).parent.parent.parent.parent / "VERSION"
    if root_version.exists():
        return root_version.read_text().strip()

    # Fallback
    return "0.1.0"


__version__ = _get_version()
