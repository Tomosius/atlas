# Atlas MCP — Agent Context

MCP server that gives AI coding agents structured project knowledge.
One tool (`atlas`), 10 verbs, single string input.

---

## Project Links

| Resource | URL |
|---|---|
| Repository | https://github.com/Tomosius/atlas |
| Project Board | https://github.com/users/Tomosius/projects/21 |
| All Issues | https://github.com/Tomosius/atlas/issues |
| Phase 1 Issues | https://github.com/Tomosius/atlas/milestone/1 |
| Phase 2 Issues | https://github.com/Tomosius/atlas/milestone/2 |
| Phase 3 Issues | https://github.com/Tomosius/atlas/milestone/3 |
| Phase 4 Issues | https://github.com/Tomosius/atlas/milestone/4 |

---

## Current Status

**Version:** `0.1.0` (pre-release, in development)
**Active Phase:** Phase 1 — The Foundation
**Current Issue:** None — pick the next open issue from Phase 1

### How to find the next issue to work on

```bash
# List open Phase 1 issues, ordered by number
gh issue list --repo Tomosius/atlas --label "phase:1" --state open --limit 50

# See what is currently in-progress
gh issue list --repo Tomosius/atlas --label "status:in-progress"
```

---

## Milestones

| # | Title | Issues | Status |
|---|---|---|---|
| 1 | Phase 1 — The Foundation | 114 issues (#1–#114) | In Progress |
| 2 | Phase 2 — Workflow & Intelligence | 65 issues (#115–#179) | Pending |
| 3 | Phase 3 — Advanced Intelligence | 8 issues (#180–#187) | Pending |
| 4 | Phase 4 — God Mode | 4 issues (#188–#191) | Pending |

---

## Issue Workflow (follow exactly)

### Starting an issue

1. Pick the lowest-numbered open issue in the current phase.
2. Mark it in-progress:
   ```bash
   gh issue edit <number> --add-label "status:in-progress" --repo Tomosius/atlas
   ```
3. Update the **Current Issue** line above.

### During an issue

- Make as many atomic commits as needed — more is better than fewer.
- Each commit must follow `COMMIT_RULES.md` exactly.
- One issue can produce 2, 5, or 10 commits — that is correct and expected.
- Do not mix work from different issues in the same commit.

### Completing an issue

Run these commands in order:

```bash
# 1. Close the issue with a completion comment
gh issue close <number> --repo Tomosius/atlas --comment "Completed."

# 2. Remove the in-progress label
gh issue edit <number> --remove-label "status:in-progress" --repo Tomosius/atlas

# 3. Mark the next issue as in-progress
gh issue edit <next-number> --add-label "status:in-progress" --repo Tomosius/atlas
```

Then update this file:
- Set **Current Issue** to the new issue number and title.

### Completing a milestone

When all issues in a milestone are closed:

1. Bump version in `pyproject.toml` (see version table below).
2. Commit: `chore(release): bump version to <version>`
3. Close the milestone:
   ```bash
   gh api repos/Tomosius/atlas/milestones/<milestone-number> -X PATCH -f state=closed
   ```
4. Update **Version** and **Active Phase** in this file.

### Version table

| Milestone Completed | Version |
|---|---|
| Phase 1 — The Foundation | `0.1.0` |
| Phase 2 — Workflow & Intelligence | `0.2.0` |
| Phase 3 — Advanced Intelligence | `0.3.0` |
| Phase 4 — God Mode | `1.0.0` |
| Patch fix within a phase | increment patch (e.g. `0.1.1`) |

---

## Commit Rules

All commits must follow `COMMIT_RULES.md` in the project root.

Key points:
- **Atomic commits** — one logical change per commit.
- **One issue = many commits** — split work into small, logical steps.
- Use project scopes from `COMMIT_RULES.md` (e.g. `detection`, `scanner`, `modules`, `retrieve`, `server`, `parser`, `runtime`, `warehouse`).
- Never use `core` as a scope — use the specific sub-scope.
- Close issues with `gh issue close`, not just by merging.

---

## Architecture Overview

```
src/atlas/
  server.py       — MCP server, single "atlas" tool, dynamic description
  parser.py       — Universal input parser (verb + query + -- passthrough)
  runtime.py      — Atlas class, lazy properties, verb routing
  cli.py          — Thin CLI wrapper
  core/
    detection.py  — Language/framework/database detection engine
    scanner.py    — Config file parsing (TOML, JSON, INI, YAML, go.mod)
    categories.py — 13 category contracts + CategoryRouter
    modules.py    — Module install/remove/update lifecycle
    retrieve.py   — Retrieve file builder (rules + extracted values)
    prompts.py    — Dynamic prompt assembly with fragments
    config.py     — Config hierarchy (project > global > defaults)
    structure.py  — Project directory layout mapping
    registry.py   — Global module registry loader
    system.py     — System tool detection
    runner.py     — Task execution (just verb)
    git.py        — Git subprocess wrapper
    platform.py   — Platform CLI wrapper (gh, glab)
modules/
  registry.json   — All 61 module definitions
  languages/      — Language module bundles
  linters/        — Linter module bundles
  formatters/     — Formatter module bundles
  testing/        — Testing framework bundles
  frameworks/     — Web/app framework bundles
  databases/      — Database module bundles
  vcs/            — VCS module bundles
  platforms/      — Platform module bundles (github, gitlab)
  pkg-managers/   — Package manager bundles
  environments/   — Environment bundles (docker, venv)
  ci-cd/          — CI/CD bundles
  stacks/         — Stack bundles (python-backend, ts-frontend, etc.)
  tools/          — Tool bundles (commit-rules, etc.)
  prompts/        — Prompt templates (design, review, debug, king-mode)
tests/
plan/             — Architecture and design documents (read-only reference)
```

### Design Principles (from plan/02-DESIGN-PATTERNS.md)

1. Data tables over code branches — detection uses dicts, not if/elif chains.
2. Result dicts over exceptions — `{"ok": True, "data": ...}` or `{"ok": False, "error": ...}`.
3. Pre-compute then read — build retrieve files at init/add/sync time; serve as instant file reads.
4. No global state in core — all functions take explicit arguments.
5. No network calls — warehouse lives on disk, ships with the package.
6. No package installation — never run pip/uv install at runtime.
7. stdlib-only core — only `server.py` imports `mcp`.

---

## Plan Documents (Reference Only)

Do not modify these — they are the source of truth for what to build.

| File | Contents |
|---|---|
| `plan/00-PROJECT-PLAN.md` | Vision, 4 phases, success criteria |
| `plan/01-ARCHITECTURE.md` | Package layout, module lifecycle, retrieve builder |
| `plan/02-DESIGN-PATTERNS.md` | 13 patterns, 8 anti-patterns |
| `plan/03-IMPLEMENTATION-GUIDE.md` | 22 numbered build steps with code examples |
| `plan/04-PYPROJECT-REFERENCE.toml` | Complete pyproject.toml template |
| `plan/05-ATLAS-API.md` | Full API: 1 tool, 10 verbs, syntax rules, parser grammar |
| `plan/06-MODULE-REGISTRY.md` | All 61 modules, bundle format, registry schema |
| `plan/07-GITHUB-PROJECT.md` | All 191 issues, labels, milestones, CI config |
| `plan/08-MODULE-SPEC.md` | Module creation spec, required fields, validation |
