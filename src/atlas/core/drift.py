"""Config value drift detection for the sync verb.

Drift occurs when a user edits a project config file (e.g. pyproject.toml)
after ``atlas init``.  The stored snapshot in ``.atlas/modules/<name>.json``
no longer matches reality.

``detect_value_drift`` re-scans config files for every installed module,
compares the freshly-extracted values with what is stored, and returns a
structured report.  The caller (sync handler) is responsible for writing
the updated snapshot back to disk and rebuilding retrieve files.
"""

from __future__ import annotations

import json
import os

from atlas.core.scanner import scan_module_config


def detect_value_drift(
    installed_modules: dict,
    atlas_dir: str,
    project_dir: str,
) -> dict:
    """Re-scan config files and compare with stored snapshots.

    For each installed module:
    1. Re-scan the project config file to extract current values.
    2. Load the stored snapshot from ``.atlas/modules/<name>.json``.
    3. Compare the freshly-extracted values with what is stored.
    4. If any value changed, record it as a drift item.

    Args:
        installed_modules: Dict of ``{name: meta}`` from the manifest.
        atlas_dir: Path to the ``.atlas/`` directory.
        project_dir: Path to the project root.

    Returns:
        A dict::

            {
                "drifted": [
                    {
                        "module": "ruff",
                        "changes": [
                            {"key": "style.line_length", "old": "120", "new": "100"}
                        ],
                    },
                    ...
                ],
                "unchanged": ["pytest", "git", ...],
            }
    """
    drifted: list[dict] = []
    unchanged: list[str] = []

    for module_name in installed_modules:
        scan = scan_module_config(module_name, project_dir)
        if not scan.get("found"):
            unchanged.append(module_name)
            continue

        fresh = _flatten(scan.get("extracted", {}))
        stored = _load_stored_values(module_name, atlas_dir)

        changes = _diff_values(stored, fresh)
        if changes:
            drifted.append({"module": module_name, "changes": changes})
        else:
            unchanged.append(module_name)

    return {"drifted": drifted, "unchanged": unchanged}


def apply_drift_updates(
    drifted: list[dict],
    atlas_dir: str,
    project_dir: str,
) -> list[str]:
    """Write updated values back to ``.atlas/modules/<name>.json`` for each drifted module.

    Merges the freshly-scanned extracted values into the existing snapshot
    (preserving all other fields) and overwrites the file.

    Args:
        drifted: The ``drifted`` list from :func:`detect_value_drift`.
        atlas_dir: Path to the ``.atlas/`` directory.
        project_dir: Path to the project root.

    Returns:
        List of module names whose snapshots were updated.
    """
    updated: list[str] = []
    modules_dir = os.path.join(atlas_dir, "modules")

    for item in drifted:
        module_name = item["module"]
        scan = scan_module_config(module_name, project_dir)
        if not scan.get("found"):
            continue

        snapshot_path = os.path.join(modules_dir, f"{module_name}.json")
        snapshot = _load_snapshot(snapshot_path)

        # Merge fresh extracted values into snapshot (top-level keys)
        for top_key, sub in scan.get("extracted", {}).items():
            if isinstance(sub, dict) and isinstance(snapshot.get(top_key), dict):
                snapshot[top_key] = {**snapshot[top_key], **sub}
            else:
                snapshot[top_key] = sub

        # Update config_file pointer
        snapshot["config_file"] = scan.get("config_file", snapshot.get("config_file", ""))

        os.makedirs(modules_dir, exist_ok=True)
        with open(snapshot_path, "w") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
            f.write("\n")

        updated.append(module_name)

    return updated


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _flatten(nested: dict, prefix: str = "") -> dict:
    """Flatten a nested dict to ``{dotted.key: value}`` pairs."""
    result: dict = {}
    for key, value in nested.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(_flatten(value, full_key))
        else:
            result[full_key] = str(value)
    return result


def _load_stored_values(module_name: str, atlas_dir: str) -> dict:
    """Load and flatten the non-meta values from the stored snapshot."""
    _META_KEYS = {
        "id", "name", "version", "category", "description",
        "config_file", "config_section", "detect_files",
        "detect_in_config", "for_languages", "requires",
        "combines_with", "conflicts_with", "config_locations",
        "config_keys", "system_tool", "health_check", "unlocks_verb",
        "commands", "rules",
    }
    path = os.path.join(atlas_dir, "modules", f"{module_name}.json")
    snapshot = _load_snapshot(path)
    data_keys = {k: v for k, v in snapshot.items() if k not in _META_KEYS}
    return _flatten(data_keys)


def _load_snapshot(path: str) -> dict:
    """Load JSON from *path*, returning ``{}`` on any error."""
    if not os.path.isfile(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def detect_new_tools(
    registry: dict,
    installed_modules: dict,
    project_dir: str,
) -> list[str]:
    """Return names of registry modules that are now detectable but not installed.

    On ``atlas sync``, the project may have gained new tool config files since
    the last ``atlas init`` (e.g. the user added ``[tool.mypy]`` to
    ``pyproject.toml``).  This function scans every *uninstalled* module in the
    registry to see if its config is now present in the project, and returns
    the names of modules that should be suggested for ``atlas add``.

    Args:
        registry: The loaded registry dict.
        installed_modules: Dict of ``{name: meta}`` from the manifest.
        project_dir: Path to the project root.

    Returns:
        Sorted list of module names that are newly detectable.
    """
    all_modules = registry.get("modules", {})
    installed_names = set(installed_modules.keys())
    suggestions: list[str] = []

    for module_name, mod_info in all_modules.items():
        if module_name in installed_names:
            continue

        # Check detect_files: any of these files exist in project_dir?
        for filename in mod_info.get("detect_files", []):
            if os.path.exists(os.path.join(project_dir, filename)):
                suggestions.append(module_name)
                break
        else:
            # Check detect_in_config: scan config for matching key/value
            if _config_matches(mod_info.get("detect_in_config", {}), project_dir):
                suggestions.append(module_name)

    return sorted(suggestions)


def _config_matches(detect_in_config: dict, project_dir: str) -> bool:
    """Return True if any detect_in_config rule matches a file in project_dir.

    ``detect_in_config`` maps ``{filename: substring}`` — if *substring*
    appears anywhere in the named file, it's a match.
    """
    if not detect_in_config:
        return False
    for filename, substring in detect_in_config.items():
        filepath = os.path.join(project_dir, filename)
        if os.path.isfile(filepath):
            try:
                content = open(filepath).read()
                if substring in content:
                    return True
            except OSError:
                pass
    return False


def detect_removed_tools(
    registry: dict,
    installed_modules: dict,
    project_dir: str,
) -> list[str]:
    """Return names of installed modules whose config is no longer detectable.

    On ``atlas sync``, an installed module's config file may have been
    removed or moved since ``atlas init`` (e.g. user deleted ``ruff.toml``).
    This function checks every installed module to see if it is still
    detectable.  Modules with no ``detect_files`` and no
    ``detect_in_config`` are always considered present (they cannot be
    detected by file presence — e.g. ``git`` or ``clippy``).

    The caller should warn the user but NOT auto-remove — the user may have
    simply moved the config to another file.

    Args:
        registry: The loaded registry dict.
        installed_modules: Dict of ``{name: meta}`` from the manifest.
        project_dir: Path to the project root.

    Returns:
        Sorted list of module names whose config is no longer found.
    """
    all_modules = registry.get("modules", {})
    gone: list[str] = []

    for module_name in installed_modules:
        mod_info = all_modules.get(module_name, {})
        detect_files = mod_info.get("detect_files", [])
        detect_in_config = mod_info.get("detect_in_config", {})

        # Modules with no detection criteria cannot be checked — skip
        if not detect_files and not detect_in_config:
            continue

        # If any detect_files exist, still present
        if any(
            os.path.exists(os.path.join(project_dir, f)) for f in detect_files
        ):
            continue

        # If any detect_in_config matches, still present
        if _config_matches(detect_in_config, project_dir):
            continue

        gone.append(module_name)

    return sorted(gone)


def _diff_values(stored: dict, fresh: dict) -> list[dict]:
    """Return list of ``{key, old, new}`` for values that changed or appeared."""
    changes: list[dict] = []
    all_keys = set(stored) | set(fresh)
    for key in sorted(all_keys):
        old = stored.get(key)
        new = fresh.get(key)
        if old != new:
            changes.append({"key": key, "old": old, "new": new})
    return changes
