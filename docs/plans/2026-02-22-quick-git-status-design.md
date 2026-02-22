# Design: Quick Git Status for Auto-Brief (Issue #97)

## What We're Building

Replace the `_quick_git_status` stub in `src/atlas/runtime.py` with a real
implementation that runs fast git subprocesses and returns a formatted string
like:

```
  Branch: feat/auth-oauth (2 ahead of main)
  Modified (unstaged): src/auth/oauth.py, src/auth/providers.py
```

## Reference

- `plan/05-ATLAS-API.md §24` — `_quick_git_status` usage and output format
- `src/atlas/runtime.py:412` — current stub
- `src/atlas/core/git.py` — existing (empty) git module

## Output Format

```
  Branch: <branch> (<N> ahead of <upstream>)    ← omit ahead/behind if on main/clean
  Modified (unstaged): file1.py, file2.py        ← omit if none
  Staged: file3.py                               ← omit if none
```

Returns `""` if not in a git repo or git not available.

## Changes

### `src/atlas/runtime.py`

Replace `_quick_git_status` stub:

```python
def _quick_git_status(self) -> str:
    """Return a formatted git status string for the session brief."""
    import subprocess

    def _run(cmd: list[str]) -> str:
        try:
            return subprocess.check_output(
                cmd, cwd=self.project_dir,
                stderr=subprocess.DEVNULL, timeout=3,
            ).decode().strip()
        except Exception:
            return ""

    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if not branch or branch == "HEAD":
        return ""

    lines: list[str] = []

    # Ahead/behind vs upstream
    counts = _run(["git", "rev-list", "--left-right", "--count", "HEAD...@{upstream}"])
    if counts:
        parts = counts.split()
        if len(parts) == 2:
            ahead, behind = int(parts[0]), int(parts[1])
            suffix = ""
            if ahead and behind:
                suffix = f" ({ahead} ahead, {behind} behind)"
            elif ahead:
                suffix = f" ({ahead} ahead)"
            elif behind:
                suffix = f" ({behind} behind)"
            lines.append(f"  Branch: {branch}{suffix}")
        else:
            lines.append(f"  Branch: {branch}")
    else:
        lines.append(f"  Branch: {branch}")

    # Unstaged modifications
    unstaged = _run(["git", "diff", "--name-only"])
    if unstaged:
        files = ", ".join(unstaged.splitlines())
        lines.append(f"  Modified (unstaged): {files}")

    # Staged changes
    staged = _run(["git", "diff", "--cached", "--name-only"])
    if staged:
        files = ", ".join(staged.splitlines())
        lines.append(f"  Staged: {files}")

    return "\n".join(lines)
```

### `tests/test_git_status.py` (new file)

Tests use `monkeypatch` to mock `subprocess.check_output` — no real git calls.

**`TestQuickGitStatus`** (8 tests):
- `test_returns_empty_when_not_in_git_repo` — all subprocess calls raise CalledProcessError → `""`
- `test_returns_empty_when_branch_is_HEAD` — detached HEAD → `""`
- `test_branch_name_in_output` — normal branch → output contains branch name
- `test_ahead_count_shown` — 2 ahead → "(2 ahead)" in output
- `test_behind_count_shown` — 3 behind → "(3 behind)" in output
- `test_ahead_and_behind_shown` — both → "(1 ahead, 2 behind)" in output
- `test_unstaged_files_shown` — dirty working tree → "Modified (unstaged):" in output
- `test_staged_files_shown` — staged files → "Staged:" in output
- `test_clean_branch_no_suffix` — 0 ahead, 0 behind → no parenthetical
- `test_no_upstream_branch_still_shows_branch` — no upstream (empty counts) → branch shown, no crash

## Acceptance Criteria

- `_quick_git_status` runs real git subprocesses with 3s timeout
- Returns `""` if not in a git repo, git not available, or detached HEAD
- Output format matches spec: branch line + optional ahead/behind + optional unstaged + optional staged
- All subprocess errors handled gracefully (never raises)
- 10 tests in `tests/test_git_status.py`, all passing
- All existing tests still pass
