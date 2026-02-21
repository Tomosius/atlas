"""Tests for atlas.core.retrieve."""

from __future__ import annotations

import json
import os
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

import pytest

from atlas.core.retrieve import (
    _condense,
    _format_freshness,
    _inject_values,
    _load_module_rules,
    build_all_retrieve_files,
    build_retrieve_file,
    filter_sections,
    build_status_file,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_rules_md(warehouse_dir, path_in_registry, content):
    """Write a rules.md file at the warehouse path."""
    bundle_dir = os.path.join(warehouse_dir, path_in_registry)
    os.makedirs(bundle_dir, exist_ok=True)
    with open(os.path.join(bundle_dir, "rules.md"), "w") as f:
        f.write(content)


def _write_module_json(atlas_dir, module_name, data):
    """Write a .atlas/modules/<name>.json file."""
    mods_dir = os.path.join(atlas_dir, "modules")
    os.makedirs(mods_dir, exist_ok=True)
    with open(os.path.join(mods_dir, f"{module_name}.json"), "w") as f:
        json.dump(data, f)


def _registry(modules=None):
    modules = modules or {}
    return {"modules": modules}


# ---------------------------------------------------------------------------
# _load_module_rules
# ---------------------------------------------------------------------------


class TestLoadModuleRules:
    def test_returns_dict_when_file_exists(self, tmp_path):
        atlas_dir = str(tmp_path)
        _write_module_json(atlas_dir, "ruff", {"id": "ruff", "rules": {"line_length": "88"}})
        result = _load_module_rules("ruff", atlas_dir)
        assert result["id"] == "ruff"

    def test_returns_empty_dict_when_file_missing(self, tmp_path):
        atlas_dir = str(tmp_path)
        os.makedirs(os.path.join(atlas_dir, "modules"), exist_ok=True)
        result = _load_module_rules("nonexistent", atlas_dir)
        assert result == {}

    def test_returns_empty_dict_on_invalid_json(self, tmp_path):
        atlas_dir = str(tmp_path)
        mods_dir = os.path.join(atlas_dir, "modules")
        os.makedirs(mods_dir, exist_ok=True)
        with open(os.path.join(mods_dir, "bad.json"), "w") as f:
            f.write("{ not json }")
        result = _load_module_rules("bad", atlas_dir)
        assert result == {}

    def test_returns_empty_dict_when_modules_dir_missing(self, tmp_path):
        result = _load_module_rules("ruff", str(tmp_path))
        assert result == {}


# ---------------------------------------------------------------------------
# _inject_values
# ---------------------------------------------------------------------------


class TestInjectValues:
    def test_simple_key_replaced(self):
        content = "Line length: {{line_length}}"
        result = _inject_values(content, {"line_length": "88"})
        assert result == "Line length: 88"

    def test_multiple_keys_replaced(self):
        content = "{{a}} and {{b}}"
        result = _inject_values(content, {"a": "foo", "b": "bar"})
        assert result == "foo and bar"

    def test_unknown_placeholder_left_unchanged(self):
        content = "{{unknown}} stuff"
        result = _inject_values(content, {"line_length": "88"})
        assert result == "{{unknown}} stuff"

    def test_nested_dict_uses_dot_notation(self):
        content = "Value: {{section.key}}"
        result = _inject_values(content, {"section": {"key": "42"}})
        assert result == "Value: 42"

    def test_deeply_nested_dict(self):
        content = "{{a.b.c}}"
        result = _inject_values(content, {"a": {"b": {"c": "deep"}}})
        assert result == "deep"

    def test_non_string_value_converted(self):
        content = "Count: {{count}}"
        result = _inject_values(content, {"count": 5})
        assert result == "Count: 5"

    def test_empty_rules_returns_content_unchanged(self):
        content = "# Rules\nNo placeholders."
        result = _inject_values(content, {})
        assert result == content

    def test_empty_content_returns_empty(self):
        result = _inject_values("", {"key": "val"})
        assert result == ""

    def test_prefix_applied_recursively(self):
        content = "{{top.sub}}"
        result = _inject_values(content, {"sub": "val"}, prefix="top")
        assert result == "val"


# ---------------------------------------------------------------------------
# _condense
# ---------------------------------------------------------------------------


class TestCondense:
    def test_returns_first_two_sections_by_default(self):
        md = "# Title\n\n## Section 1\nContent 1\n\n## Section 2\nContent 2\n\n## Section 3\nContent 3"
        result = _condense(md)
        assert "Section 1" in result
        assert "Section 2" in result
        assert "Section 3" not in result

    def test_max_sections_one(self):
        md = "## First\nA\n\n## Second\nB"
        result = _condense(md, max_sections=1)
        assert "First" in result
        assert "Second" not in result

    def test_fewer_sections_than_max_returns_all(self):
        md = "## Only\nContent"
        result = _condense(md, max_sections=5)
        assert "Only" in result
        assert "Content" in result

    def test_empty_string_returns_empty(self):
        assert _condense("") == ""

    def test_no_sections_returns_full_content(self):
        md = "Just a paragraph\nwith no headers"
        assert _condense(md) == md.strip()

    def test_result_is_stripped(self):
        md = "\n\n## Section\nContent\n\n"
        result = _condense(md)
        assert not result.startswith("\n")
        assert not result.endswith("\n")


# ---------------------------------------------------------------------------
# build_retrieve_file
# ---------------------------------------------------------------------------


class TestBuildRetrieveFile:
    def _setup(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        (atlas_dir / "modules").mkdir(parents=True)
        warehouse_dir = tmp_path / "warehouse"
        warehouse_dir.mkdir()
        return str(atlas_dir), str(warehouse_dir)

    def test_returns_rules_md_content(self, tmp_path):
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        reg = _registry({"ruff": {"category": "linter", "path": "linters/ruff"}})
        _write_rules_md(warehouse_dir, "linters/ruff", "# Ruff Rules\nUse ruff.")
        result = build_retrieve_file("ruff", atlas_dir, reg, warehouse_dir, {})
        assert "# Ruff Rules" in result

    def test_returns_empty_string_when_no_rules_md_and_no_module_json(self, tmp_path):
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        reg = _registry({"ruff": {"category": "linter", "path": "linters/ruff"}})
        result = build_retrieve_file("ruff", atlas_dir, reg, warehouse_dir, {})
        assert result == ""

    def test_injects_values_from_module_json(self, tmp_path):
        # Extracted config values are stored at top level in the snapshot
        # e.g. {"style": {"line_length": "120"}} → {{style.line_length}}
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        reg = _registry({"ruff": {"category": "linter", "path": "linters/ruff"}})
        _write_rules_md(warehouse_dir, "linters/ruff", "Line length: {{style.line_length}}")
        _write_module_json(atlas_dir, "ruff", {"style": {"line_length": "120"}})
        result = build_retrieve_file("ruff", atlas_dir, reg, warehouse_dir, {})
        assert "120" in result
        assert "{{style.line_length}}" not in result

    def test_injects_commands_from_snapshot(self, tmp_path):
        # Commands stored in snapshot override warehouse template placeholders
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        reg = _registry({"uv": {"category": "pkg_manager", "path": "pkg-managers/uv"}})
        _write_rules_md(warehouse_dir, "pkg-managers/uv", "Install: {{commands.install}}")
        _write_module_json(atlas_dir, "uv", {"commands": {"install": "uv sync"}})
        result = build_retrieve_file("uv", atlas_dir, reg, warehouse_dir, {})
        assert "uv sync" in result
        assert "{{commands.install}}" not in result

    def test_meta_keys_not_injected_as_placeholders(self, tmp_path):
        # Fields like id, name, version should not be used for placeholder injection
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        reg = _registry({"ruff": {"category": "linter", "path": "linters/ruff"}})
        _write_rules_md(warehouse_dir, "linters/ruff", "Tool: {{id}} Version: {{version}}")
        _write_module_json(atlas_dir, "ruff", {"id": "ruff", "version": "1.0.0", "style": {"line_length": "88"}})
        result = build_retrieve_file("ruff", atlas_dir, reg, warehouse_dir, {})
        # Meta-fields are not injected — placeholders remain unchanged
        assert "{{id}}" in result
        assert "{{version}}" in result

    def test_appends_config_source_when_config_file_set(self, tmp_path):
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        reg = _registry({"ruff": {"category": "linter", "path": "linters/ruff"}})
        _write_rules_md(warehouse_dir, "linters/ruff", "# Rules")
        _write_module_json(atlas_dir, "ruff", {"config_file": "pyproject.toml", "rules": {}})
        result = build_retrieve_file("ruff", atlas_dir, reg, warehouse_dir, {})
        assert "pyproject.toml" in result
        assert "Config source" in result

    def test_no_config_source_line_when_config_file_empty(self, tmp_path):
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        reg = _registry({"ruff": {"category": "linter", "path": "linters/ruff"}})
        _write_rules_md(warehouse_dir, "linters/ruff", "# Rules")
        _write_module_json(atlas_dir, "ruff", {"config_file": "", "rules": {}})
        result = build_retrieve_file("ruff", atlas_dir, reg, warehouse_dir, {})
        assert "Config source" not in result

    def test_appends_linked_module_summary(self, tmp_path):
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        reg = _registry({
            "python": {"category": "language", "path": "languages/python"},
            "ruff": {"category": "linter", "path": "linters/ruff"},
        })
        _write_rules_md(warehouse_dir, "languages/python", "# Python\n\n## Usage\nPython stuff.")
        _write_rules_md(warehouse_dir, "linters/ruff", "## Section 1\nRuff rules.\n\n## Section 2\nMore.\n\n## Section 3\nExtra.")
        installed = {"python": {"category": "language"}, "ruff": {"category": "linter"}}
        config = {"retrieve_links": {"python": ["ruff"]}}
        result = build_retrieve_file("python", atlas_dir, reg, warehouse_dir, installed, config)
        assert "Linked: ruff" in result

    def test_linked_module_condensed_to_two_sections(self, tmp_path):
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        reg = _registry({
            "python": {"category": "language", "path": "languages/python"},
            "ruff": {"category": "linter", "path": "linters/ruff"},
        })
        _write_rules_md(warehouse_dir, "languages/python", "# Python")
        _write_rules_md(
            warehouse_dir, "linters/ruff",
            "## Section 1\nA\n\n## Section 2\nB\n\n## Section 3\nC"
        )
        installed = {"python": {}, "ruff": {}}
        config = {"retrieve_links": {"python": ["ruff"]}}
        result = build_retrieve_file("python", atlas_dir, reg, warehouse_dir, installed, config)
        assert "Section 1" in result
        assert "Section 2" in result
        assert "Section 3" not in result

    def test_linked_module_not_appended_when_not_installed(self, tmp_path):
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        reg = _registry({
            "python": {"category": "language", "path": "languages/python"},
            "ruff": {"category": "linter", "path": "linters/ruff"},
        })
        _write_rules_md(warehouse_dir, "languages/python", "# Python")
        _write_rules_md(warehouse_dir, "linters/ruff", "# Ruff")
        installed = {"python": {}}  # ruff NOT installed
        config = {"retrieve_links": {"python": ["ruff"]}}
        result = build_retrieve_file("python", atlas_dir, reg, warehouse_dir, installed, config)
        assert "Linked: ruff" not in result

    def test_module_not_linked_to_itself(self, tmp_path):
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        reg = _registry({"python": {"category": "language", "path": "languages/python"}})
        _write_rules_md(warehouse_dir, "languages/python", "# Python")
        installed = {"python": {}}
        config = {"retrieve_links": {"python": ["python"]}}
        result = build_retrieve_file("python", atlas_dir, reg, warehouse_dir, installed, config)
        assert result.count("# Python") == 1

    def test_no_retrieve_links_in_config_means_no_linked_sections(self, tmp_path):
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        reg = _registry({
            "python": {"category": "language", "path": "languages/python"},
            "ruff": {"category": "linter", "path": "linters/ruff"},
        })
        _write_rules_md(warehouse_dir, "languages/python", "# Python")
        _write_rules_md(warehouse_dir, "linters/ruff", "# Ruff")
        installed = {"python": {}, "ruff": {}}
        result = build_retrieve_file("python", atlas_dir, reg, warehouse_dir, installed, {})
        assert "Linked:" not in result

    def test_returns_string(self, tmp_path):
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        reg = _registry()
        result = build_retrieve_file("ruff", atlas_dir, reg, warehouse_dir, {})
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# build_status_file
# ---------------------------------------------------------------------------


class TestBuildStatusFile:
    def test_contains_header(self):
        result = build_status_file({}, {})
        assert "# Atlas Project Status" in result

    def test_lists_languages_when_detected(self):
        manifest = {"detected": {"languages": ["python", "typescript"]}}
        result = build_status_file(manifest, {})
        assert "python" in result
        assert "typescript" in result

    def test_lists_stack_when_detected(self):
        manifest = {"detected": {"stack": "python-backend"}}
        result = build_status_file(manifest, {})
        assert "python-backend" in result

    def test_lists_package_manager_when_not_none(self):
        manifest = {"detected": {"package_manager": "uv"}}
        result = build_status_file(manifest, {})
        assert "uv" in result

    def test_package_manager_none_not_shown(self):
        manifest = {"detected": {"package_manager": "none"}}
        result = build_status_file(manifest, {})
        assert "Package Manager" not in result

    def test_installed_modules_section_present(self):
        installed = {"ruff": {"category": "linter"}, "pytest": {"category": "testing"}}
        result = build_status_file({}, installed)
        assert "Installed Modules" in result
        assert "ruff" in result
        assert "pytest" in result

    def test_modules_grouped_by_category(self):
        installed = {
            "ruff": {"category": "linter"},
            "black": {"category": "formatter"},
        }
        result = build_status_file({}, installed)
        assert "linter" in result
        assert "formatter" in result

    def test_retrievable_list_includes_installed_plus_structure_project(self):
        installed = {"ruff": {"category": "linter"}}
        result = build_status_file({}, installed)
        assert "ruff" in result
        assert "structure" in result
        assert "project" in result

    def test_retrievable_list_sorted(self):
        installed = {"zz": {"category": "linter"}, "aa": {"category": "linter"}}
        result = build_status_file({}, installed)
        retrievable_line = [l for l in result.splitlines() if l.startswith("## Retrievable")]
        assert retrievable_line
        # "aa" should appear before "zz" in the sorted list
        line = retrievable_line[0]
        assert line.index("aa") < line.index("zz")

    def test_empty_installed_modules_no_installed_section(self):
        result = build_status_file({}, {})
        assert "Installed Modules" not in result

    def test_no_detected_key_produces_valid_output(self):
        result = build_status_file({}, {})
        assert "# Atlas Project Status" in result

    def test_returns_string(self):
        result = build_status_file({}, {})
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# build_all_retrieve_files
# ---------------------------------------------------------------------------


class TestBuildAllRetrieveFiles:
    def _setup(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        (atlas_dir / "modules").mkdir(parents=True)
        warehouse_dir = tmp_path / "warehouse"
        warehouse_dir.mkdir()
        return str(atlas_dir), str(warehouse_dir)

    def test_returns_list_of_built_modules(self, tmp_path):
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        reg = _registry({"ruff": {"category": "linter", "path": "linters/ruff"}})
        _write_rules_md(warehouse_dir, "linters/ruff", "# Ruff")
        manifest = {"installed_modules": {"ruff": {"category": "linter"}}}
        result = build_all_retrieve_files(atlas_dir, reg, warehouse_dir, manifest)
        assert "ruff" in result

    def test_status_always_built(self, tmp_path):
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        manifest = {"installed_modules": {}}
        result = build_all_retrieve_files(atlas_dir, reg := _registry(), warehouse_dir, manifest)
        assert "_status" in result

    def test_status_file_written_to_disk(self, tmp_path):
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        manifest = {"installed_modules": {}}
        build_all_retrieve_files(atlas_dir, _registry(), warehouse_dir, manifest)
        assert os.path.isfile(os.path.join(atlas_dir, "retrieve", "_status.md"))

    def test_module_file_written_when_content_exists(self, tmp_path):
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        reg = _registry({"ruff": {"category": "linter", "path": "linters/ruff"}})
        _write_rules_md(warehouse_dir, "linters/ruff", "# Ruff Rules")
        manifest = {"installed_modules": {"ruff": {"category": "linter"}}}
        build_all_retrieve_files(atlas_dir, reg, warehouse_dir, manifest)
        assert os.path.isfile(os.path.join(atlas_dir, "retrieve", "ruff.md"))

    def test_module_file_not_written_when_content_empty(self, tmp_path):
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        reg = _registry({"ghost": {"category": "linter"}})  # no path → empty content
        manifest = {"installed_modules": {"ghost": {"category": "linter"}}}
        build_all_retrieve_files(atlas_dir, reg, warehouse_dir, manifest)
        assert not os.path.isfile(os.path.join(atlas_dir, "retrieve", "ghost.md"))
        # ghost should not appear in built list
        result = build_all_retrieve_files(atlas_dir, reg, warehouse_dir, manifest)
        assert "ghost" not in result

    def test_creates_retrieve_dir_if_missing(self, tmp_path):
        atlas_dir = str(tmp_path / ".atlas")
        os.makedirs(atlas_dir)
        warehouse_dir = str(tmp_path / "warehouse")
        os.makedirs(warehouse_dir)
        manifest = {"installed_modules": {}}
        build_all_retrieve_files(atlas_dir, _registry(), warehouse_dir, manifest)
        assert os.path.isdir(os.path.join(atlas_dir, "retrieve"))

    def test_empty_manifest_returns_only_status(self, tmp_path):
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        manifest = {"installed_modules": {}}
        result = build_all_retrieve_files(atlas_dir, _registry(), warehouse_dir, manifest)
        assert result == ["_status"]

    def test_multiple_modules_all_built(self, tmp_path):
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        reg = _registry({
            "ruff": {"category": "linter", "path": "linters/ruff"},
            "pytest": {"category": "testing", "path": "testing/pytest"},
        })
        _write_rules_md(warehouse_dir, "linters/ruff", "# Ruff")
        _write_rules_md(warehouse_dir, "testing/pytest", "# Pytest")
        manifest = {
            "installed_modules": {
                "ruff": {"category": "linter"},
                "pytest": {"category": "testing"},
            }
        }
        result = build_all_retrieve_files(atlas_dir, reg, warehouse_dir, manifest)
        assert "ruff" in result
        assert "pytest" in result
        assert "_status" in result


# ---------------------------------------------------------------------------
# filter_sections
# ---------------------------------------------------------------------------


class TestFilterSections:
    _CONTENT = (
        "# Python Rules\n\n"
        "## Linting\nUse ruff.\n\n"
        "## Testing\nUse pytest.\n\n"
        "## Formatting\nUse black.\n"
    )

    def test_empty_filter_returns_content_unchanged(self):
        result = filter_sections(self._CONTENT, [])
        assert result == self._CONTENT

    def test_matching_filter_returns_only_that_section(self):
        result = filter_sections(self._CONTENT, ["linting"])
        assert "Linting" in result
        assert "Testing" not in result
        assert "Formatting" not in result

    def test_filter_is_case_insensitive(self):
        result = filter_sections(self._CONTENT, ["LINTING"])
        assert "Linting" in result
        assert "Testing" not in result

    def test_partial_word_match(self):
        result = filter_sections(self._CONTENT, ["lint"])
        assert "Linting" in result
        assert "Testing" not in result

    def test_multiple_filter_words_return_all_matching(self):
        result = filter_sections(self._CONTENT, ["linting", "testing"])
        assert "Linting" in result
        assert "Testing" in result
        assert "Formatting" not in result

    def test_no_match_returns_original_content(self):
        result = filter_sections(self._CONTENT, ["nonexistent"])
        assert result == self._CONTENT

    def test_empty_content_returns_empty(self):
        result = filter_sections("", ["linting"])
        assert result == ""

    def test_content_without_sections_and_no_match_returns_original(self):
        content = "Just some prose without any headers."
        result = filter_sections(content, ["linting"])
        assert result == content

    def test_returns_string(self):
        result = filter_sections(self._CONTENT, ["linting"])
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _format_freshness
# ---------------------------------------------------------------------------


class TestFormatFreshness:
    def _fixed_now(self, ts: str):
        """Return a datetime matching *ts* offset by 0 for mock patching."""
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))

    def test_seconds_ago(self):
        ts = "2025-01-15T10:30:00Z"
        now = self._fixed_now(ts) + timedelta(seconds=45)
        with patch("atlas.core.retrieve.datetime") as mock_dt:
            mock_dt.fromisoformat.side_effect = datetime.fromisoformat
            mock_dt.now.return_value = now
            result = _format_freshness(ts)
        assert "45 seconds ago" in result
        assert ts in result

    def test_minutes_ago(self):
        ts = "2025-01-15T10:30:00Z"
        now = self._fixed_now(ts) + timedelta(minutes=5)
        with patch("atlas.core.retrieve.datetime") as mock_dt:
            mock_dt.fromisoformat.side_effect = datetime.fromisoformat
            mock_dt.now.return_value = now
            result = _format_freshness(ts)
        assert "5 minutes ago" in result

    def test_one_minute_singular(self):
        ts = "2025-01-15T10:30:00Z"
        now = self._fixed_now(ts) + timedelta(minutes=1)
        with patch("atlas.core.retrieve.datetime") as mock_dt:
            mock_dt.fromisoformat.side_effect = datetime.fromisoformat
            mock_dt.now.return_value = now
            result = _format_freshness(ts)
        assert "1 minute ago" in result

    def test_hours_ago(self):
        ts = "2025-01-15T10:30:00Z"
        now = self._fixed_now(ts) + timedelta(hours=2)
        with patch("atlas.core.retrieve.datetime") as mock_dt:
            mock_dt.fromisoformat.side_effect = datetime.fromisoformat
            mock_dt.now.return_value = now
            result = _format_freshness(ts)
        assert "2 hours ago" in result

    def test_one_hour_singular(self):
        ts = "2025-01-15T10:30:00Z"
        now = self._fixed_now(ts) + timedelta(hours=1)
        with patch("atlas.core.retrieve.datetime") as mock_dt:
            mock_dt.fromisoformat.side_effect = datetime.fromisoformat
            mock_dt.now.return_value = now
            result = _format_freshness(ts)
        assert "1 hour ago" in result

    def test_days_ago(self):
        ts = "2025-01-15T10:30:00Z"
        now = self._fixed_now(ts) + timedelta(days=3)
        with patch("atlas.core.retrieve.datetime") as mock_dt:
            mock_dt.fromisoformat.side_effect = datetime.fromisoformat
            mock_dt.now.return_value = now
            result = _format_freshness(ts)
        assert "3 days ago" in result

    def test_one_day_singular(self):
        ts = "2025-01-15T10:30:00Z"
        now = self._fixed_now(ts) + timedelta(days=1)
        with patch("atlas.core.retrieve.datetime") as mock_dt:
            mock_dt.fromisoformat.side_effect = datetime.fromisoformat
            mock_dt.now.return_value = now
            result = _format_freshness(ts)
        assert "1 day ago" in result

    def test_contains_synced_prefix(self):
        ts = "2025-01-15T10:30:00Z"
        now = self._fixed_now(ts) + timedelta(hours=1)
        with patch("atlas.core.retrieve.datetime") as mock_dt:
            mock_dt.fromisoformat.side_effect = datetime.fromisoformat
            mock_dt.now.return_value = now
            result = _format_freshness(ts)
        assert result.startswith("synced: ")

    def test_invalid_timestamp_falls_back_gracefully(self):
        result = _format_freshness("not-a-timestamp")
        assert "synced: not-a-timestamp" == result


# ---------------------------------------------------------------------------
# build_retrieve_file — freshness appended
# ---------------------------------------------------------------------------


class TestBuildRetrieveFileFreshness:
    def _setup(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        (atlas_dir / "modules").mkdir(parents=True)
        warehouse_dir = tmp_path / "warehouse"
        warehouse_dir.mkdir()
        return str(atlas_dir), str(warehouse_dir)

    def test_freshness_line_appended_when_synced_at_present(self, tmp_path):
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        reg = _registry({"ruff": {"category": "linter", "path": "linters/ruff"}})
        _write_rules_md(warehouse_dir, "linters/ruff", "# Ruff Rules")
        _write_module_json(atlas_dir, "ruff", {"synced_at": "2025-01-15T10:30:00Z"})
        result = build_retrieve_file("ruff", atlas_dir, reg, warehouse_dir, {})
        assert "synced:" in result
        assert "2025-01-15T10:30:00Z" in result

    def test_no_freshness_line_when_synced_at_absent(self, tmp_path):
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        reg = _registry({"ruff": {"category": "linter", "path": "linters/ruff"}})
        _write_rules_md(warehouse_dir, "linters/ruff", "# Ruff Rules")
        _write_module_json(atlas_dir, "ruff", {"id": "ruff"})
        result = build_retrieve_file("ruff", atlas_dir, reg, warehouse_dir, {})
        assert "synced:" not in result

    def test_synced_at_not_injected_as_placeholder(self, tmp_path):
        atlas_dir, warehouse_dir = self._setup(tmp_path)
        reg = _registry({"ruff": {"category": "linter", "path": "linters/ruff"}})
        _write_rules_md(warehouse_dir, "linters/ruff", "Date: {{synced_at}}")
        _write_module_json(atlas_dir, "ruff", {"synced_at": "2025-01-15T10:30:00Z"})
        result = build_retrieve_file("ruff", atlas_dir, reg, warehouse_dir, {})
        # synced_at is a meta-key — placeholder should remain unchanged
        assert "{{synced_at}}" in result
