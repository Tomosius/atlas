# Design: Conflict Scenario Tests (Issue #92)

## What We're Building

A dedicated `tests/test_conflicts.py` file that provides comprehensive coverage
of all 6 conflict types documented in `plan/05-ATLAS-API.md §27`. Each type
gets both unit-level gap-filling tests (function-level) and integration-level
tests (Atlas verb-level).

## Reference

- `plan/05-ATLAS-API.md §27` — Conflict Management (6 types)
- `plan/05-ATLAS-API.md §28` — Drift Detection

## File Structure

```
tests/test_conflicts.py
  ├── Helpers (_make_atlas, _write_manifest, _write_module_json, etc.)
  ├── TestType1ModuleConflicts       — on add
  ├── TestType2InitDetectionConflicts — on init
  ├── TestType3ConfigDrift           — on sync (3 sub-types)
  ├── TestType4TaskOrphaning         — on remove
  ├── TestType5DependencyConflicts   — on remove
  └── TestType6WarehouseUpdate       — on sync update
```

## Conflict Types and Test Coverage

### Type 1 — Module Conflicts on `add`

Defined in registry via `conflicts_with`. Two severities: hard block (fully
conflicting) and soft warning (partial overlap, allow with --force).

**Unit gaps to fill:**
- Partial conflict produces a warning, not an error
- `check_conflicts` returns conflict detail including conflicting module name

**Integration tests (Atlas class):**
- `atlas.add_modules(["flake8"])` with ruff installed → `ok=False`, `error="MODULE_CONFLICT"`
- `atlas.add_modules(["biome"])` with eslint installed (partial) → warning in result
- `atlas.add_modules(["ruff"])` with no conflicts → installs successfully

### Type 2 — Init Detection Conflicts

During `atlas init`, both conflicting tools are found in the project's config
files. Atlas flags them in the proposal — doesn't auto-resolve.

**Unit gaps to fill:**
- `find_init_conflicts` with no detected tools returns empty list (already covered; verify)

**Integration tests (Atlas class):**
- `atlas.init()` on tmp project with both `[tool.ruff]` and `.flake8` → result
  contains `conflicts` list with both names

### Type 3 — Config Drift on `sync`

Three sub-types: value changed (auto-fix), new tool detected (suggest), config
removed (warn).

**Unit gaps to fill:**
- Value drift auto-update writes correct value to module JSON
- New tool suggestion includes module name in result
- Removed tool warning includes module name in result

**Integration tests (Atlas class):**
- `atlas.sync()` after changing `line-length` in pyproject.toml → `updated`
  contains ruff, new value reflected in `.atlas/modules/ruff.json`
- `atlas.sync()` after adding `[tool.mypy]` to pyproject.toml → result contains
  suggestion to `atlas add mypy`
- `atlas.sync()` after removing `[tool.ruff]` → result contains warning about
  ruff config gone

### Type 4 — Task Orphaning on `remove`

When removing a module whose name appears in a custom task command, Atlas warns
but does NOT delete the task.

**Unit gaps to fill:**
- Orphaned task detection is case-insensitive (e.g., "Ruff" in command)
- Chain task (array) with module reference is detected

**Integration tests (Atlas class):**
- `atlas.remove_module("ruff")` with custom task `"uv run ruff check ."` →
  `ok=True`, `warnings` includes orphaned task name
- Task is NOT deleted from config after removal (preserved)

### Type 5 — Dependency Conflicts on `remove`

If another installed module declares `requires: ["git"]`, removing `git` is
blocked.

**Unit gaps to fill:**
- Multiple dependents all named in the error detail
- Remove succeeds after the dependent is removed first

**Integration tests (Atlas class):**
- `atlas.remove_module("git")` when `commit-rules` requires `git` →
  `ok=False`, `error="MODULE_REQUIRED_BY"`, detail names `commit-rules`
- After removing `commit-rules`, `atlas.remove_module("git")` → `ok=True`

### Type 6 — Warehouse Update Preserves User Data

`sync update` pulls new module rules from the warehouse but must never
overwrite: notes.json, config.json (tasks, scopes), custom prompts.

**Unit gaps to fill:**
- `update_modules` with newer warehouse version updates module JSON rules
- Notes key in notes.json is preserved after update
- Custom tasks in config.json are preserved after update

**Integration tests (Atlas class):**
- After `sync update`, `notes.json` still contains user notes
- After `sync update`, `config.json` custom tasks still present
- After `sync update`, module version in manifest reflects new warehouse version

## Test Pattern

Integration tests use the same helpers as `test_runtime.py`:

```python
def _make_atlas(tmp_path, initialized=True) -> Atlas:
    atlas = Atlas(project_dir=str(tmp_path))
    if initialized:
        os.makedirs(atlas.atlas_dir, exist_ok=True)
    return atlas
```

State is injected via `_write_manifest`, `_write_module_json`, etc. No real
subprocess or MCP server needed. All tests are self-contained with `tmp_path`.

## Acceptance Criteria

- All 6 conflict types have dedicated test classes in `test_conflicts.py`
- Each class contains at least 2 unit tests + 2 integration tests
- All existing tests still pass (no regressions)
- New tests are all green
