"""Tests for atlas.core.modules."""

import json
import os

import pytest

from atlas.core.modules import (
    PKG_VARIABLES,
    _find_orphaned_tasks,
    install_module,
    remove_module,
    resolve_pkg_variables,
    update_modules,
)


# ---------------------------------------------------------------------------
# PKG_VARIABLES
# ---------------------------------------------------------------------------


class TestPkgVariables:
    def test_exactly_8_entries(self):
        assert len(PKG_VARIABLES) == 8

    def test_expected_managers_present(self):
        expected = {"uv", "pip", "poetry", "pnpm", "npm", "yarn", "bun", "cargo"}
        assert set(PKG_VARIABLES.keys()) == expected

    def test_each_entry_has_four_keys(self):
        required = {"pkg_run", "pkg_add", "pkg_add_dev", "pkg_sync"}
        for name, variables in PKG_VARIABLES.items():
            assert set(variables.keys()) == required, f"{name} missing keys"

    def test_all_values_are_non_empty_strings(self):
        for name, variables in PKG_VARIABLES.items():
            for key, value in variables.items():
                assert isinstance(value, str) and value, f"{name}.{key} is empty"

    def test_uv_pkg_run(self):
        assert PKG_VARIABLES["uv"]["pkg_run"] == "uv run"

    def test_pip_pkg_sync(self):
        assert "requirements" in PKG_VARIABLES["pip"]["pkg_sync"]

    def test_cargo_pkg_add(self):
        assert PKG_VARIABLES["cargo"]["pkg_add"] == "cargo add"


# ---------------------------------------------------------------------------
# resolve_pkg_variables
# ---------------------------------------------------------------------------


class TestResolvePkgVariables:
    def test_uv_pkg_run(self):
        result = resolve_pkg_variables("{{pkg_run}} ruff check .", "uv")
        assert result == "uv run ruff check ."

    def test_pip_pkg_add(self):
        result = resolve_pkg_variables("{{pkg_add}} pytest", "pip")
        assert result == "pip install pytest"

    def test_poetry_pkg_add_dev(self):
        result = resolve_pkg_variables("{{pkg_add_dev}} pytest", "poetry")
        assert result == "poetry add --dev pytest"

    def test_pnpm_pkg_sync(self):
        result = resolve_pkg_variables("{{pkg_sync}}", "pnpm")
        assert result == "pnpm install"

    def test_npm_pkg_run(self):
        result = resolve_pkg_variables("{{pkg_run}} jest", "npm")
        assert result == "npx jest"

    def test_yarn_pkg_add(self):
        result = resolve_pkg_variables("{{pkg_add}} lodash", "yarn")
        assert result == "yarn add lodash"

    def test_bun_pkg_add_dev(self):
        result = resolve_pkg_variables("{{pkg_add_dev}} vitest", "bun")
        assert result == "bun add --dev vitest"

    def test_cargo_pkg_sync(self):
        result = resolve_pkg_variables("{{pkg_sync}}", "cargo")
        assert result == "cargo build"

    def test_unknown_manager_falls_back_to_pip(self):
        result = resolve_pkg_variables("{{pkg_run}} foo", "unknown_manager")
        assert result == "python -m foo"

    def test_unknown_placeholder_left_unchanged(self):
        result = resolve_pkg_variables("{{other_var}} thing", "uv")
        assert result == "{{other_var}} thing"

    def test_multiple_placeholders_in_one_string(self):
        result = resolve_pkg_variables("{{pkg_run}} lint && {{pkg_add}} ruff", "uv")
        assert result == "uv run lint && uv add ruff"

    def test_no_placeholders_returns_unchanged(self):
        text = "ruff check ."
        assert resolve_pkg_variables(text, "uv") == text


# ---------------------------------------------------------------------------
# install_module
# ---------------------------------------------------------------------------


class TestInstallModule:
    def _registry(self, extra_modules=None):
        modules = {
            "ruff": {
                "category": "linter",
                "version": "0.4.0",
                "path": "linters/ruff",
                "conflicts_with": ["flake8"],
            },
            "flake8": {"category": "linter", "version": "7.0.0"},
        }
        if extra_modules:
            modules.update(extra_modules)
        return {"modules": modules}

    def test_happy_path_returns_ok(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        atlas_dir.mkdir()
        manifest = {"installed_modules": {}}
        result = install_module(
            "ruff", self._registry(), str(tmp_path), str(atlas_dir), manifest
        )
        assert result["ok"] is True
        assert result["installed"] == "ruff"

    def test_happy_path_writes_module_json(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        atlas_dir.mkdir()
        manifest = {"installed_modules": {}}
        install_module("ruff", self._registry(), str(tmp_path), str(atlas_dir), manifest)
        assert (atlas_dir / "modules" / "ruff.json").exists()

    def test_happy_path_updates_manifest(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        atlas_dir.mkdir()
        manifest = {"installed_modules": {}}
        install_module("ruff", self._registry(), str(tmp_path), str(atlas_dir), manifest)
        assert "ruff" in manifest["installed_modules"]
        assert manifest["installed_modules"]["ruff"]["category"] == "linter"

    def test_module_not_found_returns_error(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        atlas_dir.mkdir()
        result = install_module(
            "unknown", self._registry(), str(tmp_path), str(atlas_dir),
            {"installed_modules": {}}
        )
        assert result["ok"] is False
        assert result["error"] == "MODULE_NOT_FOUND"

    def test_already_installed_returns_error(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        atlas_dir.mkdir()
        manifest = {"installed_modules": {"ruff": {"category": "linter"}}}
        result = install_module(
            "ruff", self._registry(), str(tmp_path), str(atlas_dir), manifest
        )
        assert result["ok"] is False
        assert result["error"] == "MODULE_ALREADY_INSTALLED"

    def test_conflict_returns_error(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        atlas_dir.mkdir()
        manifest = {"installed_modules": {"flake8": {"category": "linter"}}}
        result = install_module(
            "ruff", self._registry(), str(tmp_path), str(atlas_dir), manifest
        )
        assert result["ok"] is False
        assert result["error"] == "MODULE_CONFLICT"

    def test_pkg_variables_resolved_in_commands(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        (atlas_dir / "modules").mkdir(parents=True)
        # Create a warehouse bundle with a placeholder command.
        bundle_dir = tmp_path / "linters" / "ruff"
        bundle_dir.mkdir(parents=True)
        bundle_data = {
            "id": "ruff",
            "category": "linter",
            "version": "0.4.0",
            "commands": {"check": "{{pkg_run}} ruff check ."},
        }
        (bundle_dir / "module.json").write_text(json.dumps(bundle_data))
        manifest = {"installed_modules": {}}
        install_module(
            "ruff", self._registry(), str(tmp_path), str(atlas_dir),
            manifest, package_manager="uv"
        )
        written = json.loads((atlas_dir / "modules" / "ruff.json").read_text())
        assert written["commands"]["check"] == "uv run ruff check ."

    def test_fallback_bundle_when_no_warehouse_file(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        atlas_dir.mkdir()
        manifest = {"installed_modules": {}}
        install_module("ruff", self._registry(), str(tmp_path), str(atlas_dir), manifest)
        written = json.loads((atlas_dir / "modules" / "ruff.json").read_text())
        assert written["id"] == "ruff"
        assert written["category"] == "linter"

    def test_result_has_warnings_key(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        atlas_dir.mkdir()
        manifest = {"installed_modules": {}}
        result = install_module(
            "ruff", self._registry(), str(tmp_path), str(atlas_dir), manifest
        )
        assert "warnings" in result


# ---------------------------------------------------------------------------
# remove_module
# ---------------------------------------------------------------------------


class TestRemoveModule:
    def _setup(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        mods_dir = atlas_dir / "modules"
        ret_dir = atlas_dir / "retrieve"
        mods_dir.mkdir(parents=True)
        ret_dir.mkdir(parents=True)
        return atlas_dir

    def test_happy_path_returns_ok(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        manifest = {"installed_modules": {"ruff": {"category": "linter"}}}
        result = remove_module("ruff", {}, str(atlas_dir), manifest)
        assert result["ok"] is True
        assert result["removed"] == "ruff"

    def test_removes_from_manifest(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        manifest = {"installed_modules": {"ruff": {"category": "linter"}}}
        remove_module("ruff", {}, str(atlas_dir), manifest)
        assert "ruff" not in manifest["installed_modules"]

    def test_deletes_module_json(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        mod_file = atlas_dir / "modules" / "ruff.json"
        mod_file.write_text("{}")
        manifest = {"installed_modules": {"ruff": {}}}
        remove_module("ruff", {}, str(atlas_dir), manifest)
        assert not mod_file.exists()

    def test_deletes_retrieve_md(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        ret_file = atlas_dir / "retrieve" / "ruff.md"
        ret_file.write_text("# rules")
        manifest = {"installed_modules": {"ruff": {}}}
        remove_module("ruff", {}, str(atlas_dir), manifest)
        assert not ret_file.exists()

    def test_missing_files_silently_skipped(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        manifest = {"installed_modules": {"ruff": {}}}
        result = remove_module("ruff", {}, str(atlas_dir), manifest)
        assert result["ok"] is True

    def test_not_installed_returns_error(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        result = remove_module("ruff", {}, str(atlas_dir), {"installed_modules": {}})
        assert result["ok"] is False
        assert result["error"] == "MODULE_NOT_INSTALLED"

    def test_required_by_dependent_returns_error(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        registry = {"modules": {"django": {"requires": ["python"]}}}
        manifest = {"installed_modules": {"python": {}, "django": {}}}
        result = remove_module("python", registry, str(atlas_dir), manifest)
        assert result["ok"] is False
        assert result["error"] == "MODULE_REQUIRED"

    def test_not_required_can_be_removed(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        registry = {"modules": {"django": {"requires": ["python"]}}}
        manifest = {"installed_modules": {"python": {}, "django": {}}}
        result = remove_module("django", registry, str(atlas_dir), manifest)
        assert result["ok"] is True

    def test_error_detail_names_the_dependent(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        registry = {"modules": {"django": {"requires": ["python"]}}}
        manifest = {"installed_modules": {"python": {}, "django": {}}}
        result = remove_module("python", registry, str(atlas_dir), manifest)
        assert "django" in result["detail"]

    def test_multiple_dependents_all_named_in_detail(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        registry = {
            "modules": {
                "clippy": {"requires": ["rust"]},
                "rustfmt": {"requires": ["rust"]},
            }
        }
        manifest = {"installed_modules": {"rust": {}, "clippy": {}, "rustfmt": {}}}
        result = remove_module("rust", registry, str(atlas_dir), manifest)
        assert result["ok"] is False
        assert "clippy" in result["detail"]
        assert "rustfmt" in result["detail"]

    def test_remove_succeeds_after_dependent_removed(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        registry = {"modules": {"django": {"requires": ["python"]}}}
        manifest = {"installed_modules": {"python": {}}}
        # django already removed from manifest — python can now be removed
        result = remove_module("python", registry, str(atlas_dir), manifest)
        assert result["ok"] is True

    def test_orphaned_task_warning_included_in_result(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        manifest = {"installed_modules": {"ruff": {}}}
        config = {"tasks": {"lint": "uv run ruff check ."}}
        result = remove_module("ruff", {}, str(atlas_dir), manifest, config=config)
        assert result["ok"] is True
        assert "lint" in result["warnings"]

    def test_no_warning_when_task_does_not_reference_module(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        manifest = {"installed_modules": {"ruff": {}}}
        config = {"tasks": {"test": "uv run pytest"}}
        result = remove_module("ruff", {}, str(atlas_dir), manifest, config=config)
        assert result["ok"] is True
        assert result["warnings"] == []

    def test_no_warning_when_no_tasks_in_config(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        manifest = {"installed_modules": {"ruff": {}}}
        result = remove_module("ruff", {}, str(atlas_dir), manifest)
        assert result["ok"] is True
        assert result["warnings"] == []

    def test_chain_task_with_module_reference_warns(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        manifest = {"installed_modules": {"ruff": {}}}
        config = {"tasks": {"quality": ["lint", "uv run ruff format --check ."]}}
        result = remove_module("ruff", {}, str(atlas_dir), manifest, config=config)
        assert "quality" in result["warnings"]


# ---------------------------------------------------------------------------
# _find_orphaned_tasks
# ---------------------------------------------------------------------------


class TestFindOrphanedTasks:
    def test_string_task_with_module_name_is_orphaned(self):
        config = {"tasks": {"lint": "uv run ruff check ."}}
        result = _find_orphaned_tasks("ruff", config)
        assert result == ["lint"]

    def test_string_task_without_module_name_not_orphaned(self):
        config = {"tasks": {"test": "uv run pytest"}}
        result = _find_orphaned_tasks("ruff", config)
        assert result == []

    def test_chain_task_with_module_in_command_is_orphaned(self):
        config = {"tasks": {"quality": ["lint", "uv run ruff format --check ."]}}
        result = _find_orphaned_tasks("ruff", config)
        assert "quality" in result

    def test_multiple_orphaned_tasks_all_returned(self):
        config = {"tasks": {
            "lint": "uv run ruff check .",
            "fmt": "uv run ruff format .",
            "test": "uv run pytest",
        }}
        result = _find_orphaned_tasks("ruff", config)
        assert set(result) == {"lint", "fmt"}

    def test_empty_tasks_returns_empty(self):
        assert _find_orphaned_tasks("ruff", {"tasks": {}}) == []

    def test_no_tasks_key_returns_empty(self):
        assert _find_orphaned_tasks("ruff", {}) == []

    def test_non_dict_tasks_returns_empty(self):
        assert _find_orphaned_tasks("ruff", {"tasks": "bad"}) == []


# ---------------------------------------------------------------------------
# update_modules
# ---------------------------------------------------------------------------


class TestUpdateModules:
    def _setup(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        (atlas_dir / "modules").mkdir(parents=True)
        return atlas_dir

    def test_empty_manifest_returns_empty_lists(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        result = update_modules({}, str(tmp_path), str(atlas_dir), {"installed_modules": {}})
        assert result["ok"] is True
        assert result["updated"] == []
        assert result["skipped"] == []

    def test_same_version_is_skipped(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        registry = {"modules": {"ruff": {"category": "linter", "version": "0.4.0"}}}
        manifest = {"installed_modules": {"ruff": {"version": "0.4.0"}}}
        result = update_modules(registry, str(tmp_path), str(atlas_dir), manifest)
        assert "ruff" in result["skipped"]
        assert "ruff" not in result["updated"]

    def test_newer_warehouse_version_triggers_update(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        registry = {"modules": {"ruff": {"category": "linter", "version": "0.5.0"}}}
        manifest = {"installed_modules": {"ruff": {"version": "0.4.0"}}}
        result = update_modules(registry, str(tmp_path), str(atlas_dir), manifest)
        assert "ruff" in result["updated"]
        assert "ruff" not in result["skipped"]

    def test_updated_module_version_in_manifest(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        registry = {"modules": {"ruff": {"category": "linter", "version": "0.5.0"}}}
        manifest = {"installed_modules": {"ruff": {"version": "0.4.0"}}}
        update_modules(registry, str(tmp_path), str(atlas_dir), manifest)
        assert manifest["installed_modules"]["ruff"]["version"] == "0.5.0"

    def test_updated_module_file_written(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        registry = {"modules": {"ruff": {"category": "linter", "version": "0.5.0"}}}
        manifest = {"installed_modules": {"ruff": {"version": "0.4.0"}}}
        update_modules(registry, str(tmp_path), str(atlas_dir), manifest)
        assert (atlas_dir / "modules" / "ruff.json").exists()

    def test_module_not_in_registry_is_skipped(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        manifest = {"installed_modules": {"ghost": {"version": "1.0.0"}}}
        result = update_modules({}, str(tmp_path), str(atlas_dir), manifest)
        assert "ghost" in result["skipped"]

    def test_warehouse_missing_version_is_skipped(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        registry = {"modules": {"ruff": {"category": "linter"}}}  # no version
        manifest = {"installed_modules": {"ruff": {"version": "0.4.0"}}}
        result = update_modules(registry, str(tmp_path), str(atlas_dir), manifest)
        assert "ruff" in result["skipped"]

    def test_mixed_updates_and_skips(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        registry = {"modules": {
            "ruff":   {"category": "linter",  "version": "0.5.0"},
            "pytest": {"category": "testing", "version": "8.0.0"},
        }}
        manifest = {"installed_modules": {
            "ruff":   {"version": "0.4.0"},  # outdated
            "pytest": {"version": "8.0.0"},  # current
        }}
        result = update_modules(registry, str(tmp_path), str(atlas_dir), manifest)
        assert "ruff" in result["updated"]
        assert "pytest" in result["skipped"]

    def test_result_has_ok_true(self, tmp_path):
        atlas_dir = self._setup(tmp_path)
        result = update_modules({}, str(tmp_path), str(atlas_dir), {"installed_modules": {}})
        assert result["ok"] is True
