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


# Category priority order used to sort recommendations.
# Lower index = higher priority.
_CATEGORY_PRIORITY: list[str] = [
    "vcs",
    "language",
    "pkg_manager",
    "linter",
    "formatter",
    "testing",
    "framework",
    "database",
    "environment",
    "ci_cd",
    "platform",
    "stack",
    "tool",
]


def _category_rank(category: str) -> int:
    """Return sort key for *category* (lower = higher priority)."""
    try:
        return _CATEGORY_PRIORITY.index(category)
    except ValueError:
        return len(_CATEGORY_PRIORITY)


def get_recommendations(registry: dict, detection: object) -> list[dict]:
    """Return recommended modules based on *detection* results.

    *detection* is a ``ProjectDetection`` dataclass (or any object with
    the same attributes).  Each returned dict has the shape::

        {"name": str, "category": str, "reason": str}

    Results are ordered by category priority (vcs → language →
    pkg_manager → linter → formatter → testing → …).
    An empty list is returned when nothing matches or on bad input.
    """
    modules = registry.get("modules", {})
    if not modules:
        return []

    # Safely pull detection attributes — tolerate plain dicts or dataclasses.
    def _attr(name: str, default):
        if isinstance(detection, dict):
            return detection.get(name, default)
        return getattr(detection, name, default)

    detected_languages: list[str] = _attr("languages", [])
    detected_frameworks: list[str] = _attr("frameworks", [])
    detected_databases: list[str] = _attr("databases", [])
    detected_pkg_manager: str = _attr("package_manager", "none")
    detected_tools: list[str] = _attr("existing_tools", [])
    detected_stack: str = _attr("stack", "")

    recommendations: list[dict] = []

    for name, entry in modules.items():
        category = entry.get("category", "")
        for_languages: list[str] = entry.get("for_languages", [])
        reason: str = ""

        # If the module targets specific languages, skip unless one matches.
        if for_languages and not any(
            lang in detected_languages for lang in for_languages
        ):
            continue

        if category == "language":
            detect_files: list[str] = entry.get("detect_files", [])
            # Include language module if this language was detected.
            if name in detected_languages:
                reason = f"detected language: {name}"
            else:
                continue

        elif category == "framework":
            if name in detected_frameworks:
                reason = f"detected framework: {name}"
            else:
                continue

        elif category == "database":
            if name in detected_databases:
                reason = f"detected database: {name}"
            else:
                continue

        elif category == "pkg_manager":
            if name == detected_pkg_manager:
                reason = f"detected package manager: {name}"
            else:
                continue

        elif category == "stack":
            if name == detected_stack:
                reason = f"detected stack: {name}"
            else:
                continue

        elif category in ("vcs", "linter", "formatter", "testing",
                          "environment", "ci_cd", "platform", "tool"):
            # Include if the tool was detected in existing_tools, or
            # always include vcs when any vcs tool is detected.
            if name in detected_tools:
                reason = f"detected tool: {name}"
            elif category == "vcs" and any(t in detected_tools for t in ("git",)):
                # Generic vcs match — only include the specific detected vcs.
                continue
            else:
                continue

        else:
            # Unknown category — skip.
            continue

        recommendations.append({"name": name, "category": category, "reason": reason})

    recommendations.sort(key=lambda r: _category_rank(r["category"]))
    return recommendations


def load_module_bundle(
    module_name: str, registry: dict, warehouse_dir: str
) -> dict:
    """Load the ``module.json`` for *module_name* from the warehouse.

    Resolves the bundle directory via the registry entry's ``path``
    field.  Returns an empty dict if the module is not registered, the
    path is missing, the file does not exist, or JSON parsing fails.
    """
    reg_entry = find_module(registry, module_name)
    if not reg_entry:
        return {}

    module_path = reg_entry.get("path", "")
    if not module_path:
        return {}

    module_json = os.path.join(warehouse_dir, module_path, "module.json")
    if not os.path.isfile(module_json):
        return {}

    try:
        with open(module_json) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def load_module_rules_md(
    module_name: str, registry: dict, warehouse_dir: str
) -> str:
    """Load the ``rules.md`` content for *module_name* from the warehouse.

    Returns the markdown string, or an empty string if the module is not
    registered, the path is missing, the file does not exist, or the
    file cannot be read.
    """
    reg_entry = find_module(registry, module_name)
    if not reg_entry:
        return ""

    module_path = reg_entry.get("path", "")
    if not module_path:
        return ""

    rules_file = os.path.join(warehouse_dir, module_path, "rules.md")
    if not os.path.isfile(rules_file):
        return ""

    try:
        with open(rules_file) as f:
            return f.read()
    except OSError:
        return ""
