# Go

## Project

- Module: {{project.module}}
- Go version: {{project.go_version}}

## Code Style

- Run `gofmt` before every commit — no manual formatting debates
- Follow `go vet` and `golangci-lint` — fix all warnings
- Package names: short, lowercase, no underscores (`httputil` not `http_util`)
- File names: lowercase with underscores (`user_handler.go`)

## Error Handling

- Always check errors — never assign to `_` unless truly intentional
- Return errors as the last return value: `(T, error)`
- Wrap errors with context: `fmt.Errorf("parsing config: %w", err)`
- Use `errors.Is` / `errors.As` for error inspection, not string comparison
- Define sentinel errors (`var ErrNotFound = errors.New(...)`) for comparison

## Packages & Imports

- One package per directory; package name matches directory name
- Use internal packages (`internal/`) to restrict access within the module
- Group imports: stdlib → external → internal (separated by blank lines)
- Avoid circular imports — restructure if they appear

## Functions & Interfaces

- Accept interfaces, return concrete types
- Keep interfaces small — single-method interfaces are idiomatic
- Use `context.Context` as the first parameter on all I/O functions
- Prefer table-driven tests for functions with many input cases

## Concurrency

- Communicate via channels; share memory only when channels are awkward
- Always specify goroutine lifetimes — use `context.Context` for cancellation
- Use `sync.WaitGroup` to wait for goroutine completion
- Race-test with: `go test -race ./...`

## Testing

- Tests in `*_test.go` files alongside the code
- Use subtests: `t.Run("case name", func(t *testing.T) {...})`
- Run: `{{commands.test}}`
- Race detection: `go test -race ./...`

## Common Commands

- Build: `{{commands.build}}`
- Test: `{{commands.test}}`
- Vet: `{{commands.check}}`
- Format: `gofmt -w .`
- Tidy deps: `go mod tidy`
