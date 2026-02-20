"""Configuration hierarchy: project .atlas/config.json > global ~/.atlas/config.json > defaults."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


@dataclass
class AtlasConfig:
    """Atlas configuration with three-level hierarchy."""

    retrieve_links: dict[str, list[str]] = field(default_factory=dict)
    ignore_patterns: list[str] = field(default_factory=list)
    detection_overrides: dict[str, str] = field(default_factory=dict)
    package_manager_override: str = ""
    auto_add_recommendations: bool = False


def load_config(project_dir: str = ".") -> AtlasConfig:
    """Load config with hierarchy: project > global > defaults."""
    config = AtlasConfig()

    # Global config (~/.atlas/config.json)
    global_path = os.path.expanduser("~/.atlas/config.json")
    if os.path.isfile(global_path):
        _merge_config(config, _load_json(global_path))

    # Project config (.atlas/config.json)
    project_config = os.path.join(os.path.abspath(project_dir), ".atlas", "config.json")
    if os.path.isfile(project_config):
        _merge_config(config, _load_json(project_config))

    return config


def save_config(data: dict, path: str) -> None:
    """Save config dict to JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _load_json(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _merge_config(config: AtlasConfig, data: dict) -> None:
    for key, value in data.items():
        if not hasattr(config, key):
            continue
        current = getattr(config, key)
        if isinstance(current, dict) and isinstance(value, dict):
            current.update(value)
        else:
            setattr(config, key, value)
