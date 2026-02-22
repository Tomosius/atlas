# Design: Drift Scenario Tests (Issue #93)

## What We're Building

A new `tests/test_drift_scenarios.py` covering the three drift sub-types from
`plan/05-ATLAS-API.md §27 Type 3` and `§28`. Tests are scenario-level —
realistic end-to-end flows using real file I/O, not unit tests of internals.

## Reference

- `plan/05-ATLAS-API.md §27 Type 3` — Config drift (value changed, new tool, removed tool)
- `plan/05-ATLAS-API.md §28` — Drift Detection
- `src/atlas/core/drift.py` — implementation
- `tests/test_drift.py` — existing unit tests (do not duplicate)

## Why a New File

`test_drift.py` already covers the internal helpers (`_flatten`, `_diff_values`,
`_config_matches`) and basic happy-path unit tests. The gaps are scenario-level:
realistic combinations of detect + apply across all three sub-types.

## File Structure

```
tests/test_drift_scenarios.py
  ├── Helpers (_write_snapshot, _write_config, _read_snapshot)
  ├── TestDriftScenarioConfigChanged   — detect + apply value changes
  ├── TestDriftScenarioNewTool         — newly detectable module suggestions
  └── TestDriftScenarioRemovedTool     — installed module config gone
```

## Test Classes

### TestDriftScenarioConfigChanged

Covers the "config changed" sub-type: `detect_value_drift` + `apply_drift_updates`.

Tests:
- `test_changed_value_reported` — pyproject.toml line-length changes → in `drifted` with correct old/new
- `test_multiple_values_changed_all_reported` — two keys changed → two change entries
- `test_value_removed_from_config_reported` — key present in snapshot but gone from config → `new=None`
- `test_new_value_in_config_reported` — new key in config, absent in snapshot → `old=None`
- `test_unchanged_module_in_unchanged_list` — nothing changed → in `unchanged`, not `drifted`
- `test_apply_writes_new_value_to_snapshot` — after apply, snapshot file contains new value
- `test_apply_preserves_meta_fields` — after apply, id/name/version intact in snapshot

### TestDriftScenarioNewTool

Covers the "new tool detected" sub-type: `detect_new_tools`.

Tests:
- `test_new_tool_via_file_detected` — ruff.toml appears → ruff suggested
- `test_new_tool_via_config_section_detected` — [tool.mypy] appears in pyproject.toml → mypy suggested
- `test_multiple_new_tools_all_returned` — two new tool configs → both suggested, sorted
- `test_already_installed_tool_not_suggested` — tool config present but already installed → skipped
- `test_tool_not_in_registry_not_suggested` — config file present but no registry entry → ignored

### TestDriftScenarioRemovedTool

Covers the "removed tool" sub-type: `detect_removed_tools`.

Tests:
- `test_config_file_deleted_flagged` — ruff.toml gone and no pyproject section → flagged
- `test_config_section_removed_flagged` — [tool.ruff] removed from pyproject.toml → flagged
- `test_config_moved_to_other_file_not_flagged` — ruff moved from ruff.toml to pyproject.toml → not flagged
- `test_multiple_tools_gone_all_flagged` — two installed tools both gone → both flagged, sorted
- `test_tool_with_no_detection_criteria_not_flagged` — e.g. git has no detect_files → never flagged

## Acceptance Criteria

- New file `tests/test_drift_scenarios.py` with 3 classes and ~17 tests
- No duplication with `test_drift.py` (no re-testing `_flatten`, `_diff_values`, etc.)
- All new tests pass
- All existing tests still pass (no regressions)
