# Contributing

## Setup

```bash
git clone https://github.com/Tomosius/atlas
cd atlas
just setup
```

## Workflow

1. Find an issue: `just issue-next`
2. Start it: `just issue-start <number>`
3. Write code with atomic commits (see [Commit Rules](../commit-rules.md))
4. Verify: `just check`
5. Close: `just issue-done <number>`

## Standards

- Follow the coding standards in [DEVELOPMENT.md](../development.md)
- Google-style docstrings on all public APIs
- Tests required for all new code (`just test-cov` must stay ≥ 80%)
- `just check` must pass before any PR

## Submitting a PR

Use the PR template — it has a checklist. All CI checks must pass.
