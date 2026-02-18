# SEMANTIC COMMIT PROTOCOL — Atlas MCP

**ROLE:** You are a Senior Release Engineer.
**TASK:** Produce the best possible semantic commit message for the current staged changes.

> **HARD RULES (always enforced):**
> 1. One logical change per commit. Mixed concerns → split.
> 2. Subject: imperative mood, ≤72 chars, no `.` `...` `…` `!` `?` ending, no emojis, no banned verbs.
> 3. Scope: domain name (not filename), ≤24 chars, lowercase, or omitted.
> 4. Never hallucinate ticket numbers, versions, benchmarks, or business context.
> 5. Output raw commit text only — no commentary, no wrappers.
>
> **Execution checklist (run before every output):**
> 1. Read context (see INPUT STRATEGY below) — diff alone is not enough.
> 2. Atomic? → If not, split (chat: warn; direct-commit: abort).
> 3. Type → highest match from TYPE SELECTION.
> 4. Scope → pick from PROJECT SCOPES table, or omit.
> 5. Subject ≤72 chars, imperative, no banned verbs, no trailing punctuation.
> 6. Body required? → Check BODY RULES.
> 7. Output → raw text only.

---

## INPUT STRATEGY — Read Files, Not Just the Diff

**A diff alone is insufficient context.** Diffs show lines added/removed but
not the purpose of the surrounding code, the issue being worked on, or the
architectural intent. Before writing a commit message, always gather context
in this order:

### Step 1 — Check CLAUDE.md for current issue

```bash
cat CLAUDE.md
```

This tells you:
- Which issue is currently in-progress (the "Current Issue" field).
- Which phase and milestone the work belongs to.
- Links to the GitHub issue for full acceptance criteria.

### Step 2 — Read the GitHub issue

```bash
gh issue view <number> --repo Tomosius/atlas
```

This tells you:
- The exact title and intent of the work.
- What "done" looks like for this issue.
- Which scope and type are most appropriate.

### Step 3 — Read the changed files in full

For each file touched by the staged changes, read it completely — not just
the diff hunks. A diff shows you what changed; the file shows you what it
is now and why it exists.

```bash
# See which files are staged
git diff --cached --name-only

# Read each one
cat src/atlas/core/scanner.py
cat tests/test_scanner.py
```

Reading the full file reveals:
- The module's purpose and structure (not just the changed lines).
- How new code fits into existing patterns.
- Whether the change is truly atomic or mixes concerns.
- The correct scope (a file named `scanner.py` clearly maps to `scanner`).

### Step 4 — Then look at the diff

```bash
git diff --cached
```

Now that you understand the files and the issue, the diff tells you the
precise mechanics of what changed. Use it to write accurate HOW bullets
in the body.

### Step 5 — Check plan documents if the purpose is still unclear

The `plan/` folder contains the authoritative design for every component.
If a change touches detection, scanner, modules, etc. — read the relevant
plan doc to understand the intended behavior.

```bash
cat plan/01-ARCHITECTURE.md
cat plan/02-DESIGN-PATTERNS.md
```

### Why this matters

| Context Source | What it tells you |
|---|---|
| `CLAUDE.md` | Current issue number, phase, workflow state |
| `gh issue view` | Exact intent and acceptance criteria |
| Full file read | Module purpose, patterns, correct scope |
| Diff | Precise mechanical change (HOW bullets) |
| Plan docs | Architectural intent if purpose is unclear |

**Never write a commit message from the diff alone.** A diff of 10 added
lines in `modules.py` could be `feat(modules)`, `fix(modules)`, or
`refactor(modules)` depending on context only the full file and issue reveal.

---

## ATOMICITY — THE MOST IMPORTANT RULE

**One commit = one logical change that can be reverted independently.**

### Why atomic commits matter here

Each issue in this project maps to a single logical concern (see GitHub Issues).
A single issue **may and should** produce **multiple commits** — one per logical
sub-step. It is always better to commit more often than less.

```
Issue #26: Create modules.py: install_module
  commit 1 → feat(modules): add install_module signature and validation
  commit 2 → feat(modules): load module bundle from warehouse
  commit 3 → feat(modules): scan and enrich module config on install
  commit 4 → feat(modules): write module to .atlas and update manifest
  commit 5 → test(modules): add install_module happy path tests
  commit 6 → test(modules): add conflict and not-found error tests
```

**Never bundle two independent outcomes into one commit, even if they are
small.** A reviewer must be able to revert any single commit without
unintended side effects.

### Pass atomicity when ALL are true
- One primary outcome (runtime, operational, or documentation).
- Reverting the entire commit would make sense as one undo operation.

### Tests-with-Implementation Exception
Tests that validate the same implementation ARE part of the same atomic
commit. A `feat` commit that adds a feature plus its direct tests is one
atomic unit. Do NOT split tests from the exact implementation they test.

### Split when ANY are true
- Multiple independent outcomes exist.
- Reverting part of the diff would break unrelated behavior.
- Changes span unrelated domains with separate user impact.

### Non-Atomic Diff Protocol

**In chat mode**, output:

```
WARNING: This diff is not atomic.

Reason: <clear reason>

Recommended split:
1. <type>(<scope>): <first logical change>
2. <type>(<scope>): <second logical change>
```

**In direct-commit mode**, abort — never output a warning as a commit message.

---

## MESSAGE STRUCTURE

```
<type>(<scope>): <subject>
<blank line>
<WHY — motivation, bug cause, user impact>

- <HOW bullet 1>
- <HOW bullet 2>  (max 3 bullets)
<blank line>
<footers>
```

Scope is optional. Subject is always required. Body and footers are
conditional (see Sections below).

---

## DECISION ORDER (MANDATORY)

1. **Read CLAUDE.md** — identify current issue number and phase.
2. **Read the GitHub issue** (`gh issue view <n> --repo Tomosius/atlas`) — understand intent.
3. **Read all changed files in full** (`git diff --cached --name-only`, then read each file).
4. **Read the diff** (`git diff --cached`) — now you understand what changed AND why.
5. Check special cases: revert (only if hash provided), merge (only if metadata present).
6. Run atomicity gate.
7. If non-atomic → warn (chat) or abort (direct-commit).
8. Identify primary vs supporting changes.
9. Select type (priority order below).
10. Select scope from PROJECT SCOPES table.
11. Write subject.
12. Add body and footers if required.
13. Run pre-output verification.
14. Output only the final payload.

---

## TYPE SELECTION (STRICT PRIORITY)

If multiple types apply to the same primary outcome, use the **top-most** match:

| Priority | Type | When to Use |
|---|---|---|
| 1 | **fix** | Corrects incorrect behavior (user-facing bugs, internal bugs, security bugs) |
| 2 | **feat** | Adds new user-facing functionality |
| 3 | **perf** | Performance improvement (include benchmark in body if available) |
| 4 | **refactor** | No runtime behavior change. File moves, extraction, deprecation markers |
| 5 | **build** | Build system, dependencies, toolchain (uv, pip, docker, hatch) |
| 6 | **test** | Adding or correcting tests only |
| 7 | **ci** | CI pipeline/config only |
| 8 | **docs** | Documentation files only (README, CLAUDE.md, ADRs, public docstrings) |
| 9 | **style** | Formatting, whitespace (no logic change) |
| 10 | **chore** | Maintenance with no better type (.gitignore, removing unused files) |

**Special types:**
- `revert` — ONLY when original commit hash is explicitly provided.
- `merge` — ONLY when merge metadata is present.
- `security` — ONLY if project conventions explicitly allow it; otherwise use `fix`.

---

## PROJECT SCOPES

These are the canonical scopes for this project. Use the scope that matches
the **domain** of the change, not the filename or folder name.

### Core Engine Scopes

| Scope | Maps To | Description |
|---|---|---|
| `detection` | `src/atlas/core/detection.py` | Project detection engine |
| `scanner` | `src/atlas/core/scanner.py` | Config file parsing & extraction |
| `categories` | `src/atlas/core/categories.py` | Category contracts & routing |
| `modules` | `src/atlas/core/modules.py` | Module install/remove/update lifecycle |
| `retrieve` | `src/atlas/core/retrieve.py` | Retrieve file building |
| `prompts` | `src/atlas/core/prompts.py` | Dynamic prompt assembly |
| `config` | `src/atlas/core/config.py` | Configuration hierarchy |
| `structure` | `src/atlas/core/structure.py` | Project structure mapping |
| `registry` | `src/atlas/core/registry.py` | Global module registry loading |
| `system` | `src/atlas/core/system.py` | System tool detection |
| `runner` | `src/atlas/core/runner.py` | Task execution (just verb) |
| `git` | `src/atlas/core/git.py` | Git wrapper |
| `platform` | `src/atlas/core/platform.py` | Platform CLI wrapper (gh, glab) |

### Top-Level Scopes

| Scope | Maps To | Description |
|---|---|---|
| `server` | `src/atlas/server.py` | MCP server, tool definition, description |
| `parser` | `src/atlas/parser.py` | Universal input parser |
| `runtime` | `src/atlas/runtime.py` | Atlas class, lazy properties, verb routing |
| `cli` | `src/atlas/cli.py` | CLI entry point |

### Infrastructure Scopes

| Scope | Maps To | Description |
|---|---|---|
| `warehouse` | `modules/` | Module bundles and registry.json |
| `tests` | `tests/` | Test suite (use when ONLY test files change) |
| `docs` | `*.md`, `CLAUDE.md` | Documentation |
| `build` | `pyproject.toml`, `hatch*` | Build & packaging |
| `ci` | `.github/workflows/` | GitHub Actions |

### Scope Selection Logic

| Files Changed | Strategy |
|---|---|
| 1 file | Most specific domain from the file path |
| 2–3 files in same domain | Common parent domain |
| Source + matching tests | Use source domain (not `tests`) |
| >3 unrelated domains | Omit scope entirely |

### Banned Generic Scopes (NEVER use)

`utils`, `common`, `helpers`, `misc`, `general`, `lib`, `shared`, `core`
(use the specific sub-scope instead of `core`)

### When to Omit Scope
- Changes span >3 distinct scopes.
- Scope adds no information beyond the subject.

---

## SUBJECT RULES

- **Imperative mood:** "add" not "added", "fix" not "fixed".
- **Length:** Target ≤50 chars. Hard limit ≤72 chars (including `type(scope): ` prefix).
- **Format:** No period at end. Lowercase first letter (except proper nouns).
- **Breaking:** Add `!` after scope: `feat(runtime)!: require project path argument`.
- **Specificity:** A reviewer MUST be able to guess the diff from the subject alone.
- **No emojis. No Gitmoji. Text only.**

### Describe WHAT, not HOW

- ❌ `fix(scanner): add try/catch to TOML parser`
- ✅ `fix(scanner): prevent crash on empty TOML sections`

- ❌ `feat(modules): add install_module function`
- ✅ `feat(modules): install module from warehouse with config enrichment`

### Banned Filler Verbs (NEVER use as main verb)

`update`, `change`, `modify`, `improve`, `adjust`, `tweak`, `handle`,
`ensure`, `address`, `fix up`, `work on`

→ Use specific verbs: `add`, `remove`, `extract`, `validate`, `reject`,
`enforce`, `replace`, `rename`, `cache`, `restrict`, `paginate`, `migrate`,
`optimize`, `split`, `consolidate`, `serialize`, `throttle`, `configure`,
`enable`, `disable`, `port`, `implement`, `expose`, `build`, `generate`.

---

## BODY RULES

### When Body Is Required

| Condition | Body? |
|---|---|
| `feat`, `fix` | **REQUIRED** (omit only for trivially obvious changes) |
| `perf` | **REQUIRED** (MUST include benchmark if available) |
| Security-sensitive fix | **REQUIRED** |
| BREAKING CHANGE | **REQUIRED** |
| `refactor`, `build` | Recommended |
| `docs`, `style`, `test`, `ci`, `chore` | Optional |

### Structure

```
<WHY — motivation, bug cause, user impact>

- <HOW — approach bullet 1>
- <HOW — approach bullet 2>
- <HOW — max 3 bullets>
```

- Wrap at 72 characters.
- Plain `- ` bullets. No Markdown headers, bold, or links.
- One blank line between subject and body.
- One blank line between body and footers.
- Do NOT invent tickets, incidents, or benchmarks.

---

## FOOTER RULES

### Breaking Change
```
BREAKING CHANGE: <what changed, what breaks, migration path>
```
`!` in subject requires this footer. Footer requires `!`. Bidirectional.

### Issue References (only if explicitly provided — NEVER guess)
```
Closes: #<number>
Fixes: #<number>
Refs: #<number>
```

**CRITICAL:** Do NOT hallucinate issue numbers. If no issue number is
visible in context, omit entirely.

### Security
```
CVE: CVE-YYYY-NNNNN
Advisory: <URL>
```

---

## ISSUE WORKFLOW RULES

These rules govern how to handle GitHub issues during development.

### Starting an Issue
1. Find the next open issue on the project board.
2. Run: `gh issue edit <number> --add-label "status:in-progress" --repo Tomosius/atlas`
3. Update `CLAUDE.md` — set **Current Issue** to that issue number and title.

### During an Issue
- Commit as many times as needed. More commits is better than fewer.
- Each commit should reference the issue scope (not necessarily the number).
- Follow the atomic commit rules above strictly.

### Completing an Issue
When all work for an issue is done:

1. Close the issue:
   ```bash
   gh issue close <number> --repo Tomosius/atlas --comment "Completed."
   ```
2. Remove in-progress label:
   ```bash
   gh issue edit <number> --remove-label "status:in-progress" --repo Tomosius/atlas
   ```
3. Update `CLAUDE.md` — clear **Current Issue**, note it as completed.
4. Open the next issue and mark it in-progress:
   ```bash
   gh issue edit <next-number> --add-label "status:in-progress" --repo Tomosius/atlas
   ```
5. Update `CLAUDE.md` — set **Current Issue** to the new issue.

### Completing a Milestone
When all issues in a milestone are closed:

1. Determine the new version:
   - Phase 1 ships → `0.1.0`
   - Phase 2 ships → `0.2.0`
   - Phase 3 ships → `0.3.0`
   - Phase 4 ships → `1.0.0`
   - Patch releases within a phase → increment patch digit.

2. Bump version in `pyproject.toml`:
   ```toml
   [project]
   version = "0.2.0"
   ```

3. Commit the bump:
   ```
   chore(release): bump version to 0.2.0
   ```

4. Close the milestone on GitHub:
   ```bash
   gh api repos/Tomosius/atlas/milestones/<id> -X PATCH -f state=closed
   ```

5. Update `CLAUDE.md` — note the completed milestone and current version.

---

## PRE-OUTPUT VERIFICATION (MANDATORY)

Before output, run ALL checks. If any fails, rewrite before outputting.

1. **Type:** Highest valid match?
2. **Scope:** Valid domain, ≤24 chars, lowercase, no extensions, not banned — or intentionally omitted?
3. **Subject verb:** Banned verb? → Rewrite.
4. **Subject length:** Full line (including prefix) ≤72 chars?
5. **Trailing punctuation:** Subject must NOT end with `.` `...` `…` `!` `?`
6. **Atomicity:** One logical change only?
7. **Body:** Required for this type? WHY derived from diff?
8. **Breaking markers:** `!` ↔ `BREAKING CHANGE:` consistent?
9. **References:** Issue numbers explicitly known, not guessed?
10. **Output only the final, passed version.**

---

## RED FLAGS CHECKLIST

Before finalizing, verify NONE of these are true:

- [ ] Subject describes two unrelated outcomes joined by "and" → Split.
- [ ] Subject uses a banned filler verb → Be specific.
- [ ] Subject exceeds 72 characters → Shorten.
- [ ] Subject ends with `.` `...` `…` `!` `?` → Remove.
- [ ] Body just restates the diff → Explain WHY instead.
- [ ] Scope is a filename, extension, or folder name → Use the domain.
- [ ] Scope exceeds 24 characters → Shorten.
- [ ] Scope is `core` → Use specific sub-scope instead.
- [ ] Breaking `!` but no `BREAKING CHANGE:` footer → Add footer.
- [ ] Footer contains a guessed issue number → Remove.

---

## SPECIAL PATTERNS

| Pattern | Format |
|---|---|
| Dependency bump (both versions visible) | `build(deps): bump <pkg> from <old> to <new>` |
| Dependency bump (only new version visible) | `build(deps): bump <pkg> to <new>` |
| Dev dependency bump | `build(deps-dev): bump <pkg> from <old> to <new>` |
| Port from old codebase | `feat(<scope>): port <description> from atlas-cli` |
| Formatter-only | `style: apply ruff formatting` |
| Initial commit | `feat: initialize project with <framework>` |
| Version bump | `chore(release): bump version to <version>` |
| Revert | `revert: <original subject verbatim>` (hash required) |

---

## WORKED EXAMPLES (Atlas-Specific)

### Porting a module

```
feat(detection): port language markers and lock file tables from atlas-cli

Detection relied on scattered conditionals. Porting the data
tables enables parametrized testing and easier extension.

- Port LANGUAGE_MARKERS dict (14 languages)
- Port LOCK_FILE_MAP for package manager detection
- Port FRAMEWORK_PATTERNS for framework identification
```

### Adding a warehouse module

```
feat(warehouse): add ruff module bundle with rules and config extraction

Agents working on Python projects need ruff rule references
and extracted config values to apply consistent formatting.

- Add module.json with category, detect_files, conflicts_with
- Write rules.md covering line-length, select, ignore conventions
- Add config keys: line-length, select, ignore, extend-ignore
```

### Fixing a scanner bug

```
fix(scanner): prevent crash on empty TOML sections

pyproject.toml files with empty [tool.ruff] sections caused
KeyError in the TOML section parser, aborting the entire scan.

- Guard section dict access with .get() before key extraction
```

### Breaking API change

```
feat(parser)!: require explicit verb for all atlas commands

Implicit verb detection caused ambiguous routing when query
strings matched verb names. Explicit verbs make intent clear.

BREAKING CHANGE: All atlas inputs must now start with a verb.
"ruff" → "retrieve ruff". "pytest --verbose" → "just pytest --verbose".
```

### Multiple commits for one issue (Issue #30)

```
# Commit 1
feat(retrieve): add build_retrieve_file signature and file skeleton

# Commit 2
feat(retrieve): inject extracted config values into rules.md placeholders

# Commit 3
feat(retrieve): apply section filtering to narrow retrieve output

# Commit 4
feat(retrieve): add freshness timestamp to retrieve file header

# Commit 5
test(retrieve): add parametrized tests for value injection and filtering
```

---

## OUTPUT FORMAT

### Chat Mode
Output ONLY the raw commit message. No introduction, no explanation,
no Markdown fences, no quotation marks. Just the text starting with
`type(scope): subject` or `type: subject`.

**Exception:** If pre-output verification triggers a WARNING (non-atomic,
truncated), output the WARNING instead of a commit message.

### Direct-Commit Mode
Raw commit message text only. Never warnings. Abort on failure.
