"""Module lifecycle management — install, remove, update."""

from __future__ import annotations

import json
import os

from atlas.core.errors import error_result, ok_result
from atlas.core.registry import (
    check_conflicts,
    find_module,
    load_module_bundle,
    load_module_rules_md,
)
from atlas.core.scanner import enrich_module_rules, scan_module_config

# ---------------------------------------------------------------------------
# Package manager command templates
# ---------------------------------------------------------------------------

# Maps a package manager name to the concrete commands used to fill
# {{pkg_run}}, {{pkg_add}}, {{pkg_add_dev}}, and {{pkg_sync}} placeholders
# that appear in module bundle command strings.
PKG_VARIABLES: dict[str, dict[str, str]] = {
    "uv": {
        "pkg_run": "uv run",
        "pkg_add": "uv add",
        "pkg_add_dev": "uv add --dev",
        "pkg_sync": "uv sync",
    },
    "pip": {
        "pkg_run": "python -m",
        "pkg_add": "pip install",
        "pkg_add_dev": "pip install",
        "pkg_sync": "pip install -r requirements.txt",
    },
    "poetry": {
        "pkg_run": "poetry run",
        "pkg_add": "poetry add",
        "pkg_add_dev": "poetry add --dev",
        "pkg_sync": "poetry install",
    },
    "pnpm": {
        "pkg_run": "pnpm",
        "pkg_add": "pnpm add",
        "pkg_add_dev": "pnpm add --save-dev",
        "pkg_sync": "pnpm install",
    },
    "npm": {
        "pkg_run": "npx",
        "pkg_add": "npm install",
        "pkg_add_dev": "npm install --save-dev",
        "pkg_sync": "npm install",
    },
    "yarn": {
        "pkg_run": "yarn",
        "pkg_add": "yarn add",
        "pkg_add_dev": "yarn add --dev",
        "pkg_sync": "yarn install",
    },
    "bun": {
        "pkg_run": "bun",
        "pkg_add": "bun add",
        "pkg_add_dev": "bun add --dev",
        "pkg_sync": "bun install",
    },
    "cargo": {
        "pkg_run": "cargo",
        "pkg_add": "cargo add",
        "pkg_add_dev": "cargo add --dev",
        "pkg_sync": "cargo build",
    },
}


def resolve_pkg_variables(text: str, package_manager: str) -> str:
    """Replace ``{{pkg_run}}``, ``{{pkg_add}}``, ``{{pkg_add_dev}}``,
    and ``{{pkg_sync}}`` in *text* with the concrete commands for
    *package_manager*.

    Falls back to the ``pip`` template when *package_manager* is unknown.
    Unknown placeholder tokens are left unchanged.
    """
    variables = PKG_VARIABLES.get(package_manager, PKG_VARIABLES["pip"])
    for var_name, replacement in variables.items():
        text = text.replace("{{" + var_name + "}}", replacement)
    return text
