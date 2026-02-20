# Rust

## Project

- Name: {{project.name}}
- Version: {{project.version}}
- Edition: {{project.edition}}
- Toolchain: {{toolchain.channel}}

## Ownership & Borrowing

- Prefer borrowing (`&T`, `&mut T`) over cloning unless ownership is needed
- Use `Clone` and `Copy` deliberately — don't derive them by default
- Avoid `Rc`/`RefCell` in hot paths; redesign ownership before reaching for them
- Use lifetime annotations only when the compiler cannot infer them

## Error Handling

- Use `Result<T, E>` for fallible operations — never `unwrap()` in library code
- Use `?` operator for propagation; reserve `unwrap()` for tests and prototypes
- Define domain-specific error types; implement `std::error::Error`
- Prefer `thiserror` for library errors, `anyhow` for application errors

## Types

- Use newtype wrappers to make invalid states unrepresentable
- Prefer enums with data over structs with boolean flags
- Derive `Debug` on all public types; derive `PartialEq` for testability
- Use `Option<T>` for optional values — never null equivalents

## Performance

- Avoid unnecessary allocations in hot paths; prefer slices over `Vec` in APIs
- Use iterators and combinators (`map`, `filter`, `collect`) — zero-cost abstractions
- Profile before optimizing; `cargo bench` for benchmarks

## Concurrency

- Prefer message passing (`std::sync::mpsc` or `tokio::sync`) over shared state
- Use `Arc<Mutex<T>>` sparingly; design for ownership transfer
- Mark shared state explicitly with `Send + Sync` bounds

## Testing

- Unit tests in the same file as the code (`#[cfg(test)]` module)
- Integration tests in `tests/`
- Run: `{{commands.test}}`
- Use `#[should_panic]` only when panicking is the correct behavior

## Common Commands

- Build: `{{commands.build}}`
- Test: `{{commands.test}}`
- Check: `{{commands.check}}`
- Format: `cargo fmt`
- Docs: `cargo doc --open`
