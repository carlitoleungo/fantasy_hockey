"""
Build/version helpers.

get_build_id() returns the short git commit hash of the current deployment,
so the user can quickly verify which version is running on Community Cloud
versus locally. Falls back to "dev" if git isn't available.
"""
from __future__ import annotations

import subprocess


def get_build_id() -> str:
    """Return the short (7-char) git commit hash, or 'dev' if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "dev"
