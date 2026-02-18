# Modules

Modules are the knowledge units in Atlas. Each module teaches agents how to work with a specific tool, language, or framework.

## Module categories

| Category | Examples |
|---|---|
| `language` | python, typescript, rust, go, java |
| `linter` | ruff, eslint, clippy, golangci-lint |
| `formatter` | prettier, rustfmt, gofmt |
| `testing` | pytest, vitest, jest, playwright |
| `framework` | django, fastapi, react, next-js, svelte |
| `database` | postgresql, sqlite, redis, mongodb |
| `vcs` | git, svn |
| `platform` | github, gitlab, bitbucket |
| `pkg_manager` | uv, pnpm, npm, cargo, poetry |
| `environment` | docker, docker-compose, venv |
| `ci_cd` | github-actions, gitlab-ci |
| `stack` | python-backend, ts-frontend, fullstack |
| `tool` | commit-rules |
| `prompt` | design, review, debug, king-mode |

## Module lifecycle

```
add ruff      → validate → load bundle → scan config → enrich → write retrieve file
remove ruff   → validate → delete retrieve file → update manifest
sync          → re-scan config → update changed values → rebuild retrieve files
update        → compare versions → re-enrich if newer
```

## Module bundle structure

Each module in the warehouse is a directory:

```
modules/linters/ruff/
  module.json    # metadata
  rules.md       # rules template with {{placeholders}}
```

### module.json fields

```json
{
  "name": "ruff",
  "category": "linter",
  "version": "1.0.0",
  "description": "Fast Python linter and formatter",
  "detect_files": ["pyproject.toml", ".ruff.toml", "ruff.toml"],
  "combines_with": ["python", "pytest"],
  "conflicts_with": ["flake8", "pylint"],
  "config_keys": ["line-length", "select", "ignore", "extend-ignore"],
  "unlocks_verb": null
}
```

### rules.md placeholders

```markdown
## Ruff Configuration

Line length: **{{line-length}}**
Selected rules: `{{select}}`
Ignored rules: `{{ignore}}`
```

Atlas replaces `{{line-length}}` with the actual value from your `pyproject.toml` at sync time.

## Conflict detection

Some modules conflict. Atlas checks `conflicts_with` on `add` and warns:

```
atlas add flake8
→ Warning: flake8 conflicts with ruff (already installed). Remove ruff first.
```

## Creating a module

See `plan/08-MODULE-SPEC.md` for the full spec and required fields.
