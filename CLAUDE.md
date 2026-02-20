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
**Current Issue:** #76 — Create module bundle: vcs/git

### Completed so far

| Issue | Title | Notes |
|---|---|---|
| #1 | src layout + pyproject.toml | ✅ hatchling, entry points, ruff, basedpyright, pytest |
| #2 | Create CLAUDE.md | ✅ this file |
| #3 | Create README.md | ✅ |
| #4 | Set up CI via GitHub Actions | ✅ `.github/workflows/ci.yml` |
| #5 | Create test fixtures | ✅ `tests/fixtures/empty_project/` |
| #6 | Port data models | ✅ `src/atlas/core/models.py` |
| #7 | Port error codes | ✅ `src/atlas/core/errors.py` |
| #8 | Port system utilities | ✅ `src/atlas/core/system.py` |
| #9 | Port detection engine | ✅ `src/atlas/core/detection.py` |
| #10 | Write tests for detection engine | ✅ 153 tests, `tests/test_detection.py` |
| #11 | Port config scanner: MODULE_CONFIG_MAP | ✅ 72 entries, `src/atlas/core/scanner.py` |
| #12 | Port config scanner: MODULE_CONFIG_KEYS | ✅ 19 entries |
| #13 | Port TOML section parser | ✅ |
| #14 | Port JSON, INI, YAML, go.mod parsers | ✅ |
| #15 | Port scan_module_config and enrich_module_rules | ✅ |
| #16 | Write tests for config scanner | ✅ 124 tests, `tests/test_scanner.py` |
| #17 | Port category contracts (13 categories + 2 auto) | ✅ `src/atlas/core/categories.py` |
| #18 | Port CategoryRouter class | ✅ `CategoryRouter` in `src/atlas/core/categories.py` |
| #19 | Port validate_module_against_contract and validate_registry_integrity | ✅ `src/atlas/core/categories.py` |
| #20 | Write tests for categories (port 67 existing tests) | ✅ 73 tests, `tests/test_categories.py` |
| #21 | Create registry.py: load_registry, find_module, check_conflicts | ✅ `src/atlas/core/registry.py` |
| #22 | Create registry.py: load_module_bundle, load_module_rules_md | ✅ `src/atlas/core/registry.py` |
| #23 | Create registry.py: get_recommendations | ✅ `src/atlas/core/registry.py` |
| #24 | Write tests for registry | ✅ 53 tests, `tests/test_registry.py` |
| #25 | Port PKG_VARIABLES (8 package managers) | ✅ `src/atlas/core/modules.py` |
| #26 | Create modules.py: install_module | ✅ `src/atlas/core/modules.py` |
| #27 | Create modules.py: remove_module | ✅ `src/atlas/core/modules.py` |
| #28 | Create modules.py: update_modules | ✅ `src/atlas/core/modules.py` |
| #29 | Write tests for module lifecycle | ✅ 45 tests, `tests/test_modules.py` |
| #30 | Create retrieve.py: build_retrieve_file | ✅ `src/atlas/core/retrieve.py` |
| #31 | Create retrieve.py: build_status_file | ✅ implemented as part of #30 |
| #32 | Create retrieve.py: build_all_retrieve_files | ✅ implemented as part of #30 |
| #33 | Create retrieve.py: value injection | ✅ `_inject_values` in `retrieve.py` |
| #34 | Create retrieve.py: section filtering | ✅ `filter_sections` in `retrieve.py` |
| #35 | Write tests for retrieve builder | ✅ 59 tests, `tests/test_retrieve.py` |
| #36 | Port config hierarchy (project > global > defaults) | ✅ `src/atlas/core/config.py` |
| #37 | Create AtlasConfig dataclass | ✅ implemented as part of #36 |
| #38 | Write tests for config hierarchy and merge logic | ✅ 31 tests, `tests/test_config.py` |
| #39 | Create runner.py: execute tasks via subprocess | ✅ `src/atlas/core/runner.py` |
| #40 | Create runner.py: tool resolution cascade | ✅ `resolve_tool` in `runner.py` |
| #41 | Write tests for runner | ✅ 21 tests, `tests/test_runner.py` |
| #42 | Create parser.py: ParsedInput dataclass | ✅ `src/atlas/parser.py` |
| #43 | Create parser.py: parse_input() | ✅ `src/atlas/parser.py` |
| #44 | Write tests for parser | ✅ 68 tests, `tests/test_parser.py` |

| #45 | Create runtime.py: Atlas class with lazy properties | ✅ `src/atlas/runtime.py` |
| #46 | Create runtime.py: warehouse path resolution | ✅ `_find_warehouse` in `runtime.py` |
| #47 | Create runtime.py: invalidate() method | ✅ `runtime.py` |
| #48 | Create runtime.py: verb handlers | ✅ `add_modules`, `remove_module`, `just` in `runtime.py` |
| #49 | Create runtime.py: query handler | ✅ `query()` in `runtime.py` |
| #50 | Create runtime.py: notes management | ✅ `add_note`, `remove_note` in `runtime.py` |
| #51 | Create runtime.py: save helpers | ✅ `save_manifest`, `save_notes`, `save_config` |
| #52 | Write tests for Atlas runtime | ✅ 62 tests, `tests/test_runtime.py` |
| #53 | Create server.py: MCP Server instance with single atlas tool | ✅ `src/atlas/server.py` |
| #54 | Create server.py: build_description() | ✅ implemented as part of #53 |
| #55 | Create server.py: build_input_help() | ✅ implemented as part of #53 |
| #56 | Create server.py: call_tool handler | ✅ implemented as part of #53 |
| #57 | Create server.py: list_resources handler | ✅ implemented as part of #53 |
| #58 | Create server.py: main_sync() entry point | ✅ implemented as part of #53 |
| #59 | Write tests for server | ✅ 28 tests, `tests/test_server.py` |
| #60 | Create cli.py: thin CLI wrapper | ✅ `src/atlas/cli.py` |
| #61 | Write tests for CLI | ✅ 24 tests, `tests/test_cli.py` |
| #62 | Create modules/registry.json with all fields | ✅ 69 modules, `modules/registry.json` |
| #63 | Create module bundle: languages/python | ✅ `modules/languages/python/` |
| #64 | Create module bundle: languages/typescript | ✅ `modules/languages/typescript/` |
| #65 | Create module bundle: languages/rust | ✅ `modules/languages/rust/` |
| #66 | Create module bundle: languages/go | ✅ `modules/languages/go/` |
| #67 | Create module bundle: linters/ruff | ✅ `modules/linters/ruff/` |
| #68 | Create module bundle: linters/eslint | ✅ `modules/linters/eslint/` |
| #69 | Create module bundle: linters/biome | ✅ `modules/linters/biome/` |
| #70 | Create module bundle: linters/clippy | ✅ `modules/linters/clippy/` |
| #71 | Create module bundle: formatters/prettier | ✅ `modules/formatters/prettier/` |
| #72 | Create module bundle: formatters/rustfmt | ✅ `modules/formatters/rustfmt/` |
| #73 | Create module bundle: testing/pytest | ✅ `modules/testing/pytest/` |
| #74 | Create module bundle: testing/vitest | ✅ `modules/testing/vitest/` |
| #75 | Create module bundle: testing/jest | ✅ `modules/testing/jest/` |

### Not yet started (next up)

Continue: #76, #77 … through #114.

```bash
# See all open Phase 1 issues
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

### Project board IDs (do not change)

| Field | ID |
|---|---|
| Project ID | `PVT_kwHOAbrAN84BPiZJ` |
| Status field ID | `PVTSSF_lAHOAbrAN84BPiZJzg96unA` |
| Status: Todo | `f75ad846` |
| Status: In Progress | `47fc9ee4` |
| Status: Done | `98236657` |

Get the project item ID for an issue number:
```bash
gh project item-list 21 --owner Tomosius --format json | \
  python3 -c "import json,sys; [print(i['id']) for i in json.load(sys.stdin)['items'] if i.get('content',{}).get('number')==<number>]"
```

### Starting an issue

1. Pick the lowest-numbered open issue in the current phase.
2. Read `plan/07-GITHUB-PROJECT.md` and find the issue's row in the table to understand full context, scope, and what "done" looks like.
3. Write a description to the GitHub issue body — include: what to build, acceptance criteria, and relevant plan doc references:
   ```bash
   gh issue edit <number> --body "## What
   <what to build, 2-3 sentences from the plan>

   ## Acceptance criteria
   - <criterion 1>
   - <criterion 2>

   ## References
   - plan/07-GITHUB-PROJECT.md §<section>
   - plan/03-IMPLEMENTATION-GUIDE.md §<step> (if applicable)" --repo Tomosius/atlas
   ```
4. Mark it in-progress (label + project board):
   ```bash
   gh issue edit <number> --add-label "status:in-progress" --repo Tomosius/atlas

   # Get item ID then set project board status to In Progress
   ITEM_ID=$(gh project item-list 21 --owner Tomosius --format json | \
     python3 -c "import json,sys; [print(i['id']) for i in json.load(sys.stdin)['items'] if i.get('content',{}).get('number')==<number>]")
   gh project item-edit --project-id PVT_kwHOAbrAN84BPiZJ --id $ITEM_ID \
     --field-id PVTSSF_lAHOAbrAN84BPiZJzg96unA --single-select-option-id 47fc9ee4
   ```
5. Update the **Current Issue** line above.

### During an issue

- Make as many atomic commits as needed — more is better than fewer.
- Each commit must follow `COMMIT_RULES.md` exactly.
- One issue can produce 2, 5, or 10 commits — that is correct and expected.
- Do not mix work from different issues in the same commit.

### Completing an issue

Run these commands in order:

```bash
# 1. Close the issue with a completion comment — summarise what was built and confirm criteria met
gh issue close <number> --repo Tomosius/atlas --comment "Completed.

## What was built
<1-2 sentences describing what was implemented>

## Acceptance criteria
- [x] <criterion 1>
- [x] <criterion 2>"

# 2. Remove the in-progress label
gh issue edit <number> --remove-label "status:in-progress" --repo Tomosius/atlas

# 3. Set project board status to Done
ITEM_ID=$(gh project item-list 21 --owner Tomosius --format json | \
  python3 -c "import json,sys; [print(i['id']) for i in json.load(sys.stdin)['items'] if i.get('content',{}).get('number')==<number>]")
gh project item-edit --project-id PVT_kwHOAbrAN84BPiZJ --id $ITEM_ID \
  --field-id PVTSSF_lAHOAbrAN84BPiZJzg96unA --single-select-option-id 98236657

# 4. Mark the next issue as in-progress (label + project board)
gh issue edit <next-number> --add-label "status:in-progress" --repo Tomosius/atlas

NEXT_ITEM_ID=$(gh project item-list 21 --owner Tomosius --format json | \
  python3 -c "import json,sys; [print(i['id']) for i in json.load(sys.stdin)['items'] if i.get('content',{}).get('number')==<next-number>]")
gh project item-edit --project-id PVT_kwHOAbrAN84BPiZJ --id $NEXT_ITEM_ID \
  --field-id PVTSSF_lAHOAbrAN84BPiZJzg96unA --single-select-option-id 47fc9ee4
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
