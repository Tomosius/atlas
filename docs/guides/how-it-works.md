# How Atlas Works

## The core idea: pre-compute, then read

Atlas never computes anything at serve time. When you run `atlas init`, `atlas add`, or `atlas sync`, it:

1. Detects your project stack
2. Loads module bundles from the warehouse
3. Scans your config files for real values
4. Injects those values into the module's `rules.md`
5. Writes the result to `.atlas/retrieve/<module>.md`

When an agent calls `atlas retrieve ruff`, Atlas reads that pre-built file from disk — instant.

## Architecture

```
Agent
  │
  │  atlas retrieve ruff
  ▼
MCP Server (server.py)
  │  parse input → route to runtime
  ▼
Atlas Runtime (runtime.py)
  │  read .atlas/retrieve/ruff.md
  ▼
Pre-built retrieve file (instant file read)
```

## The .atlas directory

Atlas stores all project state in `.atlas/` at your project root:

```
.atlas/
  manifest.json        # installed modules + versions
  config.json          # project-level config overrides
  retrieve/
    python.md          # pre-built retrieve file for python module
    ruff.md            # pre-built retrieve file with your actual ruff config
    pytest.md          # ...
  notes/
    ruff.md            # tribal knowledge notes you've added
  history.jsonl        # append-only operation log
```

## Module bundles

Each module in the warehouse ships as:

```
modules/linters/ruff/
  module.json    # metadata: category, detect_files, conflicts_with, ...
  rules.md       # template with {{line-length}} placeholders
```

At init/sync time, Atlas replaces `{{line-length}}` with your actual value from `pyproject.toml`.

## Truth hierarchy

When a value exists in multiple places, Atlas uses this priority:

1. Your config files (`pyproject.toml`, `.eslintrc`, etc.) — highest truth
2. `.atlas/modules/` overrides
3. Warehouse defaults — lowest truth

## Dynamic tool description

The MCP tool description changes based on what modules are installed. An agent connecting to a Python+ruff project sees different verbs and options than one connecting to a TypeScript+ESLint project.
