# uv

## Project

- Python version: {{uv.python_version}}
- Run prefix: `uv run`
- Lock file: `uv.lock` (commit this file)

## Core Commands

```bash
uv sync                  # install all dependencies from uv.lock
uv add <package>         # add runtime dependency
uv add --dev <package>   # add development dependency
uv remove <package>      # remove dependency
uv run <command>         # run command in project environment
uv lock                  # regenerate uv.lock without installing
uv lock --upgrade        # upgrade all dependencies
```

## Running Tools

Always use `uv run` to invoke project tools — never activate the venv manually:

```bash
uv run pytest            # run tests
uv run ruff check .      # run linter
uv run python script.py  # run a script
```

This ensures the correct environment is always used, regardless of shell state.

## Dependency Groups

```toml
# pyproject.toml
[project]
dependencies = ["fastapi", "sqlalchemy"]

[dependency-groups]
dev = ["pytest", "ruff", "mypy"]
docs = ["mkdocs", "mkdocs-material"]
```

Install specific groups:
```bash
uv sync --group docs
uv sync --no-dev          # production only
```

## Lock File

- `uv.lock` is the source of truth for reproducible installs — always commit it
- Run `uv lock` after editing `pyproject.toml` manually
- Run `uv lock --upgrade` to update all packages to latest compatible versions
- CI should run `uv sync --frozen` to verify lock file is up to date

## Python Version Management

```bash
uv python install 3.12   # install a specific Python version
uv python pin 3.12       # write .python-version file
```

Set in `pyproject.toml`:
```toml
[project]
requires-python = ">=3.11"
```

## Key Differences from pip

| Task | pip | uv |
|------|-----|----|
| Install deps | `pip install -r requirements.txt` | `uv sync` |
| Add package | edit + `pip install` | `uv add <pkg>` |
| Run tool | activate venv first | `uv run <cmd>` |
| Speed | baseline | 10-100× faster |
