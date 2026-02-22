"""Scenario-level tests for drift detection (issue #93).

Covers the three drift sub-types from plan/05-ATLAS-API.md §27 Type 3:
  1. Config value changed (detect + apply)
  2. New tool detected since init
  3. Installed tool config gone
"""

from __future__ import annotations

import json
import os

from atlas.core.drift import (
    apply_drift_updates,
    detect_new_tools,
    detect_removed_tools,
    detect_value_drift,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _write_snapshot(atlas_dir, module_name: str, data: dict) -> None:
    """Write a module snapshot JSON to .atlas/modules/<name>.json."""
    mods_dir = os.path.join(str(atlas_dir), "modules")
    os.makedirs(mods_dir, exist_ok=True)
    with open(os.path.join(mods_dir, f"{module_name}.json"), "w") as f:
        json.dump(data, f)


def _read_snapshot(atlas_dir, module_name: str) -> dict:
    """Read a module snapshot JSON from .atlas/modules/<name>.json."""
    path = os.path.join(str(atlas_dir), "modules", f"{module_name}.json")
    with open(path) as f:
        return json.load(f)


def _write_project_file(project_dir, filename: str, content: str) -> None:
    """Write a file into the project directory."""
    with open(os.path.join(str(project_dir), filename), "w") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# Sub-type 1: Config value changed
# ---------------------------------------------------------------------------


class TestDriftScenarioConfigChanged:
    """Scenario: user edits a config file after atlas init.

    detect_value_drift should report the change; apply_drift_updates should
    write the new value back to the snapshot on disk.
    """

    def _setup(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        (atlas_dir / "modules").mkdir(parents=True)
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return atlas_dir, project_dir

    def test_changed_value_in_drifted(self, tmp_path):
        """A changed config value appears in the drifted list."""
        atlas_dir, project_dir = self._setup(tmp_path)
        _write_snapshot(atlas_dir, "ruff", {"style": {"line_length": "120"}})
        _write_project_file(project_dir, "pyproject.toml", "[tool.ruff]\nline-length = 100\n")
        result = detect_value_drift({"ruff": {}}, str(atlas_dir), str(project_dir))
        drifted_modules = [d["module"] for d in result["drifted"]]
        assert "ruff" in drifted_modules

    def test_changed_value_has_correct_old_and_new(self, tmp_path):
        """The change entry records both the old and new value."""
        atlas_dir, project_dir = self._setup(tmp_path)
        _write_snapshot(atlas_dir, "ruff", {"style": {"line_length": "120"}})
        _write_project_file(project_dir, "pyproject.toml", "[tool.ruff]\nline-length = 100\n")
        result = detect_value_drift({"ruff": {}}, str(atlas_dir), str(project_dir))
        ruff_entry = next(d for d in result["drifted"] if d["module"] == "ruff")
        ll_change = next(
            (c for c in ruff_entry["changes"] if "line_length" in c["key"]), None
        )
        assert ll_change is not None
        assert ll_change["old"] == "120"
        assert ll_change["new"] == "100"

    def test_unchanged_module_in_unchanged_list(self, tmp_path):
        """A module with no config file ends up in unchanged, not drifted."""
        atlas_dir, project_dir = self._setup(tmp_path)
        _write_snapshot(atlas_dir, "ruff", {"style": {"line_length": "120"}})
        # No pyproject.toml → scan_module_config returns found=False → unchanged
        result = detect_value_drift({"ruff": {}}, str(atlas_dir), str(project_dir))
        assert "ruff" in result["unchanged"]
        drifted_modules = [d["module"] for d in result["drifted"]]
        assert "ruff" not in drifted_modules

    def test_multiple_values_changed_all_reported(self, tmp_path):
        """Two changed keys on a single module both appear in drifted[0]['changes']."""
        atlas_dir, project_dir = self._setup(tmp_path)
        # Snapshot has line_length=120 and select=["E501"] stored under 'style' and 'lint'
        _write_snapshot(
            atlas_dir, "ruff",
            {"style": {"line_length": "120"}, "extra_setting": "old_value"}
        )
        # Config file changes line_length to 100; extra_setting is a custom key not produced
        # by the scanner, so it will appear as new=None (removed from config perspective).
        # Also line_length changes from 120 to 100.
        _write_project_file(project_dir, "pyproject.toml", "[tool.ruff]\nline-length = 100\n")
        result = detect_value_drift({"ruff": {}}, str(atlas_dir), str(project_dir))
        drifted_modules = [d["module"] for d in result["drifted"]]
        assert "ruff" in drifted_modules
        ruff_entry = next(d for d in result["drifted"] if d["module"] == "ruff")
        change_keys = [c["key"] for c in ruff_entry["changes"]]
        # Both the changed line_length and the missing extra_setting should be reported
        assert any("line_length" in k for k in change_keys)
        assert any("extra_setting" in k for k in change_keys)
        assert len(ruff_entry["changes"]) >= 2

    def test_value_removed_from_config_reported(self, tmp_path):
        """A key in the snapshot but absent from the live config gets new=None."""
        atlas_dir, project_dir = self._setup(tmp_path)
        # Snapshot has a custom key 'extra_setting' the scanner will never produce
        _write_snapshot(atlas_dir, "ruff", {"id": "ruff", "extra_setting": "foo"})
        # Live config has ruff section so scan finds it, but produces only style.line_length
        _write_project_file(project_dir, "pyproject.toml", "[tool.ruff]\nline-length = 88\n")
        result = detect_value_drift({"ruff": {}}, str(atlas_dir), str(project_dir))
        ruff_entry = next((d for d in result["drifted"] if d["module"] == "ruff"), None)
        assert ruff_entry is not None
        removed_change = next(
            (c for c in ruff_entry["changes"] if c["key"] == "extra_setting"), None
        )
        assert removed_change is not None
        assert removed_change["old"] == "foo"
        assert removed_change["new"] is None

    def test_new_value_in_config_reported(self, tmp_path):
        """A key present in the live config but absent from the snapshot gets old=None."""
        atlas_dir, project_dir = self._setup(tmp_path)
        # Snapshot has only meta keys — no data keys at all
        _write_snapshot(atlas_dir, "ruff", {"id": "ruff"})
        # Live config introduces line-length which scanner extracts as style.line_length
        _write_project_file(project_dir, "pyproject.toml", "[tool.ruff]\nline-length = 88\n")
        result = detect_value_drift({"ruff": {}}, str(atlas_dir), str(project_dir))
        ruff_entry = next((d for d in result["drifted"] if d["module"] == "ruff"), None)
        assert ruff_entry is not None
        new_change = next(
            (c for c in ruff_entry["changes"] if "line_length" in c["key"]), None
        )
        assert new_change is not None
        assert new_change["old"] is None
        assert new_change["new"] == "88"

    def test_apply_writes_new_value_to_snapshot(self, tmp_path):
        """apply_drift_updates writes the updated config value back to disk."""
        atlas_dir, project_dir = self._setup(tmp_path)
        _write_snapshot(
            atlas_dir, "ruff",
            {"id": "ruff", "style": {"line_length": "120"}}
        )
        _write_project_file(project_dir, "pyproject.toml", "[tool.ruff]\nline-length = 100\n")
        drifted = detect_value_drift({"ruff": {}}, str(atlas_dir), str(project_dir))
        updated = apply_drift_updates(drifted["drifted"], str(atlas_dir), str(project_dir))
        assert "ruff" in updated
        # Verify the snapshot on disk now contains the new value (stored as int or str)
        snap = _read_snapshot(atlas_dir, "ruff")
        assert str(snap.get("style", {}).get("line_length")) == "100"

    def test_apply_preserves_meta_fields(self, tmp_path):
        """apply_drift_updates never overwrites id, name, version in the snapshot."""
        atlas_dir, project_dir = self._setup(tmp_path)
        _write_snapshot(
            atlas_dir, "ruff",
            {"id": "ruff", "name": "Ruff Linter", "version": "1.0.0",
             "style": {"line_length": "120"}}
        )
        _write_project_file(project_dir, "pyproject.toml", "[tool.ruff]\nline-length = 100\n")
        drifted = detect_value_drift({"ruff": {}}, str(atlas_dir), str(project_dir))
        apply_drift_updates(drifted["drifted"], str(atlas_dir), str(project_dir))
        snap = _read_snapshot(atlas_dir, "ruff")
        assert snap["id"] == "ruff"
        assert snap["name"] == "Ruff Linter"
        assert snap["version"] == "1.0.0"

# ---------------------------------------------------------------------------
# Sub-type 2: New tool detected since init
# ---------------------------------------------------------------------------


class TestDriftScenarioNewTool:
    """Scenario: a new tool config appears in the project after atlas init.

    detect_new_tools should return the module name so the sync handler can
    suggest 'atlas add <name>'.
    """

    def _registry(self):
        return {
            "modules": {
                "mypy": {
                    "detect_files": [],
                    "detect_in_config": {"pyproject.toml": "[tool.mypy]"},
                },
                "ruff": {
                    "detect_files": ["ruff.toml"],
                    "detect_in_config": {"pyproject.toml": "[tool.ruff]"},
                },
                "eslint": {
                    "detect_files": [".eslintrc.json"],
                    "detect_in_config": {},
                },
            }
        }

    def test_new_tool_via_detect_file_suggested(self, tmp_path):
        """A tool whose sentinel file appears is suggested for install."""
        (tmp_path / "ruff.toml").write_text("[tool.ruff]\n")
        result = detect_new_tools(self._registry(), {}, str(tmp_path))
        assert "ruff" in result

    def test_new_tool_via_config_section_suggested(self, tmp_path):
        """A tool whose config section appears in pyproject.toml is suggested."""
        (tmp_path / "pyproject.toml").write_text("[tool.mypy]\nstrict = true\n")
        result = detect_new_tools(self._registry(), {}, str(tmp_path))
        assert "mypy" in result

    def test_multiple_new_tools_all_suggested_sorted(self, tmp_path):
        """Multiple new tool configs → all suggested, result is sorted."""
        (tmp_path / "ruff.toml").write_text("")
        (tmp_path / ".eslintrc.json").write_text("{}")
        result = detect_new_tools(self._registry(), {}, str(tmp_path))
        assert "ruff" in result
        assert "eslint" in result
        assert result == sorted(result)

    def test_already_installed_tool_not_suggested(self, tmp_path):
        """A tool whose config is present but already installed is not suggested."""
        (tmp_path / "ruff.toml").write_text("")
        result = detect_new_tools(self._registry(), {"ruff": {}}, str(tmp_path))
        assert "ruff" not in result

    def test_tool_not_in_registry_not_suggested(self, tmp_path):
        """A config file that doesn't match any registry module is ignored."""
        (tmp_path / "unknown-tool.json").write_text("{}")
        result = detect_new_tools(self._registry(), {}, str(tmp_path))
        assert result == []


# ---------------------------------------------------------------------------
# Sub-type 3: Installed tool config gone
# ---------------------------------------------------------------------------


class TestDriftScenarioRemovedTool:
    """Scenario: an installed module's config file is deleted or moved after init.

    detect_removed_tools flags such modules so the sync handler can warn the user.
    Atlas does NOT auto-remove — the user may have just moved the config.
    """

    def _registry(self):
        return {
            "modules": {
                "ruff": {
                    "detect_files": ["ruff.toml"],
                    "detect_in_config": {"pyproject.toml": "[tool.ruff]"},
                },
                "mypy": {
                    "detect_files": [],
                    "detect_in_config": {"pyproject.toml": "[tool.mypy]"},
                },
                "eslint": {
                    "detect_files": [".eslintrc.json"],
                    "detect_in_config": {},
                },
                "git": {
                    "detect_files": [],
                    "detect_in_config": {},
                },
            }
        }

    def test_config_file_deleted_flagged(self, tmp_path):
        """Installed module whose sentinel file is gone is flagged."""
        result = detect_removed_tools(self._registry(), {"ruff": {}}, str(tmp_path))
        assert "ruff" in result

    def test_config_section_removed_from_pyproject_flagged(self, tmp_path):
        """Installed module whose pyproject.toml section is gone is flagged."""
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 88\n")
        result = detect_removed_tools(self._registry(), {"mypy": {}}, str(tmp_path))
        assert "mypy" in result

    def test_config_moved_to_other_file_not_flagged(self, tmp_path):
        """Module is not flagged if config moved to a file still matching detect_in_config."""
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 88\n")
        result = detect_removed_tools(self._registry(), {"ruff": {}}, str(tmp_path))
        assert "ruff" not in result

    def test_multiple_tools_gone_all_flagged_sorted(self, tmp_path):
        """Multiple installed modules with missing configs are all flagged, sorted."""
        installed = {"ruff": {}, "mypy": {}}
        result = detect_removed_tools(self._registry(), installed, str(tmp_path))
        assert "ruff" in result
        assert "mypy" in result
        assert result == sorted(result)

    def test_tool_with_no_detection_criteria_never_flagged(self, tmp_path):
        """A module with no detect_files and no detect_in_config is never flagged."""
        result = detect_removed_tools(self._registry(), {"git": {}}, str(tmp_path))
        assert "git" not in result
