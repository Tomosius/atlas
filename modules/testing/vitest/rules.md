# Vitest

## Configuration

- Config file: {{config_file}}
- Test include: {{test.include}}
- Test exclude: {{test.exclude}}
- Environment: {{test.environment}} (default: node)
- Globals: {{test.globals}}
- Coverage provider: {{test.coverage_provider}}

## Commands

- Run once (CI): `{{commands.test}}`
- Watch mode (dev): `{{commands.test-watch}}`
- With coverage: `{{commands.test-cov}}`

## Structure

- Test files: `*.test.ts`, `*.spec.ts` alongside source or in `__tests__/`
- One test file per source module
- Share setup in `vitest.setup.ts` (referenced via `setupFiles` in config)

## Writing Tests

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";

describe("MyComponent", () => {
  it("does the thing", () => {
    expect(result).toBe(expected);
  });
});
```

- Use `describe` to group related tests
- Use `it` (or `test`) for individual cases — name describes the behaviour
- Prefer `expect(x).toBe(y)` for primitives, `.toEqual(y)` for objects/arrays
- Use `vi.fn()` for mocks, `vi.spyOn()` for spies
- Use `vi.mock("module")` to mock entire modules at the top of the file

## Async Tests

```typescript
it("fetches data", async () => {
  const result = await fetchUser(1);
  expect(result.name).toBe("Alice");
});
```

Always `await` async operations; Vitest handles async natively.

## Mocking

- `vi.fn()` — create a mock function
- `vi.spyOn(obj, "method")` — spy on an existing method
- `vi.mock("../module")` — auto-mock a module (hoisted to top of file)
- `vi.resetAllMocks()` in `beforeEach` to prevent mock state leakage

## Coverage

Run with `{{commands.test-cov}}`. Configure thresholds in `vitest.config.ts`:

```typescript
coverage: {
  provider: "v8",
  thresholds: { lines: 80, functions: 80 }
}
```

## Integration

- CI: `{{commands.test}}` as a required check
- Watch mode during development: `{{commands.test-watch}}`
- Vitest UI: `vitest --ui` for browser-based test explorer
