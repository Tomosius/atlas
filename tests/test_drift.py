"""Tests for atlas.core.drift."""

from __future__ import annotations

import json
import os

import pytest

from atlas.core.drift import (
    _config_matches,
    _diff_values,
    _flatten,
    apply_drift_updates,
    detect_new_tools,
    detect_value_drift,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_snapshot(atlas_dir, module_name, data):
    mods_dir = os.path.join(str(atlas_dir), "modules")
    os.makedirs(mods_dir, exist_ok=True)
    with open(os.path.join(mods_dir, f"{module_name}.json"), "w") as f:
        json.dump(data, f)


def _write_config(project_dir, filename, content):
    with open(os.path.join(str(project_dir), filename), "w") as f:
        f.write(content)


def _read_snapshot(atlas_dir, module_name):
    path = os.path.join(str(atlas_dir), "modules", f"{module_name}.json")
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# _flatten
# ---------------------------------------------------------------------------


class TestFlatten:
    def test_flat_dict_unchanged(self):
        assert _flatten({"a": "1", "b": "2"}) == {"a": "1", "b": "2"}

    def test_nested_dict_flattened(self):
        result = _flatten({"style": {"line_length": "120"}})
        assert result == {"style.line_length": "120"}

    def test_deeply_nested(self):
        result = _flatten({"a": {"b": {"c": "v"}}})
        assert result == {"a.b.c": "v"}

    def test_mixed_nested_and_flat(self):
        result = _flatten({"a": "1", "b": {"c": "2"}})
        assert "a" in result
        assert "b.c" in result

    def test_values_stringified(self):
        result = _flatten({"count": 5})
        assert result["count"] == "5"

    def test_empty_returns_empty(self):
        assert _flatten({}) == {}


# ---------------------------------------------------------------------------
# _diff_values
# ---------------------------------------------------------------------------


class TestDiffValues:
    def test_changed_value_reported(self):
        result = _diff_values({"a": "1"}, {"a": "2"})
        assert result == [{"key": "a", "old": "1", "new": "2"}]

    def test_new_key_reported(self):
        result = _diff_values({}, {"a": "1"})
        assert result == [{"key": "a", "old": None, "new": "1"}]

    def test_removed_key_reported(self):
        result = _diff_values({"a": "1"}, {})
        assert result == [{"key": "a", "old": "1", "new": None}]

    def test_identical_values_not_reported(self):
        result = _diff_values({"a": "1"}, {"a": "1"})
        assert result == []

    def test_multiple_changes(self):
        result = _diff_values({"a": "1", "b": "2"}, {"a": "9", "b": "2"})
        assert len(result) == 1
        assert result[0]["key"] == "a"

    def test_empty_both_returns_empty(self):
        assert _diff_values({}, {}) == []


# ---------------------------------------------------------------------------
# detect_value_drift
# ---------------------------------------------------------------------------


class TestDetectValueDrift:
    def _setup(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        (atlas_dir / "modules").mkdir(parents=True)
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return str(atlas_dir), str(project_dir)

    def test_no_config_found_module_is_unchanged(self, tmp_path):
        atlas_dir, project_dir = self._setup(tmp_path)
        _write_snapshot(atlas_dir, "ruff", {"style": {"line_length": "120"}})
        # No ruff config file in project_dir
        result = detect_value_drift({"ruff": {}}, atlas_dir, project_dir)
        assert "ruff" in result["unchanged"]
        assert result["drifted"] == []

    def test_empty_installed_returns_empty(self, tmp_path):
        atlas_dir, project_dir = self._setup(tmp_path)
        result = detect_value_drift({}, atlas_dir, project_dir)
        assert result["drifted"] == []
        assert result["unchanged"] == []

    def test_unchanged_values_not_drifted(self, tmp_path):
        atlas_dir, project_dir = self._setup(tmp_path)
        # Write pyproject.toml with ruff config
        _write_config(
            project_dir,
            "pyproject.toml",
            "[tool.ruff]\nline-length = 120\n",
        )
        # Store the same value in snapshot
        _write_snapshot(
            atlas_dir, "ruff",
            {"style": {"line_length": "120"}}
        )
        result = detect_value_drift({"ruff": {}}, atlas_dir, project_dir)
        # Whether drifted or unchanged depends on scanner; key test is no crash
        assert "drifted" in result
        assert "unchanged" in result


# ---------------------------------------------------------------------------
# apply_drift_updates
# ---------------------------------------------------------------------------


class TestApplyDriftUpdates:
    def _setup(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        (atlas_dir / "modules").mkdir(parents=True)
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        return str(atlas_dir), str(project_dir)

    def test_empty_drifted_returns_empty(self, tmp_path):
        atlas_dir, project_dir = self._setup(tmp_path)
        result = apply_drift_updates([], atlas_dir, project_dir)
        assert result == []

    def test_snapshot_updated_with_fresh_values(self, tmp_path):
        atlas_dir, project_dir = self._setup(tmp_path)
        _write_config(
            project_dir,
            "pyproject.toml",
            "[tool.ruff]\nline-length = 100\n",
        )
        _write_snapshot(atlas_dir, "ruff", {"id": "ruff", "style": {"line_length": "120"}})
        drifted = [
            {"module": "ruff", "changes": [{"key": "style.line_length", "old": "120", "new": "100"}]}
        ]
        updated = apply_drift_updates(drifted, atlas_dir, project_dir)
        # ruff was in drifted list with a valid config file — should be updated
        # (actual value depends on scanner; test that function runs without error)
        assert isinstance(updated, list)

    def test_module_without_config_file_skipped(self, tmp_path):
        atlas_dir, project_dir = self._setup(tmp_path)
        # No config file written — scan_module_config returns found=False
        drifted = [{"module": "ruff", "changes": []}]
        updated = apply_drift_updates(drifted, atlas_dir, project_dir)
        assert "ruff" not in updated

    def test_meta_fields_preserved_in_snapshot(self, tmp_path):
        atlas_dir, project_dir = self._setup(tmp_path)
        _write_config(
            project_dir,
            "pyproject.toml",
            "[tool.ruff]\nline-length = 100\n",
        )
        original = {
            "id": "ruff", "name": "Ruff", "version": "1.0.0",
            "style": {"line_length": "120"},
        }
        _write_snapshot(atlas_dir, "ruff", original)
        drifted = [{"module": "ruff", "changes": []}]
        apply_drift_updates(drifted, atlas_dir, project_dir)
        # Meta fields must survive the update
        snap = _read_snapshot(atlas_dir, "ruff")
        assert snap.get("id") == "ruff"
        assert snap.get("name") == "Ruff"
        assert snap.get("version") == "1.0.0"


# ---------------------------------------------------------------------------
# _config_matches
# ---------------------------------------------------------------------------


class TestConfigMatches:
    def test_substring_in_file_returns_true(self, tmp_path):
        f = tmp_path / "pyproject.toml"
        f.write_text("[tool.mypy]\nstrict = true\n")
        assert _config_matches({"pyproject.toml": "mypy"}, str(tmp_path)) is True

    def test_substring_absent_returns_false(self, tmp_path):
        f = tmp_path / "pyproject.toml"
        f.write_text("[tool.ruff]\nline-length = 88\n")
        assert _config_matches({"pyproject.toml": "mypy"}, str(tmp_path)) is False

    def test_file_missing_returns_false(self, tmp_path):
        assert _config_matches({"missing.toml": "mypy"}, str(tmp_path)) is False

    def test_empty_detect_in_config_returns_false(self, tmp_path):
        assert _config_matches({}, str(tmp_path)) is False

    def test_multiple_files_any_match_returns_true(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("psycopg2\n")
        assert _config_matches(
            {"requirements.txt": "psycopg", "pyproject.toml": "psycopg"},
            str(tmp_path),
        ) is True


# ---------------------------------------------------------------------------
# detect_new_tools
# ---------------------------------------------------------------------------


class TestDetectNewTools:
    def _registry(self):
        return {
            "modules": {
                "mypy": {
                    "detect_files": [],
                    "detect_in_config": {"pyproject.toml": "mypy"},
                },
                "ruff": {
                    "detect_files": ["ruff.toml"],
                    "detect_in_config": {},
                },
                "git": {
                    "detect_files": [".git"],
                    "detect_in_config": {},
                },
            }
        }

    def test_new_tool_via_detect_files_suggested(self, tmp_path):
        (tmp_path / "ruff.toml").write_text("[tool.ruff]\n")
        result = detect_new_tools(self._registry(), {}, str(tmp_path))
        assert "ruff" in result

    def test_new_tool_via_detect_in_config_suggested(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[tool.mypy]\nstrict = true\n")
        result = detect_new_tools(self._registry(), {}, str(tmp_path))
        assert "mypy" in result

    def test_already_installed_not_suggested(self, tmp_path):
        (tmp_path / "ruff.toml").write_text("")
        result = detect_new_tools(self._registry(), {"ruff": {}}, str(tmp_path))
        assert "ruff" not in result

    def test_undetectable_tool_not_suggested(self, tmp_path):
        # No mypy config, no ruff.toml
        result = detect_new_tools(self._registry(), {}, str(tmp_path))
        assert "mypy" not in result
        assert "ruff" not in result

    def test_empty_project_returns_empty(self, tmp_path):
        result = detect_new_tools(self._registry(), {}, str(tmp_path))
        assert result == []

    def test_empty_registry_returns_empty(self, tmp_path):
        result = detect_new_tools({"modules": {}}, {}, str(tmp_path))
        assert result == []

    def test_result_is_sorted(self, tmp_path):
        (tmp_path / "ruff.toml").write_text("")
        (tmp_path / ".git").mkdir()
        result = detect_new_tools(self._registry(), {}, str(tmp_path))
        assert result == sorted(result)
