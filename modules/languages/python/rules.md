# Python

## Project

- Name: {{project.name}}
- Version: {{project.version}}
- Requires Python: {{project.python_version}}
- Package manager: {{pkg_manager}}
- Run prefix: `{{pkg_run}}`

## Style

- Follow PEP 8 — enforced by linter
- Use type hints on all function signatures
- Prefer `pathlib.Path` over `os.path`
- Use f-strings (not `.format()` or `%`)
- Max line length set by linter config (default: 88)

## Imports

- Standard library → third-party → local (separated by blank lines)
- Use absolute imports; avoid `from module import *`
- Keep `__init__.py` files minimal

## Functions & Classes

- One public responsibility per function
- Prefer small, pure functions — easier to test and compose
- Use `@dataclass` or `@dataclass(frozen=True)` for value objects
- Raise specific exceptions; never catch bare `except:`

## Async

- Use `async`/`await` when I/O is involved (HTTP, DB, file)
- Do not mix sync blocking calls inside async functions
- Prefer `asyncio.gather` for concurrent tasks

## Testing

- All tests in `tests/`; mirror the source layout
- Run: `{{pkg_run}} pytest`
- Use `tmp_path` fixture (not `tempfile`) for temporary files
- Parametrize repetitive assertions with `@pytest.mark.parametrize`

## Packaging

- Config in `pyproject.toml` — single source of truth
- Use `{{pkg_run}} <tool>` to invoke project-local tools
- Never install packages at runtime

## Common Commands

{{#if commands.check}}- Check: `{{commands.check}}`{{/if}}
{{#if commands.test}}- Test: `{{commands.test}}`{{/if}}
{{#if commands.fix}}- Fix: `{{commands.fix}}`{{/if}}
