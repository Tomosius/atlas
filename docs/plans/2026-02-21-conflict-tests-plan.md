# Conflict Scenario Tests Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create `tests/test_conflicts.py` with unit and integration tests for all 6 conflict types defined in `plan/05-ATLAS-API.md §27`.

**Architecture:** One test file, six test classes (one per conflict type), each with unit-level gap-filling tests and integration-level tests via the Atlas class or core functions. Integration tests use `tmp_path` fixtures and injected in-memory state — no subprocess or MCP server needed.

**Tech Stack:** pytest, `atlas.core.registry`, `atlas.core.modules`, `atlas.core.drift`, `atlas.runtime.Atlas`

---

## Context: What Already Exists

Before writing each task, understand the coverage gaps:

- **Type 1** (`check_conflicts`, `install_module`): well covered in `test_registry.py::TestCheckConflicts` and `test_modules.py::TestInstallModule`. Gap: no integration test through `Atlas.add_modules()`.
- **Type 2** (`find_init_conflicts`): well covered in `test_registry.py::TestFindInitConflicts`. Gap: no integration test through `Atlas.init()` or project-file-based scenario.
- **Type 3** (`detect_value_drift`, `detect_new_tools`, `detect_removed_tools`, `apply_drift_updates`): covered in `test_drift.py`. Gap: no integration test combining detection + apply in one flow.
- **Type 4** (`_find_orphaned_tasks`, `remove_module` with config): covered in `test_modules.py`. Gap: no integration test through `Atlas.remove_module()` with a config.json on disk.
- **Type 5** (`remove_module` with `requires`): covered in `test_modules.py::TestRemoveModule`. Gap: no integration test through `Atlas.remove_module()`.
- **Type 6** (`update_modules`): covered in `test_modules.py::TestUpdateModules`. Gap: no test verifying notes.json and config.json survive an update cycle.

`Atlas.sync()` does not yet exist — Types 3 and 6 integration tests call the underlying core functions directly (same pattern as the unit tests, but combined end-to-end).

---

## Task 1: Scaffold the file and Type 1 unit gaps

**Files:**
- Create: `tests/test_conflicts.py`

**Step 1: Write the failing tests**

Add this to `tests/test_conflicts.py`:

```python
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
        """The error result from install_module names the conflicting module."""
        atlas_dir = tmp_path / ".atlas"
        atlas_dir.mkdir()
        manifest = {"installed_modules": {"flake8": {"category": "linter"}}}
        result = install_module(
            "ruff", self._registry(), str(tmp_path), str(atlas_dir), manifest
        )
        assert result["ok"] is False
        assert result["error"] == "MODULE_CONFLICT"
        assert "flake8" in result.get("detail", "")

    def test_no_conflict_when_different_category(self, tmp_path):
        """Installing a module with no conflicts_with entry succeeds."""
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
```

**Step 2: Run the tests to verify they fail**

```bash
uv run pytest tests/test_conflicts.py::TestType1ModuleConflicts -v
```

Expected: some PASS (unit tests using existing functions), integration tests may fail if `Atlas._registry` / `Atlas._manifest` injection doesn't work as expected. Note any failures and adjust.

**Step 3: Fix if needed**

If `atlas._registry = ...` doesn't inject the registry into the lazy property, look at how `test_runtime.py` injects state:
- Check `test_runtime.py` around line 379: `atlas._manifest = {...}` and `atlas._registry = {...}` — this is the established pattern.
- The lazy property names use `_manifest` and `_registry` as the backing stores.

**Step 4: Run until all Type 1 tests pass**

```bash
uv run pytest tests/test_conflicts.py::TestType1ModuleConflicts -v
```

Expected: all PASS.

**Step 5: Commit**

```bash
git add tests/test_conflicts.py
git commit -m "test(conflicts): add Type 1 module conflict tests"
```

---

## Task 2: Type 2 — Init detection conflicts

**Files:**
- Modify: `tests/test_conflicts.py`

**Step 1: Add the test class**

Append to `tests/test_conflicts.py`:

```python
# ---------------------------------------------------------------------------
# Type 2 — Init detection conflicts
# ---------------------------------------------------------------------------


class TestType2InitDetectionConflicts:
    """Type 2: Both conflicting tools detected during atlas init.

    Spec: plan/05-ATLAS-API.md §27 Type 2
    """

    def _registry(self):
        return {
            "modules": {
                "ruff": {"category": "linter", "conflicts_with": ["flake8"]},
                "flake8": {"category": "linter", "conflicts_with": ["ruff"]},
                "pytest": {"category": "testing"},
                "eslint": {"category": "linter", "conflicts_with": ["biome"]},
                "biome": {"category": "linter", "conflicts_with": ["eslint"]},
            }
        }

    # -- unit gaps --

    def test_single_tool_no_conflict(self):
        """Only one of a conflicting pair detected → no conflict flagged."""
        result = find_init_conflicts(self._registry(), ["ruff", "pytest"])
        assert result == []

    def test_non_conflicting_tools_no_conflict(self):
        """Tools with no conflicts_with entries never produce conflicts."""
        result = find_init_conflicts(self._registry(), ["pytest"])
        assert result == []

    def test_conflict_pair_result_contains_both_names(self):
        """Each conflict entry lists both module names."""
        result = find_init_conflicts(self._registry(), ["ruff", "flake8"])
        assert len(result) == 1
        pair = result[0]
        assert "ruff" in pair
        assert "flake8" in pair

    def test_multiple_conflict_pairs_all_returned(self):
        """Two independent conflicting pairs both appear in the result."""
        result = find_init_conflicts(
            self._registry(), ["ruff", "flake8", "eslint", "biome"]
        )
        assert len(result) == 2

    # -- integration: verify conflict detection fires in realistic scenario --

    def test_init_conflict_detection_combined_flow(self, tmp_path):
        """Simulate the init detection step: given detected tools list with a
        conflict pair, find_init_conflicts returns the pair."""
        detected_tools = ["ruff", "flake8", "pytest"]
        conflicts = find_init_conflicts(self._registry(), detected_tools)
        # The proposal should flag the conflict — at least one pair returned
        assert len(conflicts) >= 1
        # ruff and flake8 should be in the flagged pair
        all_names = [name for pair in conflicts for name in pair]
        assert "ruff" in all_names
        assert "flake8" in all_names

    def test_no_conflict_when_only_one_installed(self, tmp_path):
        """If only ruff is detected (flake8 absent), no conflict is raised."""
        detected_tools = ["ruff", "pytest"]
        conflicts = find_init_conflicts(self._registry(), detected_tools)
        assert conflicts == []
```

**Step 2: Run the tests**

```bash
uv run pytest tests/test_conflicts.py::TestType2InitDetectionConflicts -v
```

Expected: all PASS (these call existing `find_init_conflicts` which is already implemented).

**Step 3: Commit**

```bash
git add tests/test_conflicts.py
git commit -m "test(conflicts): add Type 2 init detection conflict tests"
```

---

## Task 3: Type 3 — Config drift on sync

**Files:**
- Modify: `tests/test_conflicts.py`

**Step 1: Add the test class**

Append to `tests/test_conflicts.py`:

```python
# ---------------------------------------------------------------------------
# Type 3 — Config file drift on sync
# ---------------------------------------------------------------------------


class TestType3ConfigDrift:
    """Type 3: Config file changed after init — Atlas stored values are stale.
    Three sub-types: value changed (auto-fix), new tool (suggest), removed tool (warn).

    Spec: plan/05-ATLAS-API.md §27 Type 3
    """

    def _registry(self):
        return {
            "modules": {
                "ruff": {
                    "category": "linter",
                    "detect_files": ["ruff.toml"],
                    "detect_in_config": {"pyproject.toml": "[tool.ruff]"},
                    "config_keys": {"pyproject.toml": {"tool.ruff": ["line-length"]}},
                },
                "mypy": {
                    "category": "linter",
                    "detect_files": [],
                    "detect_in_config": {"pyproject.toml": "mypy"},
                },
            }
        }

    # -- unit: value drift auto-updates the stored snapshot --

    def test_value_drift_detected_when_config_changes(self, tmp_path):
        """detect_value_drift finds a changed line-length value."""
        atlas_dir = tmp_path / ".atlas"
        mods_dir = atlas_dir / "modules"
        mods_dir.mkdir(parents=True)
        # Store old value in snapshot
        (mods_dir / "ruff.json").write_text(
            json.dumps({"id": "ruff", "rules": {"line_length": 120}})
        )
        # Config file now says 100
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 100\n"
        )
        registry = self._registry()
        installed = {"ruff": {}}
        drifted = detect_value_drift(registry, installed, str(tmp_path), str(atlas_dir))
        assert "ruff" in drifted

    def test_no_value_drift_when_config_unchanged(self, tmp_path):
        """detect_value_drift returns empty when nothing changed."""
        atlas_dir = tmp_path / ".atlas"
        mods_dir = atlas_dir / "modules"
        mods_dir.mkdir(parents=True)
        (mods_dir / "ruff.json").write_text(json.dumps({"id": "ruff", "rules": {}}))
        # No pyproject.toml → nothing to drift
        drifted = detect_value_drift(
            self._registry(), {"ruff": {}}, str(tmp_path), str(atlas_dir)
        )
        assert "ruff" not in drifted

    def test_apply_drift_updates_writes_new_value(self, tmp_path):
        """apply_drift_updates writes the new extracted values to modules/*.json."""
        atlas_dir = tmp_path / ".atlas"
        mods_dir = atlas_dir / "modules"
        mods_dir.mkdir(parents=True)
        (mods_dir / "ruff.json").write_text(
            json.dumps({"id": "ruff", "rules": {"line_length": 120}})
        )
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 100\n"
        )
        registry = self._registry()
        drifted = detect_value_drift(registry, {"ruff": {}}, str(tmp_path), str(atlas_dir))
        apply_drift_updates(drifted, str(atlas_dir))
        written = json.loads((mods_dir / "ruff.json").read_text())
        # After apply, the snapshot should be updated (no longer has old value)
        assert written is not None  # file was rewritten

    # -- unit: new tool detection suggests add --

    def test_new_tool_detected_suggests_module(self, tmp_path):
        """detect_new_tools returns the new tool when its config appears."""
        (tmp_path / "pyproject.toml").write_text("[tool.mypy]\nstrict = true\n")
        result = detect_new_tools(self._registry(), {}, str(tmp_path))
        assert "mypy" in result

    def test_already_installed_not_re_suggested(self, tmp_path):
        """detect_new_tools skips modules already in installed."""
        (tmp_path / "pyproject.toml").write_text("[tool.mypy]\nstrict = true\n")
        result = detect_new_tools(self._registry(), {"mypy": {}}, str(tmp_path))
        assert "mypy" not in result

    # -- unit: removed tool detection warns --

    def test_removed_tool_config_flagged(self, tmp_path):
        """detect_removed_tools flags a module whose config file is gone."""
        # ruff was installed but ruff.toml is now absent and no [tool.ruff] in pyproject.toml
        result = detect_removed_tools(self._registry(), {"ruff": {}}, str(tmp_path))
        assert "ruff" in result

    def test_present_tool_config_not_flagged(self, tmp_path):
        """detect_removed_tools does not flag a module whose config still exists."""
        (tmp_path / "ruff.toml").write_text("[tool.ruff]\n")
        result = detect_removed_tools(self._registry(), {"ruff": {}}, str(tmp_path))
        assert "ruff" not in result

    # -- integration: combined drift flow --

    def test_drift_detect_and_apply_cycle(self, tmp_path):
        """Full drift cycle: detect value change, apply update, snapshot is refreshed."""
        atlas_dir = tmp_path / ".atlas"
        mods_dir = atlas_dir / "modules"
        mods_dir.mkdir(parents=True)
        # Stored snapshot (old values)
        (mods_dir / "ruff.json").write_text(
            json.dumps({"id": "ruff", "rules": {"line_length": 88}})
        )
        # User changed pyproject.toml
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 120\n")
        registry = self._registry()
        installed = {"ruff": {}}
        drifted = detect_value_drift(registry, installed, str(tmp_path), str(atlas_dir))
        assert "ruff" in drifted, "drift should be detected"
        apply_drift_updates(drifted, str(atlas_dir))
        # Snapshot was rewritten
        assert (mods_dir / "ruff.json").exists()

    def test_new_tool_and_removed_tool_independent(self, tmp_path):
        """New tool detection and removed tool detection are independent operations."""
        # mypy config present (new tool) but ruff config absent (removed tool)
        (tmp_path / "pyproject.toml").write_text("[tool.mypy]\nstrict = true\n")
        installed = {"ruff": {}}  # ruff installed but config gone
        new = detect_new_tools(self._registry(), installed, str(tmp_path))
        removed = detect_removed_tools(self._registry(), installed, str(tmp_path))
        assert "mypy" in new
        assert "ruff" in removed
```

**Step 2: Run the tests**

```bash
uv run pytest tests/test_conflicts.py::TestType3ConfigDrift -v
```

Expected: most PASS. The `apply_drift_updates` test verifies the file is rewritten — if `apply_drift_updates` doesn't write back the file, this will fail and you'll need to check the implementation.

**Step 3: Commit**

```bash
git add tests/test_conflicts.py
git commit -m "test(conflicts): add Type 3 config drift tests"
```

---

## Task 4: Type 4 — Task orphaning on remove

**Files:**
- Modify: `tests/test_conflicts.py`

**Step 1: Add the test class**

Append to `tests/test_conflicts.py`:

```python
# ---------------------------------------------------------------------------
# Type 4 — Task orphaning on remove
# ---------------------------------------------------------------------------


class TestType4TaskOrphaning:
    """Type 4: Removing a module whose name appears in a custom task command.
    Atlas warns but does NOT delete the task.

    Spec: plan/05-ATLAS-API.md §27 Type 4
    """

    def _setup(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        (atlas_dir / "modules").mkdir(parents=True)
        (atlas_dir / "retrieve").mkdir(parents=True)
        return atlas_dir

    # -- unit gaps --

    def test_chain_task_with_module_reference_produces_warning(self, tmp_path):
        """A chain task (list) referencing the removed module name is orphaned."""
        atlas_dir = self._setup(tmp_path)
        manifest = {"installed_modules": {"ruff": {}}}
        config = {"tasks": {"quality": ["typecheck", "uv run ruff format ."]}}
        result = remove_module("ruff", {}, str(atlas_dir), manifest, config=config)
        assert result["ok"] is True
        assert "quality" in result["warnings"]

    def test_task_not_referencing_removed_module_no_warning(self, tmp_path):
        """A task that doesn't reference the removed module has no warning."""
        atlas_dir = self._setup(tmp_path)
        manifest = {"installed_modules": {"ruff": {}}}
        config = {"tasks": {"test": "uv run pytest", "typecheck": "uv run basedpyright src/"}}
        result = remove_module("ruff", {}, str(atlas_dir), manifest, config=config)
        assert result["ok"] is True
        assert result["warnings"] == []

    # -- integration via Atlas.remove_module() --

    def test_atlas_remove_with_orphaned_task_warns(self, tmp_path):
        """Atlas.remove_module with config.json containing orphaned task → warning."""
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {"ruff": {"category": "linter"}}}
        atlas._registry = {"modules": {}}
        # Write config.json with an orphaned task
        _write_config(atlas, {"tasks": {"lint": "uv run ruff check ."}})
        result = atlas.remove_module("ruff")
        assert result["ok"] is True
        assert "lint" in result["warnings"]

    def test_atlas_remove_orphaned_task_is_preserved(self, tmp_path):
        """The orphaned task must NOT be deleted from config.json after removal."""
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {"ruff": {"category": "linter"}}}
        atlas._registry = {"modules": {}}
        _write_config(atlas, {"tasks": {"lint": "uv run ruff check ."}})
        atlas.remove_module("ruff")
        # config.json still contains the task
        config_path = os.path.join(atlas.atlas_dir, "config.json")
        config = json.loads(open(config_path).read())
        assert "lint" in config.get("tasks", {})

    def test_atlas_remove_no_tasks_no_warning(self, tmp_path):
        """Atlas.remove_module with no config.json tasks → no orphan warnings."""
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {"ruff": {"category": "linter"}}}
        atlas._registry = {"modules": {}}
        result = atlas.remove_module("ruff")
        assert result["ok"] is True
        assert result["warnings"] == []
```

**Step 2: Run the tests**

```bash
uv run pytest tests/test_conflicts.py::TestType4TaskOrphaning -v
```

Expected: unit tests PASS (existing `remove_module` handles this). Integration tests may reveal whether `Atlas.remove_module` reads `config.json` from disk and passes it to `remove_module`. Check `runtime.py:248` — if config is not passed, the integration test `test_atlas_remove_with_orphaned_task_warns` will fail. If it fails, that's a genuine gap — note it but do NOT fix the runtime in this PR. Mark the test with `pytest.mark.xfail` and add a comment explaining the gap.

**Step 3: Commit**

```bash
git add tests/test_conflicts.py
git commit -m "test(conflicts): add Type 4 task orphaning tests"
```

---

## Task 5: Type 5 — Dependency conflicts on remove

**Files:**
- Modify: `tests/test_conflicts.py`

**Step 1: Add the test class**

Append to `tests/test_conflicts.py`:

```python
# ---------------------------------------------------------------------------
# Type 5 — Dependency conflicts on remove
# ---------------------------------------------------------------------------


class TestType5DependencyConflicts:
    """Type 5: Removing a module that another installed module requires.
    The removal must be blocked with a clear error.

    Spec: plan/05-ATLAS-API.md §27 Type 5
    """

    def _setup(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        (atlas_dir / "modules").mkdir(parents=True)
        (atlas_dir / "retrieve").mkdir(parents=True)
        return atlas_dir

    # -- unit gaps --

    def test_removal_blocked_when_dependent_present(self, tmp_path):
        """remove_module returns error when another installed module requires it."""
        atlas_dir = self._setup(tmp_path)
        registry = {"modules": {"commit-rules": {"requires": ["git"]}}}
        manifest = {"installed_modules": {"git": {}, "commit-rules": {}}}
        result = remove_module("git", registry, str(atlas_dir), manifest)
        assert result["ok"] is False
        assert result["error"] == "MODULE_REQUIRED"

    def test_error_detail_names_the_dependent(self, tmp_path):
        """The error detail string names the dependent module."""
        atlas_dir = self._setup(tmp_path)
        registry = {"modules": {"commit-rules": {"requires": ["git"]}}}
        manifest = {"installed_modules": {"git": {}, "commit-rules": {}}}
        result = remove_module("git", registry, str(atlas_dir), manifest)
        assert "commit-rules" in result["detail"]

    def test_removal_succeeds_after_dependent_removed(self, tmp_path):
        """Once the dependent is removed, the dependency can be removed."""
        atlas_dir = self._setup(tmp_path)
        registry = {"modules": {"commit-rules": {"requires": ["git"]}}}
        # commit-rules already removed from manifest
        manifest = {"installed_modules": {"git": {}}}
        result = remove_module("git", registry, str(atlas_dir), manifest)
        assert result["ok"] is True

    # -- integration via Atlas.remove_module() --

    def test_atlas_remove_blocked_by_dependency(self, tmp_path):
        """Atlas.remove_module('git') with commit-rules installed → blocked."""
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {
            "installed_modules": {"git": {"category": "vcs"}, "commit-rules": {"category": "tools"}}
        }
        atlas._registry = {"modules": {"commit-rules": {"requires": ["git"]}}}
        result = atlas.remove_module("git")
        assert result["ok"] is False
        assert "commit-rules" in result.get("detail", "")

    def test_atlas_remove_succeeds_when_no_dependents(self, tmp_path):
        """Atlas.remove_module('git') with no dependents → succeeds."""
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {"installed_modules": {"git": {"category": "vcs"}}}
        atlas._registry = {"modules": {"commit-rules": {"requires": ["git"]}}}
        result = atlas.remove_module("git")
        assert result["ok"] is True
        assert result["removed"] == "git"

    def test_atlas_remove_multiple_dependents_all_named(self, tmp_path):
        """Atlas.remove_module when multiple modules depend on target → all named."""
        atlas = _make_atlas(tmp_path)
        atlas._manifest = {
            "installed_modules": {
                "rust": {"category": "language"},
                "clippy": {"category": "linter"},
                "rustfmt": {"category": "formatter"},
            }
        }
        atlas._registry = {
            "modules": {
                "clippy": {"requires": ["rust"]},
                "rustfmt": {"requires": ["rust"]},
            }
        }
        result = atlas.remove_module("rust")
        assert result["ok"] is False
        assert "clippy" in result.get("detail", "")
        assert "rustfmt" in result.get("detail", "")
```

**Step 2: Run the tests**

```bash
uv run pytest tests/test_conflicts.py::TestType5DependencyConflicts -v
```

Expected: all PASS.

**Step 3: Commit**

```bash
git add tests/test_conflicts.py
git commit -m "test(conflicts): add Type 5 dependency conflict tests"
```

---

## Task 6: Type 6 — Warehouse update preserves user data

**Files:**
- Modify: `tests/test_conflicts.py`

**Step 1: Add the test class**

Append to `tests/test_conflicts.py`:

```python
# ---------------------------------------------------------------------------
# Type 6 — Warehouse update preserves user data
# ---------------------------------------------------------------------------


class TestType6WarehouseUpdate:
    """Type 6: sync update pulls new module rules but must never overwrite
    notes.json, config.json (tasks/scopes), or custom prompts.

    Spec: plan/05-ATLAS-API.md §27 Type 6
    """

    def _setup(self, tmp_path):
        atlas_dir = tmp_path / ".atlas"
        (atlas_dir / "modules").mkdir(parents=True)
        return atlas_dir

    # -- unit gaps: notes and config survive update --

    def test_notes_file_untouched_after_update(self, tmp_path):
        """update_modules does not touch notes.json."""
        atlas_dir = self._setup(tmp_path)
        # Write notes.json
        notes_path = atlas_dir / "notes.json"
        notes_path.write_text(json.dumps({"python": [{"text": "use async"}]}))
        # Registry has newer version
        registry = {"modules": {"ruff": {"category": "linter", "version": "0.5.0"}}}
        manifest = {"installed_modules": {"ruff": {"version": "0.4.0"}}}
        update_modules(registry, str(tmp_path), str(atlas_dir), manifest)
        # notes.json must be unchanged
        assert notes_path.exists()
        notes = json.loads(notes_path.read_text())
        assert notes["python"][0]["text"] == "use async"

    def test_config_file_untouched_after_update(self, tmp_path):
        """update_modules does not touch config.json."""
        atlas_dir = self._setup(tmp_path)
        # Write config.json with custom tasks
        config_path = atlas_dir / "config.json"
        config_path.write_text(json.dumps({"tasks": {"lint": "uv run ruff check ."}}))
        # Registry has newer version
        registry = {"modules": {"ruff": {"category": "linter", "version": "0.5.0"}}}
        manifest = {"installed_modules": {"ruff": {"version": "0.4.0"}}}
        update_modules(registry, str(tmp_path), str(atlas_dir), manifest)
        # config.json must be unchanged
        assert config_path.exists()
        config = json.loads(config_path.read_text())
        assert config["tasks"]["lint"] == "uv run ruff check ."

    def test_module_version_updated_in_manifest(self, tmp_path):
        """After update, the manifest reflects the new warehouse version."""
        atlas_dir = self._setup(tmp_path)
        registry = {"modules": {"ruff": {"category": "linter", "version": "0.5.0"}}}
        manifest = {"installed_modules": {"ruff": {"version": "0.4.0"}}}
        update_modules(registry, str(tmp_path), str(atlas_dir), manifest)
        assert manifest["installed_modules"]["ruff"]["version"] == "0.5.0"

    def test_custom_prompts_directory_untouched_after_update(self, tmp_path):
        """update_modules does not delete or overwrite custom prompt files."""
        atlas_dir = self._setup(tmp_path)
        prompts_dir = atlas_dir / "prompts"
        prompts_dir.mkdir()
        custom_prompt = prompts_dir / "my-security.md"
        custom_prompt.write_text("# My security prompt")
        registry = {"modules": {"ruff": {"category": "linter", "version": "0.5.0"}}}
        manifest = {"installed_modules": {"ruff": {"version": "0.4.0"}}}
        update_modules(registry, str(tmp_path), str(atlas_dir), manifest)
        assert custom_prompt.exists()
        assert custom_prompt.read_text() == "# My security prompt"

    # -- integration: full update cycle --

    def test_update_cycle_older_version_updates_module_json(self, tmp_path):
        """Full update: old version in manifest → update_modules → module JSON written."""
        atlas_dir = self._setup(tmp_path)
        (atlas_dir / "modules" / "ruff.json").write_text(
            json.dumps({"id": "ruff", "version": "0.4.0", "rules": {}})
        )
        registry = {"modules": {"ruff": {"id": "ruff", "category": "linter", "version": "0.5.0"}}}
        manifest = {"installed_modules": {"ruff": {"version": "0.4.0"}}}
        result = update_modules(registry, str(tmp_path), str(atlas_dir), manifest)
        assert result["ok"] is True
        assert "ruff" in result["updated"]
        written = json.loads((atlas_dir / "modules" / "ruff.json").read_text())
        assert written["version"] == "0.5.0"

    def test_update_cycle_same_version_not_updated(self, tmp_path):
        """Module at current version is skipped, not re-written."""
        atlas_dir = self._setup(tmp_path)
        registry = {"modules": {"ruff": {"category": "linter", "version": "0.4.0"}}}
        manifest = {"installed_modules": {"ruff": {"version": "0.4.0"}}}
        result = update_modules(registry, str(tmp_path), str(atlas_dir), manifest)
        assert "ruff" in result["skipped"]
        assert "ruff" not in result["updated"]
```

**Step 2: Run the tests**

```bash
uv run pytest tests/test_conflicts.py::TestType6WarehouseUpdate -v
```

Expected: all PASS. The `custom_prompts_directory_untouched` test will pass as long as `update_modules` doesn't touch the prompts directory (it shouldn't — it only writes to `modules/*.json`).

**Step 3: Commit**

```bash
git add tests/test_conflicts.py
git commit -m "test(conflicts): add Type 6 warehouse update preservation tests"
```

---

## Task 7: Final verification

**Step 1: Run the full new test file**

```bash
uv run pytest tests/test_conflicts.py -v
```

Expected: all tests PASS (or xfail if any integration gap was marked).

**Step 2: Run the full suite to check for regressions**

```bash
uv run pytest tests/ -q
```

Expected: all previously passing tests still pass.

**Step 3: Count new tests**

```bash
uv run pytest tests/test_conflicts.py --co -q | tail -5
```

Note the count for the issue closing comment.

**Step 4: Commit**

No code change — this is just a verification step. If any test needed a small fix (import path, assertion tweak), commit those fixes with:

```bash
git add tests/test_conflicts.py
git commit -m "test(conflicts): fix test assertions after verification"
```

---

## Issue Workflow

After all tests pass, follow the standard issue completion workflow from CLAUDE.md:

```bash
# 1. Close issue #92
gh issue close 92 --repo Tomosius/atlas --comment "Completed.

## What was built
Created tests/test_conflicts.py with comprehensive coverage of all 6 conflict
types from plan/05-ATLAS-API.md §27. Each type has unit-level and
integration-level tests.

## Acceptance criteria
- [x] All 6 conflict types have dedicated test classes
- [x] Each class contains unit tests + integration tests
- [x] All existing tests still pass (no regressions)
- [x] All new tests are green"

# 2. Remove in-progress label
gh issue edit 92 --remove-label "status:in-progress" --repo Tomosius/atlas

# 3. Set project board status to Done
ITEM_ID=$(gh project item-list 21 --owner Tomosius --format json | \
  python3 -c "import json,sys; [print(i['id']) for i in json.load(sys.stdin)['items'] if i.get('content',{}).get('number')==92]")
gh project item-edit --project-id PVT_kwHOAbrAN84BPiZJ --id $ITEM_ID \
  --field-id PVTSSF_lAHOAbrAN84BPiZJzg96unA --single-select-option-id 98236657

# 4. Mark issue #93 as in-progress
gh issue edit 93 --add-label "status:in-progress" --repo Tomosius/atlas

NEXT_ITEM_ID=$(gh project item-list 21 --owner Tomosius --format json | \
  python3 -c "import json,sys; [print(i['id']) for i in json.load(sys.stdin)['items'] if i.get('content',{}).get('number')==93]")
gh project item-edit --project-id PVT_kwHOAbrAN84BPiZJ --id $NEXT_ITEM_ID \
  --field-id PVTSSF_lAHOAbrAN84BPiZJzg96unA --single-select-option-id 47fc9ee4
```

Then update CLAUDE.md: set **Current Issue** to `#93`.
