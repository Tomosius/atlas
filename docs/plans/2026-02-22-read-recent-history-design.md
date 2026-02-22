# Design: Read Recent History (Issue #96)

## What We're Building

Replace the `_read_recent_history` stub in `src/atlas/runtime.py` with a real
implementation that reads the last N entries from `.atlas/history.jsonl`,
computes relative timestamps, and returns `[{"ago": "2h ago", "summary": "..."}]`.

## Reference

- `plan/05-ATLAS-API.md §24` — `_read_recent_history` usage in `build_session_brief`
- `src/atlas/runtime.py:374` — current stub
- Issue #101 will write entries to `history.jsonl`; this issue only reads

## history.jsonl format

One JSON object per line (JSONL), written by #101:
```json
{"ts": 1708600000.0, "summary": "atlas just test → ALL PASSED"}
```

## Changes

### `src/atlas/runtime.py`

Add `import time` to imports (already has `import json` and `import os`).

Replace `_read_recent_history` stub with real implementation. Add
`_relative_time(ts, now)` as a module-level helper (not a method — pure
function, easily testable).

```python
def _relative_time(ts: float, now: float) -> str:
    delta = int(now - ts)
    if delta < 60:
        return "just now"
    if delta < 3600:
        return f"{delta // 60}m ago"
    if delta < 86400:
        return f"{delta // 3600}h ago"
    return f"{delta // 86400}d ago"
```

```python
def _read_recent_history(self, limit: int = 5) -> list[dict]:
    path = os.path.join(self.atlas_dir, "history.jsonl")
    if not os.path.isfile(path):
        return []
    try:
        with open(path) as f:
            lines = [l.strip() for l in f if l.strip()]
    except OSError:
        return []
    now = time.time()
    entries = []
    for line in lines[-limit:]:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        summary = record.get("summary", "")
        if not summary:
            continue
        ts = record.get("ts")
        ago = _relative_time(ts, now) if ts is not None else "?"
        entries.append({"ago": ago, "summary": summary})
    return entries
```

### `tests/test_history.py` (new file)

**`TestRelativeTime`** — unit tests for `_relative_time`:
- `test_just_now` — delta < 60 → "just now"
- `test_minutes_ago` — 90s → "1m ago"
- `test_hours_ago` — 7200s → "2h ago"
- `test_days_ago` — 172800s → "2d ago"
- `test_boundary_one_hour` — 3600s → "1h ago"

**`TestReadRecentHistory`** — scenario tests with real file I/O:
- `test_returns_empty_when_no_file` — no file → `[]`
- `test_returns_entries_in_order` — 3 entries → all 3, oldest first
- `test_respects_limit` — 10 entries, limit=3 → last 3
- `test_skips_malformed_lines` — bad JSON line → skipped
- `test_skips_entries_without_summary` — no summary field → skipped
- `test_ago_field_is_relative_string` — known ts → ago matches expected string

## Acceptance Criteria

- `_read_recent_history` reads real data from `.atlas/history.jsonl`
- `_relative_time` handles just now / minutes / hours / days
- Missing file, malformed lines, missing summary all handled gracefully
- 11 new tests in `tests/test_history.py`, all passing
- All existing tests still pass
