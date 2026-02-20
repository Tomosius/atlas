# TypeScript

## Project

- Package manager: {{pkg_manager}}
- Run prefix: `{{pkg_run}}`
- Compiler target: {{compiler.target}}
- Module system: {{compiler.module}}
- Strict mode: {{compiler.strict}}
- Output: {{compiler.outDir}}

## Type Safety

- Enable `strict: true` in tsconfig — no exceptions
- Never use `any`; use `unknown` and narrow with type guards
- Prefer `interface` for object shapes, `type` for unions/intersections
- Use `readonly` on properties that should not mutate
- Use `satisfies` operator to validate without widening type

## Functions

- Annotate return types explicitly on exported functions
- Prefer arrow functions for callbacks; named functions for top-level
- Use optional chaining (`?.`) and nullish coalescing (`??`) over null checks
- Avoid function overloads when a union type suffices

## Imports & Modules

- Use ES module syntax (`import`/`export`), not CommonJS
- Use `import type` for type-only imports
- Barrel files (`index.ts`) only at package boundaries — not within features
- Prefer named exports over default exports

## Async

- Use `async`/`await` — avoid raw `.then()` chains
- Type Promise return values: `Promise<User>` not `Promise<any>`
- Handle errors with `try/catch` or typed `Result` patterns

## Null Handling

- Enable `strictNullChecks` (included in `strict`)
- Return `null` for intentional absence; `undefined` for missing/optional
- Use discriminated unions for operations that can fail

## Testing

- Tests alongside source or in `tests/` — match source layout
- Run: `{{pkg_run}} {{commands.test}}`
- Mock at module boundaries, not deep inside implementations

## Common Commands

{{#if commands.check}}- Lint: `{{commands.check}}`{{/if}}
{{#if commands.test}}- Test: `{{commands.test}}`{{/if}}
{{#if commands.fix}}- Fix: `{{commands.fix}}`{{/if}}
{{#if commands.build}}- Build: `{{commands.build}}`{{/if}}
