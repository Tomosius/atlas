# MCP Auto-Brief Prompt Handlers Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `list_prompts` and `get_prompt` MCP handlers to `server.py` so agents automatically receive project context at session start.

**Architecture:** Two module-level helper functions (`build_prompt_list`, `build_prompt_result`) are added to `server.py` and wired to `@server.list_prompts()` and `@server.get_prompt()` decorators. `build_session_brief()` already exists in `runtime.py` — no changes needed there. Tests go in `test_server.py` using the existing mock-Atlas pattern.

**Tech Stack:** Python, `mcp` library (`mcp.types.Prompt`, `GetPromptResult`, `PromptMessage`), pytest

---

### Task 1: Add `build_prompt_list` + `build_prompt_result` helpers and wire handlers

**Files:**
- Modify: `src/atlas/server.py`
- Test: `tests/test_server.py`

---

**Step 1: Write the failing tests**

Open `tests/test_server.py` and add this import at the top (with the existing server imports):

```python
from atlas.server import build_prompt_list, build_prompt_result
```

Then add this class at the bottom of the file:

```python
# ---------------------------------------------------------------------------
# build_prompt_list / build_prompt_result
# ---------------------------------------------------------------------------


class TestPromptHandlers:
    def test_list_prompts_always_returns_atlas_context(self):
        result = build_prompt_list()
        assert len(result) == 1
        assert result[0].name == "atlas-context"

    def test_list_prompts_contains_description(self):
        result = build_prompt_list()
        assert result[0].description
        assert isinstance(result[0].description, str)

    def test_get_prompt_not_initialized_returns_not_initialized_message(self):
        atlas = _make_atlas(initialized=False)
        result = build_prompt_result(atlas, "atlas-context")
        assert len(result.messages) == 1
        assert "not initialized" in result.messages[0].content.text

    def test_get_prompt_initialized_returns_brief(self):
        atlas = _make_atlas(initialized=True)
        atlas.build_session_brief.return_value = "# Atlas — my-project\nInstalled: python"
        result = build_prompt_result(atlas, "atlas-context")
        assert len(result.messages) == 1
        assert "my-project" in result.messages[0].content.text

    def test_get_prompt_unknown_name_returns_empty_messages(self):
        atlas = _make_atlas(initialized=True)
        result = build_prompt_result(atlas, "unknown-prompt")
        assert result.messages == []

    def test_get_prompt_result_has_user_role(self):
        atlas = _make_atlas(initialized=True)
        atlas.build_session_brief.return_value = "brief text"
        result = build_prompt_result(atlas, "atlas-context")
        assert result.messages[0].role == "user"

    def test_get_prompt_result_is_text_content(self):
        atlas = _make_atlas(initialized=True)
        atlas.build_session_brief.return_value = "brief text"
        result = build_prompt_result(atlas, "atlas-context")
        assert result.messages[0].content.type == "text"
```

**Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_server.py::TestPromptHandlers -v
```

Expected: `ImportError` — `cannot import name 'build_prompt_list'`

---

**Step 3: Implement the helpers and handlers in `server.py`**

In `src/atlas/server.py`, update the `mcp.types` import line (currently imports `Resource`, `TextContent`, `Tool`) to also import `Prompt`, `GetPromptResult`, `PromptMessage`:

```python
from mcp.types import (
    GetPromptResult,
    Prompt,
    PromptMessage,
    Resource,
    TextContent,
    Tool,
)
```

Then add these two helper functions after the `_serialise` function (before the `server = Server("atlas")` line):

```python
def build_prompt_list() -> list[Prompt]:
    """Return the list of MCP prompts Atlas exposes."""
    return [
        Prompt(
            name="atlas-context",
            description="Project context — auto-injected at session start",
        )
    ]


def build_prompt_result(atlas: Atlas, name: str) -> GetPromptResult:
    """Build the GetPromptResult for the named prompt."""
    if name != "atlas-context":
        return GetPromptResult(messages=[])
    if not atlas.is_initialized:
        text = "Atlas: project not initialized — run `atlas init`"
    else:
        text = atlas.build_session_brief()
    return GetPromptResult(
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(type="text", text=text),
            )
        ]
    )
```

Then add the two handlers after the existing `@server.list_resources()` handler (before `@server.read_resource()`):

```python
@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    return build_prompt_list()


@server.get_prompt()
async def get_prompt(name: str, arguments: dict | None = None) -> GetPromptResult:
    return build_prompt_result(_get_atlas(), name)
```

**Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_server.py::TestPromptHandlers -v
```

Expected: 7 passed

**Step 5: Run full suite to verify no regressions**

```bash
uv run pytest tests/ -q
```

Expected: all passing, 0 failures

**Step 6: Commit**

```bash
git add src/atlas/server.py tests/test_server.py
git commit -m "feat(server): add list_prompts and get_prompt MCP handlers (#94)"
```

---

### Task 2: Write issue body, close issue #94, open #95

**Step 1: Write the issue body**

```bash
gh issue edit 94 --body "## What
Add \`list_prompts\` and \`get_prompt\` MCP handlers to \`server.py\`.
The \`atlas-context\` prompt is always listed; \`get_prompt\` returns the
full session brief when initialized, or a 'not initialized' message otherwise.

## Acceptance criteria
- \`list_prompts\` always returns the \`atlas-context\` prompt
- \`get_prompt(\"atlas-context\")\` returns full brief when initialized
- \`get_prompt(\"atlas-context\")\` returns 'not initialized' message when not initialized
- \`get_prompt\` for unknown names returns empty messages list
- 7 new tests in \`test_server.py\`, all passing
- All existing tests still pass

## References
- plan/05-ATLAS-API.md §24 (MCP Auto-Brief)
- docs/plans/2026-02-22-auto-brief-prompt-design.md" --repo Tomosius/atlas
```

**Step 2: Close the issue**

```bash
gh issue close 94 --repo Tomosius/atlas --comment "Completed.

## What was built
Added \`build_prompt_list\` and \`build_prompt_result\` helpers to \`server.py\`
and wired them to \`@server.list_prompts()\` and \`@server.get_prompt()\`.
The \`atlas-context\` prompt is always listed; uninitialized projects receive
a 'not initialized' message.

## Acceptance criteria
- [x] \`list_prompts\` always returns the \`atlas-context\` prompt
- [x] \`get_prompt\` returns full brief when initialized
- [x] \`get_prompt\` returns 'not initialized' message when not initialized
- [x] Unknown prompt names return empty messages list
- [x] 7 new tests in \`test_server.py\`, all passing
- [x] All existing tests still pass"
```

**Step 3: Remove in-progress label and set board to Done**

```bash
gh issue edit 94 --remove-label "status:in-progress" --repo Tomosius/atlas

ITEM_ID=$(gh project item-list 21 --owner Tomosius --format json | \
  python3 -c "import json,sys; [print(i['id']) for i in json.load(sys.stdin)['items'] if i.get('content',{}).get('number')==94]")
gh project item-edit --project-id PVT_kwHOAbrAN84BPiZJ --id $ITEM_ID \
  --field-id PVTSSF_lAHOAbrAN84BPiZJzg96unA --single-select-option-id 98236657
```

**Step 4: Mark #95 in-progress**

```bash
gh issue edit 95 --add-label "status:in-progress" --repo Tomosius/atlas

NEXT_ITEM_ID=$(gh project item-list 21 --owner Tomosius --format json | \
  python3 -c "import json,sys; [print(i['id']) for i in json.load(sys.stdin)['items'] if i.get('content',{}).get('number')==95]")
gh project item-edit --project-id PVT_kwHOAbrAN84BPiZJ --id $NEXT_ITEM_ID \
  --field-id PVTSSF_lAHOAbrAN84BPiZJzg96unA --single-select-option-id 47fc9ee4
```

**Step 5: Update CLAUDE.md**

In `CLAUDE.md`:
- Change `**Current Issue:** #94 — ...` to `**Current Issue:** #95 — <title of #95>`
- Add row to completed table: `| #94 | Implement MCP auto-brief prompt: list_prompts + get_prompt handlers | ✅ \`src/atlas/server.py\`, \`tests/test_server.py\` |`

**Step 6: Commit**

```bash
git add CLAUDE.md
git commit -m "chore(meta): update CLAUDE.md after completing issue #94"
```
