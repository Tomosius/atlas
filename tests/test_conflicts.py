"""Tests for all 6 conflict types (05-ATLAS-API.md §27)."""

from __future__ import annotations

import json
import os

import pytest

from atlas.core.drift import (
    apply_drift_updates,
    detect_new_tools,
    detect_removed_tools,
    detect_value_drift,
)
from atlas.core.modules import install_module, remove_module, update_modules
from atlas.core.registry import check_conflicts, find_init_conflicts
from atlas.runtime import Atlas


# ---------------------------------------------------------------------------
# Shared helpers (mirrors test_runtime.py pattern)
# ---------------------------------------------------------------------------


def _make_atlas(tmp_path, initialized: bool = True) -> Atlas:
    """Create an Atlas instance rooted at tmp_path, optionally with .atlas/."""
    atlas = Atlas(project_dir=str(tmp_path))
    if initialized:
        os.makedirs(atlas.atlas_dir, exist_ok=True)
    return atlas


def _write_manifest(atlas: Atlas, data: dict) -> None:
    path = os.path.join(atlas.atlas_dir, "manifest.json")
    with open(path, "w") as f:
        json.dump(data, f)


def _write_module_json(atlas: Atlas, name: str, data: dict) -> None:
    mods_dir = os.path.join(atlas.atlas_dir, "modules")
    os.makedirs(mods_dir, exist_ok=True)
    with open(os.path.join(mods_dir, f"{name}.json"), "w") as f:
        json.dump(data, f)


def _write_notes(atlas: Atlas, data: dict) -> None:
    path = os.path.join(atlas.atlas_dir, "notes.json")
    with open(path, "w") as f:
        json.dump(data, f)


def _write_config(atlas: Atlas, data: dict) -> None:
    path = os.path.join(atlas.atlas_dir, "config.json")
    with open(path, "w") as f:
        json.dump(data, f)


def _read_module_json(atlas: Atlas, name: str) -> dict:
    path = os.path.join(atlas.atlas_dir, "modules", f"{name}.json")
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Type 1 — Module conflicts on add
# ---------------------------------------------------------------------------


class TestType1ModuleConflicts:
    """Type 1: Two modules that cannot coexist (conflicts_with in registry).

    Spec: plan/05-ATLAS-API.md §27 Type 1
    """

    def _registry(self):
        return {
            "modules": {
                "ruff": {"category": "linter", "version": "1.0.0", "conflicts_with": ["flake8"]},
                "flake8": {"category": "linter", "version": "1.0.0", "conflicts_with": ["ruff"]},
                "eslint": {"category": "linter", "version": "1.0.0"},
                "pytest": {"category": "testing", "version": "1.0.0"},
            }
        }

    # -- unit gaps --

    def test_conflict_error_contains_conflicting_module_name(self, tmp_path):
        """The error detail from install_module names the conflicting module."""
        atlas_dir = tmp_path / ".atlas"
        atlas_dir.mkdir()
        manifest = {"installed_modules": {"flake8": {"category": "linter"}}}
        result = install_module(
            "ruff", self._registry(), str(tmp_path), str(atlas_dir), manifest
        )
        assert "flake8" in result["detail"]

    def test_no_conflict_when_different_category(self, tmp_path):
        """Installing a module when no conflict exists between it and installed modules succeeds."""
        atlas_dir = tmp_path / ".atlas"
        (atlas_dir / "modules").mkdir(parents=True)
        manifest = {"installed_modules": {"eslint": {"category": "linter"}}}
        result = install_module(
            "pytest", self._registry(), str(tmp_path), str(atlas_dir), manifest
        )
        assert result["ok"] is True

    # -- integration via Atlas.add_modules() --

    def test_add_conflicting_module_returns_failed_list(self, tmp_path):
        """Atlas.add_modules(['flake8']) with ruff installed → flake8 in failed."""
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {
            "installed_modules": {"ruff": {"category": "linter"}},
            "detected": {},
        }
        atlas._registry = self._registry()
        result = atlas.add_modules(["flake8"])
        assert result["ok"] is True  # the call itself succeeds
        failed_names = [f["name"] for f in result["failed"]]
        assert "flake8" in failed_names

    def test_add_non_conflicting_module_succeeds(self, tmp_path):
        """Atlas.add_modules(['pytest']) with eslint installed → pytest installed."""
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {
            "installed_modules": {"eslint": {"category": "linter"}},
            "detected": {},
        }
        atlas._registry = self._registry()
        result = atlas.add_modules(["pytest"])
        assert "pytest" in result["installed"]
        assert result["failed"] == []

    def test_add_multiple_some_conflict(self, tmp_path):
        """Adding [flake8, pytest] with ruff installed: pytest succeeds, flake8 fails."""
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {
            "installed_modules": {"ruff": {"category": "linter"}},
            "detected": {},
        }
        atlas._registry = self._registry()
        result = atlas.add_modules(["flake8", "pytest"])
        assert "pytest" in result["installed"]
        failed_names = [f["name"] for f in result["failed"]]
        assert "flake8" in failed_names
