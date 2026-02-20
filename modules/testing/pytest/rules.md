# pytest

## Configuration

- Test paths: {{pytest.testpaths}}
- Extra options: {{pytest.addopts}}
- Test file pattern: {{pytest.python_files}}
- Config file: {{config_file}}

## Commands

- Run tests: `{{commands.test}}`
- Verbose: `{{commands.test-v}}`
- With coverage: `{{commands.test-cov}}`

## Structure

- All tests in `tests/` mirroring the source layout
- Test files: `test_<module>.py` or `<module>_test.py`
- One `conftest.py` at each level that needs shared fixtures
- Never import from test files — tests are leaves, not libraries

## Writing Tests

- Test one behaviour per test function — name describes what it tests
- Use `assert` directly; avoid `unittest.TestCase` style
- Parametrize repetitive cases: `@pytest.mark.parametrize`
- Use `tmp_path` fixture for temporary files, not `tempfile` directly
- Use `monkeypatch` for environment variables and patching
- Use `capsys` / `capfd` to capture stdout/stderr output

## Fixtures

- Define shared fixtures in `conftest.py` — pytest discovers them automatically
- Prefer function-scoped fixtures (default); use `scope="module"` or `"session"` only for expensive setup
- Yield fixtures for teardown:

```python
@pytest.fixture
def db_connection():
    conn = create_connection()
    yield conn
    conn.close()
```

## Marks

- `@pytest.mark.slow` — skip in fast runs with `-m "not slow"`
- `@pytest.mark.parametrize` — data-driven tests
- `@pytest.mark.xfail` — known failures with reason
- `@pytest.mark.skip(reason="...")` — explicitly skipped tests

## Assertions

- Use plain `assert` — pytest rewrites assertions for detailed output
- `pytest.raises(ExceptionType)` for expected exceptions
- `pytest.approx` for floating-point comparisons

## Integration

- CI: `{{commands.test}}` as a required check
- Coverage: add `pytest-cov` and `--cov=src --cov-report=term-missing` to `addopts`
