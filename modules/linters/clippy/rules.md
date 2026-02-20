# Clippy

## Commands

- Check: `{{commands.check}}`
- Check all targets + features: `{{commands.check-all}}`

## Principles

- `-D warnings` promotes all clippy warnings to errors — fix before committing
- Run `{{commands.check-all}}` in CI; catches issues in tests and examples too
- Address every warning; only suppress with `#[allow(clippy::rule_name)]` + comment explaining why
- Clippy is part of the Rust toolchain — no separate install needed

## Rule Configuration

Configured in `Cargo.toml` under `[lints.clippy]`:

```toml
[lints.clippy]
pedantic = "warn"        # strict style rules
nursery = "warn"         # experimental rules
unwrap_used = "deny"     # ban unwrap() in library code
expect_used = "warn"     # warn on expect() usage
```

Active rules: {{linter.rules}}

## Common Lint Groups

| Group | Level | Purpose |
|-------|-------|---------|
| `clippy::all` | warn (default) | All stable lints |
| `clippy::pedantic` | opt-in | Stricter style rules |
| `clippy::nursery` | opt-in | Experimental lints |
| `clippy::cargo` | opt-in | Cargo.toml consistency |

## Suppression

```rust
// Suppress a single occurrence — always explain why
#[allow(clippy::too_many_arguments)]
fn complex_init(a: i32, b: i32, c: i32, d: i32, e: i32, f: i32, g: i32) {}
```

Prefer fixing the code over suppressing. If suppression is unavoidable,
the comment must explain the reason.

## Integration

- CI: `{{commands.check-all}}` as a required check
- Pre-commit: `cargo clippy -- -D warnings` on changed files
- Editor: `rust-analyzer` surfaces clippy lints inline when configured
