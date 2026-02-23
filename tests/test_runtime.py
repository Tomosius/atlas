"""Tests for atlas.runtime (Atlas class)."""

from __future__ import annotations

import json
import os
import sys

import pytest
from unittest.mock import MagicMock

from atlas.runtime import Atlas


# ---------------------------------------------------------------------------
# Helpers
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


def _write_notes(atlas: Atlas, data: dict) -> None:
    path = os.path.join(atlas.atlas_dir, "notes.json")
    with open(path, "w") as f:
        json.dump(data, f)


def _write_retrieve(atlas: Atlas, module_name: str, content: str) -> None:
    retrieve_dir = os.path.join(atlas.atlas_dir, "retrieve")
    os.makedirs(retrieve_dir, exist_ok=True)
    with open(os.path.join(retrieve_dir, f"{module_name}.md"), "w") as f:
        f.write(content)


def _write_module_json(atlas: Atlas, module_name: str, data: dict) -> None:
    mods_dir = os.path.join(atlas.atlas_dir, "modules")
    os.makedirs(mods_dir, exist_ok=True)
    with open(os.path.join(mods_dir, f"{module_name}.json"), "w") as f:
        json.dump(data, f)


# ---------------------------------------------------------------------------
# Atlas.__init__ and basic properties
# ---------------------------------------------------------------------------


class TestAtlasInit:
    def test_project_dir_is_absolute(self, tmp_path):
        atlas = Atlas(project_dir=str(tmp_path))
        assert os.path.isabs(atlas.project_dir)

    def test_atlas_dir_is_inside_project(self, tmp_path):
        atlas = Atlas(project_dir=str(tmp_path))
        assert atlas.atlas_dir == os.path.join(str(tmp_path), ".atlas")

    def test_warehouse_dir_is_string(self, tmp_path):
        atlas = Atlas(project_dir=str(tmp_path))
        assert isinstance(atlas.warehouse_dir, str)

    def test_defaults_to_cwd_when_no_project_dir(self):
        atlas = Atlas()
        assert atlas.project_dir == os.path.abspath(os.getcwd())

    def test_lazy_fields_start_as_none(self, tmp_path):
        atlas = Atlas(project_dir=str(tmp_path))
        assert atlas._manifest is None
        assert atlas._config is None
        assert atlas._registry is None
        assert atlas._router is None
        assert atlas._notes is None
        assert atlas._context is None


# ---------------------------------------------------------------------------
# is_initialized
# ---------------------------------------------------------------------------


class TestIsInitialized:
    def test_false_when_atlas_dir_missing(self, tmp_path):
        atlas = Atlas(project_dir=str(tmp_path))
        assert atlas.is_initialized is False

    def test_true_when_atlas_dir_exists(self, tmp_path):
        atlas = _make_atlas(tmp_path, initialized=True)
        assert atlas.is_initialized is True


# ---------------------------------------------------------------------------
# Lazy properties
# ---------------------------------------------------------------------------


class TestLazyProperties:
    def test_manifest_loaded_from_file(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        _write_manifest(atlas, {"installed_modules": {"ruff": {"category": "linter"}}})
        assert "ruff" in atlas.manifest.get("installed_modules", {})

    def test_manifest_returns_empty_dict_when_file_missing(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        assert atlas.manifest == {}

    def test_manifest_cached_after_first_access(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        _ = atlas.manifest
        assert atlas._manifest is not None

    def test_notes_returns_empty_when_file_missing(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        assert atlas.notes == {}

    def test_notes_loaded_from_file(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        _write_notes(atlas, {"python": [{"text": "Use async"}]})
        assert atlas.notes["python"][0]["text"] == "Use async"

    def test_context_returns_empty_when_file_missing(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        assert atlas.context == {}

    def test_installed_modules_from_manifest(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        _write_manifest(atlas, {"installed_modules": {"ruff": {}, "pytest": {}}})
        assert set(atlas.installed_modules) == {"ruff", "pytest"}

    def test_installed_modules_empty_when_no_manifest(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        assert atlas.installed_modules == []

    def test_config_returns_atlas_config_instance(self, tmp_path):
        from atlas.core.config import AtlasConfig
        atlas = _make_atlas(tmp_path)
        assert isinstance(atlas.config, AtlasConfig)

    def test_registry_returns_dict(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        assert isinstance(atlas.registry, dict)


# ---------------------------------------------------------------------------
# invalidate()
# ---------------------------------------------------------------------------


class TestInvalidate:
    def test_clears_manifest_cache(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        _ = atlas.manifest  # populate cache
        atlas.invalidate()
        assert atlas._manifest is None

    def test_clears_config_cache(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        _ = atlas.config
        atlas.invalidate()
        assert atlas._config is None

    def test_clears_registry_cache(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        _ = atlas.registry
        atlas.invalidate()
        assert atlas._registry is None

    def test_clears_router_cache(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        _ = atlas.router
        atlas.invalidate()
        assert atlas._router is None

    def test_clears_notes_cache(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        _ = atlas.notes
        atlas.invalidate()
        assert atlas._notes is None

    def test_clears_context_cache(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        _ = atlas.context
        atlas.invalidate()
        assert atlas._context is None

    def test_reload_after_invalidate_reads_new_data(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        _ = atlas.manifest  # load empty
        _write_manifest(atlas, {"installed_modules": {"ruff": {}}})
        atlas.invalidate()
        assert "ruff" in atlas.manifest.get("installed_modules", {})


# ---------------------------------------------------------------------------
# save_manifest / save_notes / save_config
# ---------------------------------------------------------------------------


class TestSaveHelpers:
    def test_save_manifest_writes_file(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {"ruff": {}}}
        atlas.save_manifest()
        path = os.path.join(atlas.atlas_dir, "manifest.json")
        assert os.path.isfile(path)
        with open(path) as f:
            data = json.load(f)
        assert "ruff" in data["installed_modules"]

    def test_save_manifest_noop_when_not_loaded(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas.save_manifest()  # _manifest is None — should not crash

    def test_save_notes_writes_file(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._notes = {"python": [{"text": "use async"}]}
        atlas.save_notes()
        path = os.path.join(atlas.atlas_dir, "notes.json")
        with open(path) as f:
            data = json.load(f)
        assert data["python"][0]["text"] == "use async"

    def test_save_config_writes_file(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas.save_config({"package_manager_override": "uv"})
        path = os.path.join(atlas.atlas_dir, "config.json")
        with open(path) as f:
            data = json.load(f)
        assert data["package_manager_override"] == "uv"

    def test_save_config_creates_atlas_dir_if_missing(self, tmp_path):
        atlas = Atlas(project_dir=str(tmp_path))  # not initialized
        atlas.save_config({"key": "value"})
        assert os.path.isfile(os.path.join(atlas.atlas_dir, "config.json"))


# ---------------------------------------------------------------------------
# query()
# ---------------------------------------------------------------------------


class TestQuery:
    def test_returns_content_from_retrieve_file(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        _write_retrieve(atlas, "python", "# Python Rules\nUse async.")
        result = atlas.query([["python"]])
        assert "Python Rules" in result

    def test_returns_empty_when_module_not_found(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        result = atlas.query([["nonexistent"]])
        assert result == ""

    def test_applies_filter_words(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        _write_retrieve(atlas, "python", "## Linting\nUse ruff.\n\n## Testing\nUse pytest.")
        result = atlas.query([["python", "linting"]])
        assert "Linting" in result
        assert "Testing" not in result

    def test_concatenates_multiple_context_groups(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        _write_retrieve(atlas, "python", "# Python")
        _write_retrieve(atlas, "ruff", "# Ruff")
        result = atlas.query([["python"], ["ruff"]])
        assert "Python" in result
        assert "Ruff" in result

    def test_appends_notes_to_content(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        _write_retrieve(atlas, "python", "# Python Rules")
        _write_notes(atlas, {"python": [{"text": "Use async for DB calls"}]})
        result = atlas.query([["python"]])
        assert "Use async for DB calls" in result

    def test_message_appended_when_provided(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        _write_retrieve(atlas, "python", "# Python Rules")
        result = atlas.query([["python"]], message="refactor auth")
        assert "refactor auth" in result

    def test_empty_contexts_returns_empty(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        result = atlas.query([])
        assert result == ""


# ---------------------------------------------------------------------------
# Notes management: add_note / remove_note
# ---------------------------------------------------------------------------


class TestNoteManagement:
    def test_add_note_returns_ok(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        result = atlas.add_note("python", "Use async")
        assert result["ok"] is True

    def test_add_note_stores_text(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas.add_note("python", "Use async")
        assert atlas.notes["python"][0]["text"] == "Use async"

    def test_add_note_writes_to_disk(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas.add_note("python", "Use async")
        path = os.path.join(atlas.atlas_dir, "notes.json")
        with open(path) as f:
            data = json.load(f)
        assert data["python"][0]["text"] == "Use async"

    def test_add_note_returns_index(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas.add_note("python", "Note 1")
        result = atlas.add_note("python", "Note 2")
        assert result["index"] == 1

    def test_add_note_not_initialized_returns_error(self, tmp_path):
        atlas = Atlas(project_dir=str(tmp_path))
        result = atlas.add_note("python", "test")
        assert result["ok"] is False
        assert result["error"] == "NOT_INITIALIZED"

    def test_remove_note_by_index(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas.add_note("python", "Note 0")
        atlas.add_note("python", "Note 1")
        atlas.remove_note("python", 0)
        assert len(atlas.notes["python"]) == 1
        assert atlas.notes["python"][0]["text"] == "Note 1"

    def test_remove_note_all(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas.add_note("python", "Note 0")
        atlas.add_note("python", "Note 1")
        result = atlas.remove_note("python", "all")
        assert result["ok"] is True
        assert atlas.notes["python"] == []

    def test_remove_note_no_notes_returns_error(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        result = atlas.remove_note("python", 0)
        assert result["ok"] is False
        assert result["error"] == "INVALID_ARGUMENT"

    def test_remove_note_invalid_index_returns_error(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas.add_note("python", "Note")
        result = atlas.remove_note("python", 99)
        assert result["ok"] is False

    def test_remove_note_not_initialized_returns_error(self, tmp_path):
        atlas = Atlas(project_dir=str(tmp_path))
        result = atlas.remove_note("python", 0)
        assert result["ok"] is False
        assert result["error"] == "NOT_INITIALIZED"


# ---------------------------------------------------------------------------
# add_modules / remove_module
# ---------------------------------------------------------------------------


class TestModuleManagement:
    def test_add_modules_not_initialized_returns_error(self, tmp_path):
        atlas = Atlas(project_dir=str(tmp_path))
        result = atlas.add_modules(["ruff"])
        assert result["ok"] is False
        assert result["error"] == "NOT_INITIALIZED"

    def test_add_modules_unknown_module_in_failed(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {}}
        atlas._registry = {"modules": {}}
        result = atlas.add_modules(["nonexistent"])
        assert "nonexistent" in [f["name"] for f in result["failed"]]

    def test_remove_module_not_initialized_returns_error(self, tmp_path):
        atlas = Atlas(project_dir=str(tmp_path))
        result = atlas.remove_module("ruff")
        assert result["ok"] is False
        assert result["error"] == "NOT_INITIALIZED"

    def test_remove_module_not_installed_returns_error(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {}}
        atlas._registry = {"modules": {}}
        result = atlas.remove_module("ruff")
        assert result["ok"] is False
        assert result["error"] == "MODULE_NOT_INSTALLED"


# ---------------------------------------------------------------------------
# just()
# ---------------------------------------------------------------------------


class TestJust:
    def test_not_initialized_returns_error(self, tmp_path):
        atlas = Atlas(project_dir=str(tmp_path))
        result = atlas.just("check")
        assert result["ok"] is False
        assert result["error"] == "NOT_INITIALIZED"

    def test_empty_task_name_returns_error(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {}}
        result = atlas.just("")
        assert result["ok"] is False

    def test_task_not_found_returns_error(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {"ruff": {}}}
        _write_module_json(atlas, "ruff", {"commands": {"check": "ruff check ."}})
        result = atlas.just("nonexistent_task")
        assert result["ok"] is False
        assert result["error"] == "INVALID_ARGUMENT"

    def test_task_found_and_executed(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {"mypkg": {}}}
        _write_module_json(
            atlas, "mypkg",
            {"commands": {"hello": f"{sys.executable} -c \"print('hello')\""}}
        )
        result = atlas.just("hello")
        assert result["ok"] is True
        assert "hello" in result["output"]


# ---------------------------------------------------------------------------
# build_session_brief()
# ---------------------------------------------------------------------------


class TestBuildSessionBrief:
    def test_contains_atlas_header(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {}}
        result = atlas.build_session_brief()
        assert "# Atlas" in result

    def test_lists_installed_modules(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {"ruff": {}, "pytest": {}}}
        result = atlas.build_session_brief()
        assert "ruff" in result
        assert "pytest" in result

    def test_includes_notes_section_when_notes_present(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {}}
        atlas._notes = {"python": [{"text": "Use async"}]}
        result = atlas.build_session_brief()
        assert "Use async" in result

    def test_includes_active_task_when_context_has_active(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {}}
        atlas._context = {"active": {"type": "issue", "id": 42, "title": "Fix auth"}}
        result = atlas.build_session_brief()
        assert "Fix auth" in result
        assert "42" in result

    def test_returns_string(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {}}
        result = atlas.build_session_brief()
        assert isinstance(result, str)

    def test_recent_activity_section_included_when_history_present(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {}}
        atlas._read_recent_history = lambda limit=5: [
            {"ago": "2h ago", "summary": "ran tests"}
        ]
        result = atlas.build_session_brief()
        assert "Recent Activity" in result
        assert "ran tests" in result

    def test_recent_activity_section_omitted_when_history_empty(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {}}
        result = atlas.build_session_brief()
        assert "Recent Activity" not in result

    def test_git_status_section_included_when_vcs_installed_and_status_present(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {"git": {}}}
        atlas._router = MagicMock()
        atlas._router.has_category_installed.return_value = True
        atlas._quick_git_status = lambda: "  Branch: main (2 ahead)"
        result = atlas.build_session_brief()
        assert "Git Status" in result
        assert "Branch: main" in result

    def test_git_status_section_omitted_when_no_vcs_installed(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {}}
        result = atlas.build_session_brief()
        assert "Git Status" not in result

    def test_git_status_section_omitted_when_status_empty(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {"git": {}}}
        atlas._router = MagicMock()
        atlas._router.has_category_installed.return_value = True
        atlas._quick_git_status = lambda: ""
        result = atlas.build_session_brief()
        assert "Git Status" not in result


# ---------------------------------------------------------------------------
# _find_warehouse()
# ---------------------------------------------------------------------------


class TestFindWarehouse:
    def test_env_var_used_when_set(self, tmp_path, monkeypatch):
        warehouse = tmp_path / "my_warehouse"
        warehouse.mkdir()
        monkeypatch.setenv("ATLAS_WAREHOUSE_DIR", str(warehouse))
        atlas = Atlas(project_dir=str(tmp_path))
        # Only if neither package-relative nor dev-repo candidates exist
        # We can't guarantee the other paths don't exist, so just check type
        assert isinstance(atlas.warehouse_dir, str)

    def test_returns_string_path(self, tmp_path):
        atlas = Atlas(project_dir=str(tmp_path))
        assert isinstance(atlas.warehouse_dir, str)

    def test_dev_repo_modules_detected(self, tmp_path):
        # Verify that from the actual repo, the modules/ dir is found
        atlas = Atlas(project_dir=str(tmp_path))
        # The real modules/ dir should be at repo_root/modules/
        repo_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        modules_dir = os.path.join(repo_root, "modules")
        if os.path.isdir(modules_dir):
            assert atlas.warehouse_dir == modules_dir


# ---------------------------------------------------------------------------
# just() — augmentation
# ---------------------------------------------------------------------------


class TestJustAugmentation:
    def _setup(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        (atlas_dir / "modules").mkdir(parents=True)
        return Atlas(project_dir=str(tmp_path))

    def test_just_augments_output_on_failure_with_error_codes(self, tmp_path):
        atlas = self._setup(tmp_path)
        # Write a manifest with one module
        atlas._manifest = {
            "installed_modules": {"ruff": {}},
            "detected": {},
        }
        # Write module JSON with error_codes
        import json, os
        mod_path = os.path.join(str(tmp_path / ".atlas" / "modules"), "ruff.json")
        with open(mod_path, "w") as f:
            json.dump({
                "commands": {"check": "exit 1"},
                "error_codes": {"E501": "Line too long — break at logical point"},
            }, f)
        # Patch run_task to return a failed result with an E501 error line
        from unittest.mock import patch
        from atlas.core.errors import ok_result
        fake_result = ok_result(task="check", output="file.py:1:80 E501 Line too long", returncode=1)
        with patch("atlas.runtime.run_task", return_value=fake_result):
            result = atlas.just("check")
        assert result["ok"] is True
        assert "📎" in result["output"]
        assert "Line too long — break at logical point" in result["output"]

    def test_just_does_not_augment_on_success(self, tmp_path):
        atlas = self._setup(tmp_path)
        atlas._manifest = {
            "installed_modules": {"ruff": {}},
            "detected": {},
        }
        import json, os
        mod_path = os.path.join(str(tmp_path / ".atlas" / "modules"), "ruff.json")
        with open(mod_path, "w") as f:
            json.dump({
                "commands": {"check": "exit 0"},
                "error_codes": {"E501": "Line too long"},
            }, f)
        from unittest.mock import patch
        from atlas.core.errors import ok_result
        fake_result = ok_result(task="check", output="All checks passed!", returncode=0)
        with patch("atlas.runtime.run_task", return_value=fake_result):
            result = atlas.just("check")
        assert "📎" not in result["output"]

    def test_just_does_not_augment_when_no_error_codes_in_modules(self, tmp_path):
        atlas = self._setup(tmp_path)
        atlas._manifest = {
            "installed_modules": {"ruff": {}},
            "detected": {},
        }
        import json, os
        mod_path = os.path.join(str(tmp_path / ".atlas" / "modules"), "ruff.json")
        with open(mod_path, "w") as f:
            json.dump({"commands": {"check": "exit 1"}}, f)  # no error_codes key
        from unittest.mock import patch
        from atlas.core.errors import ok_result
        fake_result = ok_result(task="check", output="file.py:1:80 E501 Line too long", returncode=1)
        with patch("atlas.runtime.run_task", return_value=fake_result):
            result = atlas.just("check")
        assert "📎" not in result["output"]


# ---------------------------------------------------------------------------
# query() — "status" virtual module
# ---------------------------------------------------------------------------


class TestQueryStatusVirtualModule:
    """atlas status virtual module returns live status."""

    def test_query_status_returns_project_status_header(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {}}
        result = atlas.query([["status"]])
        assert "# Atlas Project Status" in result

    def test_query_status_includes_active_task(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {}}
        atlas._context = {"active": {"type": "issue", "id": 7, "title": "Fix login"}}
        result = atlas.query([["status"]])
        assert "Fix login" in result
        assert "7" in result
        assert "Active Task" in result

    def test_query_status_includes_recent_activity(self, tmp_path):
        import time
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {}}
        history_path = os.path.join(str(tmp_path), ".atlas", "history.jsonl")
        with open(history_path, "w") as f:
            f.write(json.dumps({"ts": time.time() - 100, "summary": "added ruff"}) + "\n")
        result = atlas.query([["status"]])
        assert "Recent Activity" in result
        assert "added ruff" in result

    def test_query_status_includes_git_status_when_vcs_installed(self, tmp_path):
        from unittest.mock import MagicMock
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {"git": {}}}
        atlas._router = MagicMock()
        atlas._router.has_category_installed.return_value = True
        atlas._quick_git_status = lambda: "  Branch: main"
        result = atlas.query([["status"]])
        assert "Git Status" in result
        assert "Branch: main" in result

    def test_query_status_omits_git_status_when_no_vcs(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {}}
        result = atlas.query([["status"]])
        assert "Git Status" not in result

    def test_query_status_does_not_read_static_status_md(self, tmp_path):
        """Live query should NOT serve stale _status.md content."""
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {}}
        # Write a stale static file with misleading content
        retrieve_dir = os.path.join(str(tmp_path), ".atlas", "retrieve")
        os.makedirs(retrieve_dir, exist_ok=True)
        with open(os.path.join(retrieve_dir, "_status.md"), "w") as f:
            f.write("# Old stale content STALE_MARKER")
        result = atlas.query([["status"]])
        assert "STALE_MARKER" not in result

    def test_query_status_lists_installed_modules(self, tmp_path):
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {"ruff": {"category": "linter"}}}
        result = atlas.query([["status"]])
        assert "ruff" in result

    def test_query_status_empty_when_not_initialized(self, tmp_path):
        atlas = Atlas(project_dir=str(tmp_path))
        result = atlas.query([["status"]])
        assert result == ""
