# Ruff

## Configuration

- Line length: {{style.line_length}} (default: 88)
- Target Python: {{style.target_version}}
- Config file: {{config_file}}
- Auto-fix enabled: {{linter.auto_fix}}

## Active Rules

{{linter.rules}}

## Ignored Rules

{{linter.ignored}}

## Commands

- Check: `{{commands.check}}`
- Fix: `{{commands.fix}}`
- Format only: `{{commands.format}}`

## Principles

- Ruff replaces flake8, isort, pyupgrade, and pep8-naming in one tool
- If ruff reports it, fix it — don't add `# noqa` unless truly unavoidable
- Run `fix` before committing — auto-format is free
- `# noqa: EXXX` to suppress a specific rule inline; document why

## Rule Sets

Ruff rule prefixes in common use:

| Prefix | Origin | Purpose |
|--------|--------|---------|
| `E`/`W` | pycodestyle | PEP 8 style |
| `F` | Pyflakes | Undefined names, unused imports |
| `I` | isort | Import order |
| `N` | pep8-naming | Naming conventions |
| `UP` | pyupgrade | Modern Python syntax |
| `B` | flake8-bugbear | Common bugs and design issues |
| `SIM` | flake8-simplify | Code simplification |
| `RUF` | Ruff-native | Ruff-specific rules |

## Integration

- CI: add `{{commands.check}}` as a required check
- Pre-commit: use `ruff check --fix` + `ruff format` hooks
- Editor: enable ruff LSP or ruff extension for inline feedback
