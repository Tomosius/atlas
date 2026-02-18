# Atlas MCP — Development Guide

Complete reference for the development workflow, toolchain, and coding standards.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [First-time Setup](#2-first-time-setup)
3. [Daily Workflow](#3-daily-workflow)
4. [Task Runner (just)](#4-task-runner-just)
5. [Toolchain Reference](#5-toolchain-reference)
6. [Coding Standards](#6-coding-standards)
7. [Docstring Style (Google)](#7-docstring-style-google)
8. [Testing Guide](#8-testing-guide)
9. [GitHub Issue Workflow](#9-github-issue-workflow)
10. [CI Pipeline](#10-ci-pipeline)

---

## 1. Prerequisites

| Tool | Install | Purpose |
|---|---|---|
| `uv` | `brew install uv` | Python version + package manager |
| `just` | `brew install just` | Task runner (like make, but better) |
| `gh` | `brew install gh` | GitHub CLI for issue workflow |
| Python 3.11+ | managed by uv | Runtime |

---

## 2. First-time Setup

```bash
git clone https://github.com/Tomosius/atlas
cd atlas
just setup
```

`just setup` does:
1. `uv sync --all-groups` — creates `.venv/`, installs all deps including dev tools
2. Prints toolchain versions to confirm everything is working

You never need to activate the venv manually. All `just` commands use `uv run`
which auto-discovers the venv.

---

## 3. Daily Workflow

```bash
# Before starting work — see what's in progress and what's next
just issue-current
just issue-next

# Start an issue
just issue-start 6

# Write code, then get fast feedback
just quick            # lint + ty (seconds)

# Before committing
just fmt              # auto-format
just check            # full pipeline: fmt-check + lint + types + tests

# After all checks pass — commit (follow COMMIT_RULES.md)
git add -p            # stage atomically
git commit            # write message per COMMIT_RULES.md

# Close the issue when done
just issue-done 6
```

---

## 4. Task Runner (just)

Run `just` with no arguments to see all available recipes.

### Setup

| Command | Description |
|---|---|
| `just setup` | Install deps, print toolchain info |
| `just info` | Show tool versions and project info |

### Formatting

| Command | Description |
|---|---|
| `just fmt` | Format all files with ruff (apply) |
| `just fmt-check` | Check formatting without changing files (used in CI) |

### Linting

| Command | Description |
|---|---|
| `just lint` | Run ruff linter (includes docstring checks) |
| `just lint-fix` | Run ruff linter and auto-fix safe issues |

### Type Checking

| Command | Description |
|---|---|
| `just ty` | Fast check with `ty` (use during development) |
| `just pyright` | Thorough check with `basedpyright` (use before push) |
| `just types` | Run both type checkers |

### Testing

| Command | Description |
|---|---|
| `just test` | Run all tests |
| `just test-v` | Run all tests, verbose output |
| `just test-unit` | Run only `@pytest.mark.unit` tests |
| `just test-integration` | Run only `@pytest.mark.integration` tests |
| `just test-k "pattern"` | Run tests matching a keyword |
| `just test-f tests/test_scanner.py` | Run a specific file |
| `just test-cov` | Run tests with HTML coverage report |
| `just test-watch` | Re-run tests on file changes |

### Quality Gates

| Command | Description |
|---|---|
| `just check` | Full pipeline — mirrors CI exactly |
| `just quick` | Fast check — lint + ty only (no tests) |

### Running Atlas

| Command | Description |
|---|---|
| `just run status` | Run atlas CLI with arguments |
| `just serve` | Start the MCP server (stdio transport) |
| `just repl` | Python REPL with atlas importable |

### Issue Workflow

| Command | Description |
|---|---|
| `just issue-current` | Show in-progress issues |
| `just issue-next` | Show next open Phase 1 issues |
| `just issue-start 6` | Mark issue #6 as in-progress |
| `just issue-done 6` | Close issue #6 |

### Build

| Command | Description |
|---|---|
| `just build` | Build wheel + sdist |
| `just publish-test` | Publish to TestPyPI |
| `just publish` | Publish to PyPI |
| `just clean` | Remove build artifacts, `__pycache__`, `.coverage` |

---

## 5. Toolchain Reference

### uv

Fast Python package manager from Astral. Manages the venv at `.venv/`.

```bash
uv sync --all-groups        # install all deps (including dev)
uv add <package>            # add runtime dependency
uv add --dev <package>      # add dev dependency
uv remove <package>         # remove dependency
uv run <command>            # run command inside venv
uv build                    # build wheel + sdist
uv publish                  # publish to PyPI
```

### ruff

Linter + formatter. Replaces flake8, black, isort, pydocstyle.

```bash
just lint                   # check for issues
just lint-fix               # fix safe issues automatically
just fmt                    # format files
just fmt-check              # check format (CI mode)

# Direct usage if needed
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/
```

Config in `pyproject.toml` under `[tool.ruff]`. Key settings:
- `line-length = 120`
- `target-version = "py310"`
- Google docstring convention (`D` rules)
- Import sorting (`I` rules)

### ty

Fast type checker from Astral (same team as ruff/uv). Experimental but very fast.
Use for quick feedback during development.

```bash
just ty
uv run ty check src/
```

### basedpyright

Thorough type checker, stricter than vanilla pyright. Used as the CI gate.

```bash
just pyright
uv run basedpyright src/
```

Config in `pyproject.toml` under `[tool.basedpyright]`. Currently set to
`typeCheckingMode = "standard"` with some rules relaxed (the result-dict
pattern creates many "unknown type" warnings that are intentional).

### pytest

Test runner.

```bash
just test                   # all tests
just test-v                 # verbose
just test-k "detection"     # filter by keyword
just test-cov               # with coverage
```

Config in `pyproject.toml` under `[tool.pytest.ini_options]`:
- `testpaths = ["tests"]`
- `pythonpath = ["src"]` — lets tests import `atlas` directly
- `asyncio_mode = "auto"` — async tests work without decorator
- Default flags: `-ra -q --tb=short`

---

## 6. Coding Standards

### Language version

Target Python 3.10+. Use `|` union syntax only where safe; ruff's `UP007`
rule is ignored to avoid false positives.

### Result pattern (no exceptions in core)

The core engine never raises exceptions for expected error conditions.
It returns result dicts:

```python
# Good
def find_module(name: str) -> dict:
    if name not in registry:
        return {"ok": False, "error": "MODULE_NOT_FOUND", "module": name}
    return {"ok": True, "data": registry[name]}

# Bad — don't raise in core
def find_module(name: str) -> dict:
    if name not in registry:
        raise KeyError(f"Module {name} not found")   # ❌
```

Only `server.py` (MCP layer) and `cli.py` may raise or catch exceptions.

### No global state in core

All functions take explicit arguments. No module-level mutable state.

```python
# Good
def detect_project(path: Path, config: AtlasConfig) -> ProjectDetection: ...

# Bad
_current_path: Path | None = None   # ❌ global state
```

### stdlib-only core

`src/atlas/core/` must not import anything outside the standard library.
Only `src/atlas/server.py` may import `mcp`.

### Data tables over code branches

Detection, scanning, and routing use dicts and lists — not if/elif chains.

```python
# Good
LANGUAGE_MARKERS: dict[str, list[str]] = {
    "python": ["pyproject.toml", "setup.py", "requirements.txt"],
    "typescript": ["tsconfig.json", "package.json"],
}

# Bad
def detect_language(files):       # ❌
    if "pyproject.toml" in files:
        return "python"
    elif "tsconfig.json" in files:
        return "typescript"
```

### Pre-compute then read

Retrieve files are built at `init`/`add`/`sync` time and stored on disk.
The MCP tool reads them as instant file reads — no computation at serve time.

### Import style

```python
# Standard library first, then third-party, then local — ruff enforces this
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
```

---

## 7. Docstring Style (Google)

All public functions, classes, and methods require Google-style docstrings.
Ruff rule `D` enforces this. Tests are exempt.

### Function docstring

```python
def scan_module_config(module_name: str, project_path: Path) -> dict:
    """Scan project config files for values relevant to a module.

    Reads config files listed in MODULE_CONFIG_MAP for the given module,
    extracts key-value pairs, and returns them for injection into rules.md.

    Args:
        module_name: The module identifier (e.g. "ruff", "pytest").
        project_path: Absolute path to the project root.

    Returns:
        A result dict with shape:
            {"ok": True, "data": {"line-length": "120", "select": "E,W,F"}}
        or on failure:
            {"ok": False, "error": "CONFIG_NOT_FOUND", "module": module_name}

    Raises:
        Does not raise. All errors returned as result dicts.

    Example:
        >>> result = scan_module_config("ruff", Path("/my/project"))
        >>> if result["ok"]:
        ...     print(result["data"]["line-length"])
        120
    """
```

### Class docstring

```python
class Atlas:
    """Main runtime class. Owns all project state for a single project root.

    Uses lazy properties backed by cached JSON files in .atlas/. Call
    invalidate() after any mutation to clear the cache.

    Attributes:
        project_path: Absolute path to the project root.
        atlas_dir: Path to the .atlas/ directory inside the project.

    Example:
        >>> atlas = Atlas(Path("/my/project"))
        >>> result = atlas.handle("retrieve python")
        >>> print(result["data"])
    """
```

### Short docstring (one-liner)

```python
def ok_result(data: dict) -> dict:
    """Wrap data in a standard success result dict."""
    return {"ok": True, "data": data}
```

### When to skip a docstring

- `__init__` methods (document on the class instead) — `D107` ignored
- Test functions — `D` rules ignored in `tests/`
- Private helpers (`_name`) that are obvious from context — not required
  but still appreciated

---

## 8. Testing Guide

### Structure

```
tests/
  conftest.py              # shared fixtures (project paths, tmp dirs)
  fixtures/
    python_project/        # fake Python project with pyproject.toml + ruff
    typescript_project/    # fake TS project with package.json + tsconfig
    empty_project/         # bare directory
  test_detection.py
  test_scanner.py
  test_categories.py
  test_modules.py
  test_retrieve.py
  test_parser.py
  test_runtime.py
  test_server.py
  test_cli.py
```

### Fixture projects

Tests that need a real project on disk use the fixtures in `tests/fixtures/`.
Access them via conftest fixtures:

```python
@pytest.fixture
def python_project(tmp_path):
    """Copy the python fixture to a tmp dir and return its path."""
    src = Path(__file__).parent / "fixtures" / "python_project"
    dst = tmp_path / "python_project"
    shutil.copytree(src, dst)
    return dst
```

### Markers

```python
@pytest.mark.unit          # fast, no filesystem, no subprocess
@pytest.mark.integration   # needs real filesystem / subprocess
@pytest.mark.slow          # > 1s (deselect with -m "not slow")
```

### Parametrize for data tables

Detection and scanner tests use `@pytest.mark.parametrize` to cover all
entries in the data tables without repetition:

```python
@pytest.mark.parametrize("language,marker", [
    ("python", "pyproject.toml"),
    ("typescript", "tsconfig.json"),
    ("rust", "Cargo.toml"),
])
@pytest.mark.unit
def test_detect_language_from_marker(language, marker, tmp_path):
    (tmp_path / marker).touch()
    result = detect_project(tmp_path)
    assert result["ok"]
    assert result["data"].language == language
```

### Async tests

`asyncio_mode = "auto"` is set — async test functions just work:

```python
async def test_server_tool_listing():
    result = await list_tools()
    assert len(result) == 1
    assert result[0].name == "atlas"
```

---

## 9. GitHub Issue Workflow

See `COMMIT_RULES.md` for the full protocol. Quick reference:

```bash
# See what to work on
just issue-current          # in-progress
just issue-next             # next open Phase 1 issues

# Start
just issue-start 6
# → update CLAUDE.md Current Issue

# Work — many atomic commits per issue is correct
just quick                  # fast check after each logical step
just fmt && git add -p && git commit

# Finish
just check                  # full pipeline must pass
just issue-done 6
# → update CLAUDE.md Current Issue to next
```

---

## 10. CI Pipeline

Defined in `.github/workflows/ci.yml`. Runs on push/PR to `main` and `dev`.

### Jobs

**quality** — runs on Python 3.11, 3.12, 3.13:
1. `uv sync --all-groups`
2. `ruff check src/ tests/` — lint
3. `ruff format --check src/ tests/` — format gate
4. `basedpyright src/` — type check
5. `pytest tests/ -v --tb=short` — tests

**publish** — runs only on `v*` tags, after quality passes:
1. `uv build`
2. Publishes to PyPI via trusted publishing (no token needed)

### Matching CI locally

```bash
just check
```

This runs exactly the same steps as CI. If `just check` passes locally,
CI will pass.

### PyPI publishing

Publishing uses GitHub's OIDC trusted publishing — no API token stored in
secrets. To release:

```bash
# 1. Bump version in pyproject.toml
# 2. Commit: chore(release): bump version to 0.1.0
# 3. Tag and push
git tag v0.1.0
git push origin v0.1.0
# CI publishes automatically
```
