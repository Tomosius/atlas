"""Category contracts and router for Atlas modules."""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Category contracts
# ---------------------------------------------------------------------------

# 13 installable categories — user-facing modules live in one of these.
# Each contract defines:
#   description       Human-readable purpose.
#   required_fields   Fields every module in this category MUST have.
#   optional_fields   Fields that are allowed but not required.
#   expected_commands Commands modules SHOULD provide (used in validation).
#   allows_multiple   Whether more than one module of this category can
#                     coexist in the same project.
CATEGORY_CONTRACTS: dict[str, dict] = {
    "language": {
        "description": "A programming language supported by the project.",
        "required_fields": ["id", "name", "version", "category", "description", "detect_files", "brief"],
        "optional_fields": ["detect_in_config", "detect_deps", "for_languages", "combines_with", "conflicts_with", "requires", "links", "config_locations", "config_keys", "commands", "unlocks_verb"],
        "expected_commands": [],
        "allows_multiple": True,
    },
    "linter": {
        "description": "A static analysis tool that checks code for errors and style issues.",
        "required_fields": ["id", "name", "version", "category", "description", "detect_files", "brief", "for_languages"],
        "optional_fields": ["detect_in_config", "detect_deps", "combines_with", "conflicts_with", "requires", "links", "config_locations", "config_keys", "commands", "unlocks_verb"],
        "expected_commands": ["check"],
        "allows_multiple": False,
    },
    "formatter": {
        "description": "A code formatter that automatically reformats source files.",
        "required_fields": ["id", "name", "version", "category", "description", "detect_files", "brief", "for_languages"],
        "optional_fields": ["detect_in_config", "detect_deps", "combines_with", "conflicts_with", "requires", "links", "config_locations", "config_keys", "commands", "unlocks_verb"],
        "expected_commands": ["fix"],
        "allows_multiple": False,
    },
    "testing": {
        "description": "A testing framework for writing and running tests.",
        "required_fields": ["id", "name", "version", "category", "description", "detect_files", "brief", "for_languages"],
        "optional_fields": ["detect_in_config", "detect_deps", "combines_with", "conflicts_with", "requires", "links", "config_locations", "config_keys", "commands", "unlocks_verb"],
        "expected_commands": ["test"],
        "allows_multiple": False,
    },
    "framework": {
        "description": "A web or application framework that provides structure and conventions.",
        "required_fields": ["id", "name", "version", "category", "description", "detect_files", "brief"],
        "optional_fields": ["detect_in_config", "detect_deps", "for_languages", "combines_with", "conflicts_with", "requires", "links", "config_locations", "config_keys", "commands", "unlocks_verb"],
        "expected_commands": [],
        "allows_multiple": True,
    },
    "database": {
        "description": "A database or data store used by the project.",
        "required_fields": ["id", "name", "version", "category", "description", "detect_files", "brief"],
        "optional_fields": ["detect_in_config", "detect_deps", "for_languages", "combines_with", "conflicts_with", "requires", "links", "config_locations", "config_keys", "commands", "unlocks_verb"],
        "expected_commands": [],
        "allows_multiple": True,
    },
    "vcs": {
        "description": "A version control system managing the project's source history.",
        "required_fields": ["id", "name", "version", "category", "description", "detect_files", "brief"],
        "optional_fields": ["detect_in_config", "detect_deps", "for_languages", "combines_with", "conflicts_with", "requires", "links", "config_locations", "config_keys", "commands", "unlocks_verb"],
        "expected_commands": ["commit", "status", "diff", "log"],
        "allows_multiple": False,
    },
    "platform": {
        "description": "A hosting or collaboration platform (e.g. GitHub, GitLab).",
        "required_fields": ["id", "name", "version", "category", "description", "detect_files", "brief"],
        "optional_fields": ["detect_in_config", "detect_deps", "for_languages", "combines_with", "conflicts_with", "requires", "links", "config_locations", "config_keys", "commands", "unlocks_verb"],
        "expected_commands": [],
        "allows_multiple": False,
    },
    "pkg_manager": {
        "description": "A package manager that installs and manages project dependencies.",
        "required_fields": ["id", "name", "version", "category", "description", "detect_files", "brief"],
        "optional_fields": ["detect_in_config", "detect_deps", "for_languages", "combines_with", "conflicts_with", "requires", "links", "config_locations", "config_keys", "commands", "unlocks_verb"],
        "expected_commands": [],
        "allows_multiple": False,
    },
    "environment": {
        "description": "A runtime or execution environment (e.g. Docker, venv).",
        "required_fields": ["id", "name", "version", "category", "description", "detect_files", "brief"],
        "optional_fields": ["detect_in_config", "detect_deps", "for_languages", "combines_with", "conflicts_with", "requires", "links", "config_locations", "config_keys", "commands", "unlocks_verb"],
        "expected_commands": [],
        "allows_multiple": True,
    },
    "ci_cd": {
        "description": "A continuous integration or delivery pipeline configuration.",
        "required_fields": ["id", "name", "version", "category", "description", "detect_files", "brief"],
        "optional_fields": ["detect_in_config", "detect_deps", "for_languages", "combines_with", "conflicts_with", "requires", "links", "config_locations", "config_keys", "commands", "unlocks_verb"],
        "expected_commands": [],
        "allows_multiple": True,
    },
    "stack": {
        "description": "A named technology stack combining language, framework, and tooling conventions.",
        "required_fields": ["id", "name", "version", "category", "description", "detect_files", "brief"],
        "optional_fields": ["detect_in_config", "detect_deps", "for_languages", "combines_with", "conflicts_with", "requires", "links", "config_locations", "config_keys", "commands", "unlocks_verb"],
        "expected_commands": [],
        "allows_multiple": False,
    },
    "tool": {
        "description": "A standalone development tool that does not fit another category.",
        "required_fields": ["id", "name", "version", "category", "description", "detect_files", "brief"],
        "optional_fields": ["detect_in_config", "detect_deps", "for_languages", "combines_with", "conflicts_with", "requires", "links", "config_locations", "config_keys", "commands", "unlocks_verb"],
        "expected_commands": [],
        "allows_multiple": True,
    },
}

# 2 auto-generated categories — not user-installable; managed internally by Atlas.
AUTO_CATEGORIES: dict[str, dict] = {
    "prompt": {
        "description": "A prompt template that provides a persona or mode for the agent.",
        "required_fields": ["id", "name", "version", "category", "description", "brief"],
        "optional_fields": ["combines_with", "links"],
        "expected_commands": [],
        "allows_multiple": True,
    },
    "runtime": {
        "description": "An internal Atlas runtime module managed automatically.",
        "required_fields": ["id", "name", "version", "category", "description", "brief"],
        "optional_fields": [],
        "expected_commands": [],
        "allows_multiple": True,
    },
}

# Merged view of all categories (installable + auto).
ALL_CATEGORIES: dict[str, dict] = {**CATEGORY_CONTRACTS, **AUTO_CATEGORIES}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def get_valid_categories() -> list[str]:
    """Return all valid category names (installable + auto)."""
    return list(ALL_CATEGORIES.keys())


def is_valid_category(category: str) -> bool:
    """Return True if *category* is a recognised Atlas category."""
    return category in ALL_CATEGORIES


def is_auto_category(category: str) -> bool:
    """Return True if *category* is an auto-generated (non-installable) category."""
    return category in AUTO_CATEGORIES


def get_contract(category: str) -> dict:
    """Return the full contract dict for *category*, or {} if unknown."""
    return ALL_CATEGORIES.get(category, {})


def get_required_fields(category: str) -> list[str]:
    """Return the list of required module fields for *category*."""
    return ALL_CATEGORIES.get(category, {}).get("required_fields", [])


def get_expected_commands(category: str) -> list[str]:
    """Return the list of expected command keys for *category*."""
    return ALL_CATEGORIES.get(category, {}).get("expected_commands", [])
