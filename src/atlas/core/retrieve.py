"""Build pre-computed retrieve files from module rules and warehouse content."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from atlas.core.registry import find_module, load_module_rules_md


def build_retrieve_file(
    module_name: str,
    atlas_dir: str,
    registry: dict,
    warehouse_dir: str,
    installed_modules: dict,
    config: dict | None = None,
) -> str:
    """Build a single retrieve .md file for a module.

    Combines:
    1. rules.md from warehouse (base content)
    2. Extracted config values from .atlas/modules/<name>.json
    3. Linked module summaries (if configured in retrieve_links)

    Returns the built Markdown content.
    """
    config = config or {}

    # Read base rules from warehouse
    content = load_module_rules_md(module_name, registry, warehouse_dir)

    # Read extracted values from installed module rules
    module_rules = _load_module_rules(module_name, atlas_dir)

    # Inject values following the truth hierarchy:
    #   Priority 1 — snapshot (.atlas/modules/<name>.json) overrides warehouse defaults
    #   Priority 4 — warehouse rules.md provides the base template
    # All non-meta keys are injected: extracted config values AND commands.
    if module_rules:
        _META_KEYS = {
            "id", "name", "version", "category", "description",
            "config_file", "config_section", "detect_files",
            "detect_in_config", "for_languages", "requires",
            "combines_with", "conflicts_with", "config_locations",
            "config_keys", "system_tool", "health_check", "unlocks_verb",
            "synced_at",
        }
        for key, value in module_rules.items():
            if key in _META_KEYS:
                continue
            if isinstance(value, dict):
                content = _inject_values(content, value, prefix=key)
            else:
                content = content.replace("{{" + key + "}}", str(value))

        # Add config source info
        config_file = module_rules.get("config_file", "")
        if config_file:
            content += f"\n\n> Config source: `{config_file}`\n"

        # Add freshness timestamp
        synced_at = module_rules.get("synced_at", "")
        if synced_at:
            freshness = _format_freshness(synced_at)
            content += f"\n\n> {freshness}\n"

    # Append linked module summaries
    retrieve_links = config.get("retrieve_links", {})
    linked = retrieve_links.get(module_name, [])
    for linked_name in linked:
        if linked_name in installed_modules and linked_name != module_name:
            linked_content = load_module_rules_md(linked_name, registry, warehouse_dir)
            if linked_content:
                summary = _condense(linked_content, max_sections=2)
                content += f"\n\n---\n\n## Linked: {linked_name}\n\n{summary}"

    return content


def build_status_file(
    manifest: dict,
    installed_modules: dict,
    *,
    active_task: dict | None = None,
    recent_activity: list[dict] | None = None,
    git_status: str = "",
) -> str:
    """Build the _status.md overview file.

    This is the first thing agents read at session start. It contains:
    - Project type, languages, stack
    - Installed modules grouped by category
    - Active task (if provided)
    - Recent activity (if provided)
    - Git status (if provided)
    - Retrieval hints
    """
    detected = manifest.get("detected", {})
    languages = detected.get("languages", [])
    stack = detected.get("stack", "")
    pkg_mgr = detected.get("package_manager", "")

    lines = ["# Atlas Project Status", ""]

    # Project overview
    if languages:
        lines.append(f"**Languages:** {', '.join(languages)}")
    if stack:
        lines.append(f"**Stack:** {stack}")
    if pkg_mgr and pkg_mgr != "none":
        lines.append(f"**Package Manager:** {pkg_mgr}")
    lines.append("")

    # Installed modules by category
    by_category: dict[str, list[str]] = {}
    for mod_name, mod_info in installed_modules.items():
        cat = mod_info.get("category", "other")
        by_category.setdefault(cat, []).append(mod_name)

    if by_category:
        lines.append("## Installed Modules")
        for cat in sorted(by_category):
            mods = ", ".join(sorted(by_category[cat]))
            lines.append(f"- **{cat}:** {mods}")
        lines.append("")

    # Active task
    if active_task:
        task_type = active_task.get("type", "task")
        task_id = active_task.get("id", "")
        task_title = active_task.get("title", "")
        lines.append("## Active Task")
        lines.append(f"→ {task_type} #{task_id}: {task_title}")
        lines.append("")

    # Recent activity
    if recent_activity:
        lines.append("## Recent Activity")
        for entry in recent_activity:
            lines.append(f"  {entry.get('ago', '?')}: {entry.get('summary', '')}")
        lines.append("")

    # Git status
    if git_status:
        lines.append("## Git Status")
        lines.append(git_status)
        lines.append("")

    # Available retrieve targets
    retrievable = sorted(list(installed_modules.keys()) + ["structure", "project"])
    lines.append(f"## Retrievable: {', '.join(retrievable)}")
    lines.append("")

    return "\n".join(lines)


def build_all_retrieve_files(
    atlas_dir: str,
    registry: dict,
    warehouse_dir: str,
    manifest: dict,
    config: dict | None = None,
) -> list[str]:
    """Build all retrieve files for all installed modules + auto-modules.

    Returns list of module names that were built.
    """
    config = config or {}
    installed = manifest.get("installed_modules", {})
    retrieve_dir = os.path.join(atlas_dir, "retrieve")
    os.makedirs(retrieve_dir, exist_ok=True)
    built = []

    for mod_name in installed:
        content = build_retrieve_file(
            mod_name, atlas_dir, registry, warehouse_dir, installed, config
        )
        if content:
            path = os.path.join(retrieve_dir, f"{mod_name}.md")
            with open(path, "w") as f:
                f.write(content)
            built.append(mod_name)

    # Build status file
    status_content = build_status_file(manifest, installed)
    with open(os.path.join(retrieve_dir, "_status.md"), "w") as f:
        f.write(status_content)
    built.append("_status")

    return built


# --- Internal helpers ---


def _load_module_rules(module_name: str, atlas_dir: str) -> dict:
    """Load enriched module rules from .atlas/modules/<name>.json."""
    path = os.path.join(atlas_dir, "modules", f"{module_name}.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _inject_values(content: str, rules_data: dict, prefix: str = "") -> str:
    """Replace {{key}} placeholders in content with values from rules_data."""
    for key, value in rules_data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            content = _inject_values(content, value, full_key)
        else:
            placeholder = "{{" + full_key + "}}"
            content = content.replace(placeholder, str(value))
    return content


def filter_sections(content: str, filter_words: list[str]) -> str:
    """Return only the sections of *content* whose headers match any filter word.

    A section begins at any line starting with ``#`` and ends just before the
    next same-or-higher-level header (or at end-of-string).  Filter words are
    matched case-insensitively against the header text.

    If *filter_words* is empty or nothing matches, the original *content* is
    returned unchanged.
    """
    if not filter_words:
        return content

    lines = content.split("\n")
    # Collect sections: each entry is (header_line_index, header_level, [lines])
    sections: list[tuple[int, int, list[str]]] = []
    preamble: list[str] = []
    current_section: list[str] | None = None
    current_level = 0

    for line in lines:
        stripped = line.lstrip("#")
        level = len(line) - len(stripped)
        if level > 0 and line.startswith("#"):
            current_section = [line]
            current_level = level
            sections.append((level, current_section))
        elif current_section is not None:
            current_section.append(line)
        else:
            preamble.append(line)

    lower_filters = [w.lower() for w in filter_words]

    matching: list[str] = []
    for level, section_lines in sections:
        header = section_lines[0].lstrip("#").strip().lower()
        if any(f in header for f in lower_filters):
            matching.extend(section_lines)

    if not matching:
        return content

    return "\n".join(matching).strip()


def _condense(markdown: str, max_sections: int = 2) -> str:
    """Condense markdown to the first N sections (## headers)."""
    lines = markdown.split("\n")
    sections_seen = 0
    result = []
    for line in lines:
        if line.startswith("## "):
            sections_seen += 1
            if sections_seen > max_sections:
                break
        result.append(line)
    return "\n".join(result).strip()


def _format_freshness(synced_at: str) -> str:
    """Return a human-readable freshness string for *synced_at* ISO timestamp.

    Format: ``synced: 2025-01-15T10:30:00Z — 2 hours ago``

    Falls back to just the raw timestamp if parsing fails.
    """
    try:
        synced = datetime.fromisoformat(synced_at.replace("Z", "+00:00"))
        now = datetime.now(tz=timezone.utc)
        delta = now - synced
        total_seconds = int(delta.total_seconds())

        if total_seconds < 60:
            ago = f"{total_seconds} seconds ago"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            ago = f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            ago = f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = total_seconds // 86400
            ago = f"{days} day{'s' if days != 1 else ''} ago"

        return f"synced: {synced_at} — {ago}"
    except (ValueError, AttributeError):
        return f"synced: {synced_at}"
