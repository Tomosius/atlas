# ESLint

## Configuration

- Config file: {{config_file}}
- Extends: {{linter.extends}}
- Environment: {{linter.env}}

## Active Rules

{{linter.rules}}

## Commands

- Check: `{{commands.check}}`
- Fix: `{{commands.fix}}`

## Principles

- Fix all ESLint errors before committing — `--fix` handles auto-fixable ones
- Use `// eslint-disable-next-line rule-name` sparingly; document why
- Prefer config-level rule changes over inline suppressions
- With Prettier installed: ESLint handles logic, Prettier handles formatting — don't overlap

## Config Format (Flat Config — ESLint v9+)

ESLint v9 uses `eslint.config.js` (flat config). Legacy `.eslintrc.*` still works
but is deprecated. Prefer flat config for new projects.

```js
// eslint.config.js pattern
import js from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
);
```

## TypeScript Integration

- Use `typescript-eslint` for TS-aware rules
- Enable `@typescript-eslint/no-explicit-any` — enforces no `any`
- Enable `@typescript-eslint/no-unused-vars` over base `no-unused-vars`
- Parser: `@typescript-eslint/parser` (set in flat config via `tseslint.config`)

## Integration

- CI: add `{{commands.check}}` as a required check
- Pre-commit: use `eslint --fix` hook before commit
- Editor: ESLint extension for inline feedback
