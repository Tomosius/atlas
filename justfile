# =============================================================================
# Atlas MCP — justfile
# =============================================================================
#
# Prerequisites:
#   brew install just      (task runner)
#   brew install uv        (Python package manager)
#
# Quick start:
#   just setup             install deps and verify toolchain
#   just                   show this help
#
# All commands use `uv run` — no need to activate the venv manually.
# =============================================================================

# Show available recipes
default:
    @just --list --unsorted

# =============================================================================
# Setup & environment
# =============================================================================

# Install all dev dependencies and verify the toolchain
setup:
    uv sync --all-groups
    @echo ""
    @echo "✓ Dependencies installed"
    @just --justfile {{ justfile() }} info

# Show toolchain versions
info:
    @echo "── Toolchain ──────────────────────────────"
    @uv run python --version
    @uv run ruff --version
    @uv run ty --version
    @uv run basedpyright --version
    @uv run pytest --version
    @uv run mkdocs --version
    @echo "── Project ────────────────────────────────"
    @uv run python -c "import importlib.metadata; print('Version:', importlib.metadata.version('atlas-mcp'))" 2>/dev/null || echo "Version: (package not installed)"
    @echo "───────────────────────────────────────────"

# =============================================================================
# 1. Lint + Format  (use constantly during development)
# =============================================================================

# Format and lint in one shot — the primary inner-loop command
fix:
    uv run ruff format src/ tests/
    uv run ruff check --fix src/ tests/
    @echo "✓ Formatted and linted"

# Format only
fmt:
    uv run ruff format src/ tests/
    @echo "✓ Formatted"

# Lint only (no auto-fix, shows all issues)
lint:
    uv run ruff check src/ tests/

# Lint with auto-fix
lint-fix:
    uv run ruff check --fix src/ tests/

# Check format without changing files (CI mode)
fmt-check:
    uv run ruff format --check src/ tests/

# =============================================================================
# 2. Type checking
# =============================================================================

# Fast type check — use during development for quick feedback
ty:
    uv run ty check src/

# Thorough type check — use before pushing (slower, more accurate)
pyright:
    uv run basedpyright src/

# Run both type checkers
types: ty pyright

# =============================================================================
# 3. Tests
# =============================================================================

# Run tests on files changed since last git commit (fast feedback loop)
test-changed:
    @echo "── Tests for changed files ────────────────"
    @CHANGED=$( \
        git diff --name-only HEAD | grep -E '^(src|tests)/.*\.py$$' | \
        sed 's|^src/atlas/core/\(.*\)\.py$$|tests/test_\1.py|' | \
        sed 's|^src/atlas/\(.*\)\.py$$|tests/test_\1.py|' | \
        sed 's|^tests/\(.*\)$$|\1|' \
    ); \
    if [ -z "$$CHANGED" ]; then \
        echo "No changed Python files detected — running full suite"; \
        uv run pytest; \
    else \
        echo "Changed test files: $$CHANGED"; \
        uv run pytest $$CHANGED -v 2>/dev/null || uv run pytest; \
    fi

# Run the full test suite (all files, sequential)

# Exit code 5 = no tests collected (expected while stubs are empty)
test:
    uv run pytest || [ $? -eq 5 ]

# Run the full test suite in parallel (faster on multi-core)
test-fast:
    uv run pytest -n auto

# Run tests with verbose output
test-v:
    uv run pytest -v

# Run only unit tests (fast, no filesystem)
test-unit:
    uv run pytest -m unit

# Run only integration tests (real filesystem)
test-integration:
    uv run pytest -m integration -v

# Run tests matching a keyword

# Usage: just test-k scanner
test-k pattern:
    uv run pytest -k "{{ pattern }}" -v

# Run a specific test file

# Usage: just test-f tests/test_scanner.py
test-f file:
    uv run pytest {{ file }} -v

# Run tests with coverage report (terminal + HTML)
test-cov:
    uv run pytest --cov=src/atlas --cov-report=term-missing --cov-report=html
    @echo ""
    @echo "HTML coverage: open htmlcov/index.html"

# =============================================================================
# 4. Quality gate (mirrors CI exactly)
# =============================================================================
# Full pipeline: fmt-check → lint → types → full tests

# Run this before pushing. If it passes here, CI will pass.
check: fmt-check lint pyright test
    @echo ""
    @echo "✓ All checks passed — safe to push"

# Quick check: fix + ty (seconds — use after every save)
quick: fix ty
    @echo "✓ Quick checks passed"

# =============================================================================
# 5. Running Atlas
# =============================================================================
# Run the atlas CLI with arguments

# Usage: just run status    /    just run "retrieve python"
run *args:
    uv run atlas {{ args }}

# Start the MCP server (stdio transport — useful for manual testing)
serve:
    uv run atlas-mcp

# Open a Python REPL with atlas importable
repl:
    uv run python -c "import atlas; print('atlas imported OK'); import code; code.interact(local=locals())"

# =============================================================================
# 6. Documentation (MkDocs)
# =============================================================================

# Serve docs locally with live reload (opens at http://127.0.0.1:8000)
docs:
    uv run mkdocs serve

# Build static docs site into site/
docs-build:
    uv run mkdocs build --strict

# Deploy docs to GitHub Pages (gh-pages branch)
docs-deploy:
    uv run mkdocs gh-deploy --force
    @echo "✓ Docs deployed to https://tomosius.github.io/atlas"

# =============================================================================
# 7. GitHub issue workflow
# =============================================================================

# Show currently in-progress issues
issue-current:
    @gh issue list --repo Tomosius/atlas --label "status:in-progress" \
        --json number,title --jq '.[] | "#\(.number)  \(.title)"'

# Show next open Phase 1 issues
issue-next:
    @gh issue list --repo Tomosius/atlas --label "phase:1" --state open \
        --json number,title --limit 10 \
        --jq '.[] | "#\(.number)  \(.title)"'

# Mark an issue as in-progress

# Usage: just issue-start 6
issue-start number:
    gh issue edit {{ number }} --add-label "status:in-progress" --repo Tomosius/atlas
    @echo "✓ Issue #{{ number }} marked in-progress — update CLAUDE.md"

# Close a completed issue

# Usage: just issue-done 6
issue-done number:
    gh issue close {{ number }} --repo Tomosius/atlas --comment "Completed."
    gh issue edit {{ number }} --remove-label "status:in-progress" --repo Tomosius/atlas
    @echo "✓ Issue #{{ number }} closed — update CLAUDE.md"

# =============================================================================
# 8. Build & publish
# =============================================================================

# Build wheel and sdist into dist/
build:
    uv build
    @echo ""
    @ls -lh dist/

# Publish to TestPyPI (verify before real publish)
publish-test:
    uv publish --index-url https://test.pypi.org/legacy/

# Publish to PyPI — only run on tagged releases
publish:
    @echo "⚠ Publishing to PyPI. This is permanent."
    @echo "Ensure version in pyproject.toml matches the git tag."
    uv publish

# Remove all build artifacts
clean:
    rm -rf dist/ build/ site/ htmlcov/ .coverage .pytest_cache
    find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -not -path './.venv/*' -delete 2>/dev/null || true
    @echo "✓ Cleaned"
