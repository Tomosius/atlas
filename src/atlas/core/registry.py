"""Global module registry loading and querying."""

from __future__ import annotations

import json
import os


def load_registry(registry_path: str) -> dict:
    """Load registry.json from *registry_path*.

    Returns an empty dict if the file does not exist, cannot be read,
    or contains invalid JSON.
    """
    if not os.path.isfile(registry_path):
        return {}
    try:
        with open(registry_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def find_module(registry: dict, module_name: str) -> dict:
    """Return the registry entry for *module_name*, or {} if not found."""
    return registry.get("modules", {}).get(module_name, {})


def check_conflicts(
    registry: dict, module_name: str, installed: list[str]
) -> list[str]:
    """Return names of *installed* modules that conflict with *module_name*.

    Looks up the ``conflicts_with`` list in the registry entry and
    returns only the entries that appear in *installed*.
    An empty list means no conflicts.
    """
    mod_info = find_module(registry, module_name)
    if not mod_info:
        return []
    conflicts = mod_info.get("conflicts_with", [])
    return [c for c in conflicts if c in installed]


def get_dependencies(registry: dict, module_name: str) -> list[str]:
    """Return the ``requires`` list for *module_name*.

    Returns an empty list if the module is not found or has no
    dependencies.
    """
    mod_info = find_module(registry, module_name)
    if not mod_info:
        return []
    return list(mod_info.get("requires", []))
