# rustfmt

## Configuration

- Config file: {{config_file}}
- Max width: {{style.max_width}} (default: 100)
- Tab spaces: {{style.tab_spaces}} (default: 4)
- Edition: {{style.edition}}
- Imports granularity: {{style.imports_granularity}} (default: Preserve)

## Commands

- Format: `{{commands.fix}}`
- Check (CI): `{{commands.check}}`

## Principles

- rustfmt ships with the Rust toolchain — no separate install needed
- Run `cargo fmt` before every commit; `cargo fmt --check` fails CI if any file differs
- Accept rustfmt output without argument — consistency over personal preference
- `rustfmt.toml` / `.rustfmt.toml` for project-level overrides; keep overrides minimal

## Ignore Syntax

```rust
#[rustfmt::skip]
fn manually_formatted() {
    let matrix = [[1, 0, 0],
                  [0, 1, 0],
                  [0, 0, 1]];
}
```

Use `#[rustfmt::skip]` only when manual layout carries meaning (matrices,
alignment tables). Requires `#![feature(rustfmt_skip)]` on stable — prefer
`#[allow(clippy::...)]` patterns where possible.

For a single expression:
```rust
let x = #[rustfmt::skip] complex_expression;
```

## Common Config Options

| Option | Default | Purpose |
|--------|---------|---------|
| `max_width` | 100 | Maximum line length |
| `tab_spaces` | 4 | Spaces per indent level |
| `imports_granularity` | `Preserve` | `Module`, `Crate`, `One` to merge imports |
| `group_imports` | `Preserve` | `StdExternalCrate` for stdlib/ext/local grouping |
| `format_strings` | `false` | Format string literals |

## Integration

- CI: `{{commands.check}}` as a required check
- Pre-commit: `cargo fmt` before `cargo clippy`
- Editor: `rust-analyzer` applies rustfmt on save when configured
