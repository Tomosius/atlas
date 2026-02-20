# Jest

## Configuration

- Config file: {{config_file}}
- Test match: {{test.match}}
- Environment: {{test.environment}} (default: node)
- Transform: {{test.transform}}
- Coverage threshold: {{test.coverage_threshold}}

## Commands

- Run once (CI): `{{commands.test}}`
- Watch mode (dev): `{{commands.test-watch}}`
- With coverage: `{{commands.test-cov}}`

## Structure

- Test files: `*.test.ts`, `*.spec.ts` alongside source or in `__tests__/`
- One test file per source module
- Shared setup in `jest.setup.ts` (referenced via `setupFilesAfterFramework`)

## Writing Tests

```typescript
import { describe, it, expect, jest, beforeEach } from "@jest/globals";

describe("MyService", () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  it("returns expected value", () => {
    expect(result).toBe(expected);
  });
});
```

- Use `describe` to group; `it`/`test` for individual cases
- `expect(x).toBe(y)` for primitives, `.toEqual(y)` for objects/arrays
- Always reset mocks in `beforeEach` to prevent state leakage

## TypeScript Setup

Jest requires a transformer for TypeScript. Common options:

- `ts-jest` — full TypeScript compilation, slower but accurate type-checking
- `@swc/jest` / `babel-jest` — transpile-only, faster but no type errors

Configure in `jest.config.ts`:
```typescript
export default {
  preset: "ts-jest",           // or transform: {"^.+\\.tsx?$": "@swc/jest"}
  testEnvironment: "node",
};
```

## Mocking

- `jest.fn()` — create a mock function
- `jest.spyOn(obj, "method")` — spy on existing method
- `jest.mock("../module")` — auto-mock a module (hoisted automatically)
- `jest.resetAllMocks()` — reset between tests
- `jest.useFakeTimers()` — control `setTimeout`/`setInterval`

## Coverage

Run with `{{commands.test-cov}}`. Set thresholds in config:

```typescript
coverageThreshold: {
  global: { lines: 80, functions: 80, branches: 70 }
}
```

## Integration

- CI: `{{commands.test}}` as a required check
- Watch mode during development: `{{commands.test-watch}}`
