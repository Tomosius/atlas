"""Module lifecycle management — install, remove, update."""

from __future__ import annotations

import json
import os

from atlas.core.errors import error_result, ok_result
from atlas.core.registry import (
    check_conflicts,
    find_module,
    get_dependents,
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


# ---------------------------------------------------------------------------
# Module lifecycle
# ---------------------------------------------------------------------------


def install_module(
    module_name: str,
    registry: dict,
    warehouse_dir: str,
    atlas_dir: str,
    manifest: dict,
    package_manager: str = "",
) -> dict:
    """Install a module from the warehouse into the project.

    Steps:
    1. Validate — exists in registry, not already installed, no conflicts.
    2. Load bundle from warehouse (``module.json``).
    3. Scan project config to extract current values.
    4. Enrich rules with extracted values.
    5. Resolve package manager variables in commands.
    6. Write to ``.atlas/modules/<name>.json``.
    7. Update manifest in-place.

    Returns ``ok_result(installed=name, warnings=[])`` on success,
    or an ``error_result`` on the first validation failure.
    """
    # 1. Validate
    installed = list(manifest.get("installed_modules", {}).keys())

    reg_entry = find_module(registry, module_name)
    if not reg_entry:
        return error_result("MODULE_NOT_FOUND", module_name)

    if module_name in installed:
        return error_result("MODULE_ALREADY_INSTALLED", module_name)

    conflicts = check_conflicts(registry, module_name, installed)
    if conflicts:
        return error_result(
            "MODULE_CONFLICT",
            f"{module_name} conflicts with {', '.join(conflicts)}",
        )

    # 2. Load bundle — fall back to a minimal dict when warehouse has no file.
    bundle = load_module_bundle(module_name, registry, warehouse_dir)
    if not bundle:
        bundle = {
            "id": module_name,
            "category": reg_entry.get("category", ""),
            "version": reg_entry.get("version", "1.0.0"),
        }

    # 3. Scan project config for extracted values.
    project_dir = os.path.dirname(os.path.abspath(atlas_dir))
    scan_result = scan_module_config(module_name, project_dir)

    # 4. Enrich — merge extracted config values into the bundle copy.
    rules = dict(bundle)
    if scan_result.get("found"):
        rules["config_file"] = scan_result.get("config_file", "")
        rules["config_section"] = scan_result.get("config_section", "")
        extracted = scan_result.get("extracted", {})
        if extracted:
            rules.setdefault("rules", {}).update(extracted)

    # 5. Resolve package manager variables in every command string.
    if package_manager:
        commands = rules.get("commands", {})
        if commands:
            rules["commands"] = {
                cmd_name: resolve_pkg_variables(str(cmd_str), package_manager)
                for cmd_name, cmd_str in commands.items()
            }

    # 6. Write to .atlas/modules/<name>.json.
    modules_dir = os.path.join(atlas_dir, "modules")
    os.makedirs(modules_dir, exist_ok=True)
    module_path = os.path.join(modules_dir, f"{module_name}.json")
    with open(module_path, "w") as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # 7. Update manifest.
    manifest.setdefault("installed_modules", {})[module_name] = {
        "version": bundle.get("version", "1.0.0"),
        "category": reg_entry.get("category", ""),
    }

    return ok_result(installed=module_name, warnings=[])


def remove_module(
    module_name: str,
    registry: dict,
    atlas_dir: str,
    manifest: dict,
) -> dict:
    """Remove a module from the project.

    Steps:
    1. Validate — is installed, no other installed module requires it.
    2. Delete ``.atlas/modules/<name>.json`` (if present).
    3. Delete ``.atlas/retrieve/<name>.md`` (if present).
    4. Remove from manifest in-place.

    Returns ``ok_result(removed=name)`` on success,
    or an ``error_result`` on validation failure.
    """
    installed = manifest.get("installed_modules", {})

    if module_name not in installed:
        return error_result("MODULE_NOT_INSTALLED", module_name)

    dependents = get_dependents(registry, module_name, list(installed.keys()))
    if dependents:
        return error_result(
            "MODULE_REQUIRED",
            f"Required by: {', '.join(dependents)}",
        )

    # Delete associated files — silently skip if absent.
    for subdir, ext in (("modules", ".json"), ("retrieve", ".md")):
        path = os.path.join(atlas_dir, subdir, f"{module_name}{ext}")
        if os.path.isfile(path):
            os.remove(path)

    del manifest["installed_modules"][module_name]

    return ok_result(removed=module_name)


def update_modules(
    registry: dict,
    warehouse_dir: str,
    atlas_dir: str,
    manifest: dict,
    package_manager: str = "",
) -> dict:
    """Re-enrich installed modules whose warehouse version is newer.

    For each installed module:
    1. Look up the warehouse version from the registry entry.
    2. Skip if versions match or warehouse has no version.
    3. Re-load bundle, re-scan config, re-enrich, resolve pkg variables.
    4. Overwrite ``.atlas/modules/<name>.json``.
    5. Update manifest version in-place.

    Returns ``ok_result(updated=[...], skipped=[...])`` listing both groups.
    """
    installed = manifest.get("installed_modules", {})
    updated: list[str] = []
    skipped: list[str] = []

    project_dir = os.path.dirname(os.path.abspath(atlas_dir))
    modules_dir = os.path.join(atlas_dir, "modules")
    os.makedirs(modules_dir, exist_ok=True)

    for module_name, meta in installed.items():
        reg_entry = find_module(registry, module_name)
        if not reg_entry:
            skipped.append(module_name)
            continue

        warehouse_version = reg_entry.get("version", "")
        installed_version = meta.get("version", "")

        if not warehouse_version or warehouse_version == installed_version:
            skipped.append(module_name)
            continue

        # Re-load bundle.
        bundle = load_module_bundle(module_name, registry, warehouse_dir)
        if not bundle:
            bundle = {
                "id": module_name,
                "category": reg_entry.get("category", ""),
                "version": warehouse_version,
            }

        # Re-scan config.
        scan_result = scan_module_config(module_name, project_dir)

        # Re-enrich.
        rules = dict(bundle)
        if scan_result.get("found"):
            rules["config_file"] = scan_result.get("config_file", "")
            rules["config_section"] = scan_result.get("config_section", "")
            extracted = scan_result.get("extracted", {})
            if extracted:
                rules.setdefault("rules", {}).update(extracted)

        # Resolve pkg variables.
        if package_manager:
            commands = rules.get("commands", {})
            if commands:
                rules["commands"] = {
                    cmd_name: resolve_pkg_variables(str(cmd_str), package_manager)
                    for cmd_name, cmd_str in commands.items()
                }

        # Overwrite module file.
        module_path = os.path.join(modules_dir, f"{module_name}.json")
        with open(module_path, "w") as f:
            json.dump(rules, f, indent=2, ensure_ascii=False)
            f.write("\n")

        # Update manifest version.
        manifest["installed_modules"][module_name]["version"] = warehouse_version

        updated.append(module_name)

    return ok_result(updated=updated, skipped=skipped)


