# Configuration

## Project config: `.atlas/config.json`

Override Atlas defaults for a specific project:

```json
{
  "retrieve": {
    "max_sections": 10,
    "include_notes": true
  },
  "tasks": {
    "test": "uv run pytest",
    "lint": "uv run ruff check src/",
    "fmt": "uv run ruff format src/"
  }
}
```

## Global config: `~/.atlas/config.json`

Defaults applied to all projects:

```json
{
  "auto_install_policy": "suggest",
  "allow_file_deletion": false
}
```

## Config hierarchy

Project config > global config > built-in defaults.

## Task shortcuts

Define project tasks in `.atlas/config.json` under `tasks`. These become available via `atlas just <name>`:

```json
{
  "tasks": {
    "test": "uv run pytest tests/ -v",
    "test-fast": "uv run pytest -n auto",
    "lint": "uv run ruff check src/ tests/",
    "typecheck": "uv run basedpyright src/"
  }
}
```

Then in your editor:

```
atlas just test
atlas just lint
```
