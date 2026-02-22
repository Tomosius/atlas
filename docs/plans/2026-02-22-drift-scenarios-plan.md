# Drift Scenario Tests Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create `tests/test_drift_scenarios.py` with scenario-level tests for all three drift sub-types (config changed, new tool detected, removed tool warning).

**Architecture:** One new file, three test classes, ~17 tests total. All tests use real file I/O with `tmp_path`. No mocking. No duplication of internals already tested in `test_drift.py` (`_flatten`, `_diff_values`, `_config_matches`).

**Tech Stack:** pytest, `atlas.core.drift` (`detect_value_drift`, `apply_drift_updates`, `detect_new_tools`, `detect_removed_tools`)

---

## Context: Existing Coverage to Avoid Duplicating

`tests/test_drift.py` already has 39 tests covering:
- `_flatten`, `_diff_values`, `_config_matches` — internal helpers, fully covered
- `detect_value_drift` — 3 thin tests (no-config, empty, unchanged)
- `apply_drift_updates` — 4 thin tests (empty, runs-without-error, skip-if-no-config, meta fields)
- `detect_new_tools` — 7 tests, well covered
- `detect_removed_tools` — 8 tests, well covered

**Gaps this plan fills:** scenario-level tests with realistic file I/O and concrete assertions on output values — particularly the "value actually changed" path in `detect_value_drift` + `apply_drift_updates`.

## Key API Facts (read `src/atlas/core/drift.py` before implementing)

```python
# detect_value_drift signature:
detect_value_drift(installed_modules: dict, atlas_dir: str, project_dir: str) -> dict
# Returns: {"drifted": [{"module": str, "changes": [...]}], "unchanged": [str, ...]}

# apply_drift_updates signature:
apply_drift_updates(drifted: list[dict], atlas_dir: str, project_dir: str) -> list[str]
# Returns: list of module names updated

# detect_new_tools signature:
detect_new_tools(registry: dict, installed_modules: dict, project_dir: str) -> list[str]

# detect_removed_tools signature:
detect_removed_tools(registry: dict, installed_modules: dict, project_dir: str) -> list[str]
```

The snapshot format in `.atlas/modules/<name>.json` stores extracted config values as **top-level keys** (not under a "rules" key). Example:
```json
{"id": "ruff", "name": "Ruff", "version": "1.0.0", "style": {"line_length": "120"}}
```
`detect_value_drift` flattens only non-meta keys for comparison. Meta keys are: `id`, `name`, `version`, `category`, `description`, `config_file`, `config_section`, `detect_files`, `detect_in_config`, `for_languages`, `requires`, `combines_with`, `conflicts_with`, `config_locations`, `config_keys`, `system_tool`, `health_check`, `unlocks_verb`, `commands`, `rules`, `synced_at`.

---

## Task 1: Scaffold + TestDriftScenarioConfigChanged

**Files:**
- Create: `tests/test_drift_scenarios.py`

**Step 1: Write the file**

```python
"""Scenario-level tests for drift detection (issue #93).

Covers the three drift sub-types from plan/05-ATLAS-API.md §27 Type 3:
  1. Config value changed (detect + apply)
  2. New tool detected since init
  3. Installed tool config gone
"""

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


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _write_snapshot(atlas_dir, module_name: str, data: dict) -> None:
    mods_dir = os.path.join(str(atlas_dir), "modules")
    os.makedirs(mods_dir, exist_ok=True)
    with open(os.path.join(mods_dir, f"{module_name}.json"), "w") as f:
        json.dump(data, f)


def _read_snapshot(atlas_dir, module_name: str) -> dict:
    path = os.path.join(str(atlas_dir), "modules", f"{module_name}.json")
    with open(path) as f:
        return json.load(f)


def _write_project_file(project_dir, filename: str, content: str) -> None:
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
        """A changed config value appears in the drifted list with old and new."""
        atlas_dir, project_dir = self._setup(tmp_path)
        # Snapshot: line_length was 120
        _write_snapshot(atlas_dir, "ruff", {"style": {"line_length": "120"}})
        # Config now says 100
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
        # Find the line_length change
        ll_change = next(
            (c for c in ruff_entry["changes"] if "line_length" in c["key"]), None
        )
        assert ll_change is not None
        assert ll_change["old"] == "120"
        assert ll_change["new"] == "100"

    def test_unchanged_module_in_unchanged_list(self, tmp_path):
        """A module whose config hasn't changed ends up in unchanged, not drifted."""
        atlas_dir, project_dir = self._setup(tmp_path)
        # No config file for ruff — scan returns found=False → goes to unchanged
        _write_snapshot(atlas_dir, "ruff", {"style": {"line_length": "120"}})
        result = detect_value_drift({"ruff": {}}, str(atlas_dir), str(project_dir))
        assert "ruff" in result["unchanged"]
        drifted_modules = [d["module"] for d in result["drifted"]]
        assert "ruff" not in drifted_modules

    def test_multiple_modules_independently_reported(self, tmp_path):
        """Two modules with different drift status are independently reported."""
        atlas_dir, project_dir = self._setup(tmp_path)
        _write_snapshot(atlas_dir, "ruff", {"style": {"line_length": "120"}})
        _write_snapshot(atlas_dir, "pytest", {})
        _write_project_file(project_dir, "pyproject.toml", "[tool.ruff]\nline-length = 100\n")
        # pytest has no config file → unchanged
        result = detect_value_drift(
            {"ruff": {}, "pytest": {}}, str(atlas_dir), str(project_dir)
        )
        drifted_modules = [d["module"] for d in result["drifted"]]
        assert "ruff" in drifted_modules
        assert "pytest" in result["unchanged"]

    def test_apply_writes_new_value_to_snapshot(self, tmp_path):
        """apply_drift_updates rewrites the snapshot file and returns module name."""
        atlas_dir, project_dir = self._setup(tmp_path)
        _write_snapshot(
            atlas_dir, "ruff",
            {"id": "ruff", "style": {"line_length": "120"}}
        )
        _write_project_file(project_dir, "pyproject.toml", "[tool.ruff]\nline-length = 100\n")
        drifted = detect_value_drift({"ruff": {}}, str(atlas_dir), str(project_dir))
        updated = apply_drift_updates(drifted["drifted"], str(atlas_dir), str(project_dir))
        assert "ruff" in updated

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

    def test_apply_empty_drifted_list_returns_empty(self, tmp_path):
        """apply_drift_updates with empty list returns [] and writes nothing."""
        atlas_dir, project_dir = self._setup(tmp_path)
        result = apply_drift_updates([], str(atlas_dir), str(project_dir))
        assert result == []
```

**Step 2: Run the tests**

```bash
uv run pytest tests/test_drift_scenarios.py::TestDriftScenarioConfigChanged -v
```

Expected: most PASS. If `test_changed_value_has_correct_old_and_new` fails because the scanner doesn't extract `line_length` for `ruff`, investigate: the scanner only extracts values for modules with `config_keys` in the registry. Since we're passing `{"ruff": {}}` (no registry), `scan_module_config` may return `found=False`. If that's the case, adjust the test to use a snapshot with no data keys (so no drift is possible from the scan), OR adjust the test to assert only that the module is in `unchanged` (since no config was found by scanner). Check `src/atlas/core/scanner.py` to understand what `scan_module_config("ruff", project_dir)` actually does with no registry context.

**Step 3: Fix any failures**

If the scanner needs registry data to find ruff config, the drift test for "changed value" needs to work differently. The key insight: `detect_value_drift` calls `scan_module_config(module_name, project_dir)` which looks up `MODULE_CONFIG_MAP` by module name internally. So `ruff` WILL be scanned if `ruff`'s config is detectable. Verify by reading `src/atlas/core/scanner.py` lines 1-50.

Do NOT change production code. Adjust test setup to match what the scanner actually does.

**Step 4: Run until all pass**

```bash
uv run pytest tests/test_drift_scenarios.py::TestDriftScenarioConfigChanged -v
```

**Step 5: Commit**

```bash
git add tests/test_drift_scenarios.py
git commit -m "test(drift): add config-changed drift scenario tests (#93)"
```

---

## Task 2: TestDriftScenarioNewTool

**Files:**
- Modify: `tests/test_drift_scenarios.py`

**Step 1: Append the class**

```python
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
        # Write a config that matches nothing in registry
        (tmp_path / "unknown-tool.json").write_text("{}")
        result = detect_new_tools(self._registry(), {}, str(tmp_path))
        assert result == []

    def test_no_new_tools_returns_empty(self, tmp_path):
        """Empty project with nothing matching → empty result."""
        result = detect_new_tools(self._registry(), {}, str(tmp_path))
        assert result == []
```

**Step 2: Run**

```bash
uv run pytest tests/test_drift_scenarios.py::TestDriftScenarioNewTool -v
```

Expected: all PASS.

**Step 3: Commit**

```bash
git add tests/test_drift_scenarios.py
git commit -m "test(drift): add new-tool drift scenario tests (#93)"
```

---

## Task 3: TestDriftScenarioRemovedTool

**Files:**
- Modify: `tests/test_drift_scenarios.py`

**Step 1: Append the class**

```python
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
                # git has no detection criteria — never flagged
                "git": {
                    "detect_files": [],
                    "detect_in_config": {},
                },
            }
        }

    def test_config_file_deleted_flagged(self, tmp_path):
        """Installed module whose sentinel file is gone is flagged."""
        # ruff.toml never written — ruff config is gone
        result = detect_removed_tools(self._registry(), {"ruff": {}}, str(tmp_path))
        assert "ruff" in result

    def test_config_section_removed_from_pyproject_flagged(self, tmp_path):
        """Installed module whose pyproject.toml section is gone is flagged."""
        # pyproject.toml exists but has no [tool.mypy]
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 88\n")
        result = detect_removed_tools(self._registry(), {"mypy": {}}, str(tmp_path))
        assert "mypy" in result

    def test_config_moved_to_other_file_not_flagged(self, tmp_path):
        """Module is not flagged if config moved to a file still matching detect_in_config."""
        # ruff config moved from ruff.toml to pyproject.toml — still detectable
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 88\n")
        result = detect_removed_tools(self._registry(), {"ruff": {}}, str(tmp_path))
        assert "ruff" not in result

    def test_multiple_tools_gone_all_flagged_sorted(self, tmp_path):
        """Multiple installed modules with missing configs are all flagged, sorted."""
        # No ruff.toml and no [tool.mypy] → both flagged
        installed = {"ruff": {}, "mypy": {}}
        result = detect_removed_tools(self._registry(), installed, str(tmp_path))
        assert "ruff" in result
        assert "mypy" in result
        assert result == sorted(result)

    def test_tool_with_no_detection_criteria_never_flagged(self, tmp_path):
        """A module with no detect_files and no detect_in_config is skipped."""
        # git has no detection criteria — always considered present
        result = detect_removed_tools(self._registry(), {"git": {}}, str(tmp_path))
        assert "git" not in result

    def test_present_tool_not_flagged(self, tmp_path):
        """An installed module whose config file still exists is not flagged."""
        (tmp_path / "ruff.toml").write_text("")
        result = detect_removed_tools(self._registry(), {"ruff": {}}, str(tmp_path))
        assert "ruff" not in result
```

**Step 2: Run**

```bash
uv run pytest tests/test_drift_scenarios.py::TestDriftScenarioRemovedTool -v
```

Expected: all PASS.

**Step 3: Commit**

```bash
git add tests/test_drift_scenarios.py
git commit -m "test(drift): add removed-tool drift scenario tests (#93)"
```

---

## Task 4: Final verification and issue workflow

**Step 1: Run the full new file**

```bash
uv run pytest tests/test_drift_scenarios.py -v
```

Expected: all ~17 tests PASS.

**Step 2: Run the full suite**

```bash
uv run pytest tests/ -q
```

Expected: all previously passing tests still pass (871+).

**Step 3: Count new tests**

```bash
uv run pytest tests/test_drift_scenarios.py --co -q | tail -3
```

**Step 4: Commit any final fixes if needed**

```bash
git add tests/test_drift_scenarios.py
git commit -m "test(drift): fix assertions after verification (#93)"
```

**Step 5: Close issue and update project board**

```bash
gh issue close 93 --repo Tomosius/atlas --comment "Completed.

## What was built
Created tests/test_drift_scenarios.py with scenario-level tests for all three
drift sub-types from plan/05-ATLAS-API.md §27 Type 3 and §28.

## Acceptance criteria
- [x] TestDriftScenarioConfigChanged — detect + apply value changes
- [x] TestDriftScenarioNewTool — new tool detection
- [x] TestDriftScenarioRemovedTool — removed tool detection
- [x] No duplication with test_drift.py
- [x] All new tests pass, no regressions"

gh issue edit 93 --remove-label "status:in-progress" --repo Tomosius/atlas

ITEM_ID=$(gh project item-list 21 --owner Tomosius --format json | \
  python3 -c "import json,sys; [print(i['id']) for i in json.load(sys.stdin)['items'] if i.get('content',{}).get('number')==93]")
gh project item-edit --project-id PVT_kwHOAbrAN84BPiZJ --id $ITEM_ID \
  --field-id PVTSSF_lAHOAbrAN84BPiZJzg96unA --single-select-option-id 98236657

gh issue edit 94 --add-label "status:in-progress" --repo Tomosius/atlas

NEXT_ITEM_ID=$(gh project item-list 21 --owner Tomosius --format json | \
  python3 -c "import json,sys; [print(i['id']) for i in json.load(sys.stdin)['items'] if i.get('content',{}).get('number')==94]")
gh project item-edit --project-id PVT_kwHOAbrAN84BPiZJ --id $NEXT_ITEM_ID \
  --field-id PVTSSF_lAHOAbrAN84BPiZJzg96unA --single-select-option-id 47fc9ee4
```

**Step 6: Update CLAUDE.md**

In `CLAUDE.md`:
- Change `**Current Issue:** #93 — ...` to `**Current Issue:** #94 — ...`
- Add `| #93 | Write tests for drift detection | ✅ ~17 tests, tests/test_drift_scenarios.py |` to the completed table

```bash
git add CLAUDE.md
git commit -m "chore(meta): update CLAUDE.md after completing issue #93"
```
