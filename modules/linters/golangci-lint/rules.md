# golangci-lint

## Commands

- Check: `{{commands.check}}`
- Fix: `{{commands.fix}}`

## Principles

- golangci-lint runs multiple linters in parallel — faster than running each separately
- Fix all reported issues before committing; don't suppress without a documented reason
- Use `//nolint:lintername` with a comment explaining why when suppression is truly necessary
- Configure enabled/disabled linters in `.golangci.yml` rather than inline suppressions

## Configuration

Configured in `.golangci.yml`:

```yaml
linters:
  enable:
    - errcheck
    - govet
    - staticcheck
    - gosimple
    - unused
  disable:
    - exhaustruct

linters-settings:
  govet:
    enable-all: true
```

## Common Linters Included

| Linter | Purpose |
|--------|---------|
| `errcheck` | Unchecked error return values |
| `govet` | Suspicious constructs (shadow, printf format, etc.) |
| `staticcheck` | Comprehensive static analysis |
| `gosimple` | Code simplification suggestions |
| `unused` | Unused code detection |
| `gofmt` | Formatting check (fails if code is not gofmt-formatted) |

## Integration

- CI: `{{commands.check}}` as a required check
- Pre-commit: `golangci-lint run --new-from-rev=HEAD~1` to check only changed code
- Editor: gopls surfaces many of the same issues inline
