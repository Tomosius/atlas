# Design: Session Brief Content (Issue #95)

## What We're Building

Complete `build_session_brief` in `src/atlas/runtime.py` to match the spec
in `plan/05-ATLAS-API.md §24`. The two missing sections are **Recent Activity**
and **Git Status**. Their helpers (`_read_recent_history`, `_quick_git_status`)
are added as stubs returning empty results — filled in by issues #96 and #97.

## Reference

- `plan/05-ATLAS-API.md §24` — full `build_session_brief` spec
- `src/atlas/runtime.py:333` — current implementation (missing two sections)
- `tests/test_runtime.py` — existing `TestBuildSessionBrief` class

## Changes

### `src/atlas/runtime.py`

**Two new private stub methods** (after `build_session_brief`):

```python
def _read_recent_history(self, limit: int = 5) -> list[dict]:
    """Return recent history entries. Implemented in #96."""
    return []

def _quick_git_status(self) -> str:
    """Return a quick git status string. Implemented in #97."""
    return ""
```

**Updated `build_session_brief`** — insert two missing sections after the
active task block and before the notes block:

```python
# Recent activity (from history.jsonl — last 3-5 entries)
history = self._read_recent_history(limit=5)
if history:
    parts.append("\n## Recent Activity")
    for entry in history:
        parts.append(f"  {entry['ago']}: {entry['summary']}")

# Git status (quick subprocess if git installed)
if self.router.has_category_installed("vcs"):
    git_status = self._quick_git_status()
    if git_status:
        parts.append(f"\n## Git Status\n{git_status}")
```

### `tests/test_runtime.py`

Five new tests added to `TestBuildSessionBrief`:

| Test | Asserts |
|---|---|
| `test_recent_activity_section_included_when_history_present` | section appears when `_read_recent_history` returns entries |
| `test_recent_activity_section_omitted_when_history_empty` | no "Recent Activity" when stub returns `[]` |
| `test_git_status_section_included_when_vcs_installed_and_status_present` | section appears when vcs installed + status non-empty |
| `test_git_status_section_omitted_when_no_vcs_installed` | no "Git Status" without vcs category |
| `test_git_status_section_omitted_when_status_empty` | no "Git Status" when `_quick_git_status` returns `""` |

## Acceptance Criteria

- `build_session_brief` matches spec exactly (all 6 sections: header, active task, recent activity, git status, notes, atlas tool)
- `_read_recent_history` and `_quick_git_status` exist as stubs returning empty
- 5 new tests pass
- All existing tests still pass
