# Biome

## Configuration

- Config file: {{config_file}}
- Indent style: {{style.indent_style}} (default: tab)
- Indent width: {{style.indent_width}} (default: 2)
- Line width: {{style.line_width}} (default: 80)

## Active Rules

{{linter.rules}}

## Commands

- Check (lint + format): `{{commands.check}}`
- Fix (auto-fix + format): `{{commands.fix}}`
- Format only: `{{commands.format}}`

## Principles

- Biome replaces both ESLint and Prettier in one tool — do not run both
- `check` runs lint and format checks together; `--write` applies fixes
- Fix all biome errors before committing
- Use `// biome-ignore lint/category/ruleName: reason` to suppress inline — always include reason
- Biome is intentionally opinionated; resist overriding defaults without cause

## Key Differences from ESLint + Prettier

- Single config file (`biome.json`) instead of `.eslintrc` + `.prettierrc`
- Significantly faster (Rust-based)
- Formatter is not as configurable as Prettier — that is by design
- No plugin ecosystem — rules are built-in

## Integration

- CI: add `{{commands.check}}` as a required check
- Pre-commit: use `biome check --write` hook
- Editor: Biome VSCode/Zed extension for inline feedback; disable ESLint and Prettier extensions
