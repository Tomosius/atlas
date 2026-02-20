# Prettier

## Configuration

- Config file: {{config_file}}
- Print width: {{style.print_width}} (default: 80)
- Tab width: {{style.tab_width}} (default: 2)
- Use tabs: {{style.use_tabs}} (default: false)
- Semicolons: {{style.semi}} (default: true)
- Single quotes: {{style.single_quote}} (default: false)
- Trailing commas: {{style.trailing_comma}} (default: "all")

## Commands

- Format all files: `{{commands.fix}}`
- Check (CI): `{{commands.check}}`

## Principles

- Prettier is intentionally opinionated — accept its output, don't fight it
- Never manually reformat code that Prettier manages; run `fix` instead
- `--check` in CI fails if any file differs from Prettier's output
- Use `.prettierignore` to exclude generated files, build output, and vendored code

## With ESLint

When using Prettier alongside ESLint:
- Install `eslint-config-prettier` to disable ESLint formatting rules
- ESLint handles code quality; Prettier handles formatting — no overlap
- Run Prettier first, then ESLint (or use lint-staged to sequence them)

## Ignore Syntax

```
// prettier-ignore
const matrix = [1,0,0, 0,1,0, 0,0,1];  // preserve manual alignment
```

Use `// prettier-ignore` only for cases where manual layout carries meaning
(matrices, lookup tables). Not for avoiding formatting you dislike.

## Integration

- CI: `{{commands.check}}` as a required check
- Pre-commit: `prettier --write` on staged files via lint-staged
- Editor: format-on-save with Prettier extension; set as default formatter
