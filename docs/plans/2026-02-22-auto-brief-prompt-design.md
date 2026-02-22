# Design: MCP Auto-Brief Prompt Handlers (Issue #94)

## What We're Building

Two MCP prompt handlers in `src/atlas/server.py`:
- `list_prompts` — always returns a single `atlas-context` prompt entry
- `get_prompt` — returns the full session brief when initialized, or a
  "not initialized" message otherwise

## Reference

- `plan/05-ATLAS-API.md §24` — MCP Auto-Brief spec
- `src/atlas/server.py` — implementation target
- `src/atlas/runtime.py:333` — `build_session_brief()` (already implemented)
- `tests/test_server.py` — test target

## Approach

Always list the `atlas-context` prompt regardless of init state. `get_prompt`
returns either the full brief (initialized) or a short "not initialized"
message. This is more useful than returning `[]` from `list_prompts` when not
initialized, since it means agents always have a hook to inject project context.

## Changes

### `src/atlas/server.py`

**New imports:**
```python
from mcp.types import Prompt, GetPromptResult, PromptMessage
```
(add to existing `mcp.types` import line)

**Two new module-level helpers** (testable without async):
```python
def build_prompt_list() -> list[Prompt]:
    return [Prompt(
        name="atlas-context",
        description="Project context — auto-injected at session start",
    )]

def build_prompt_result(atlas: Atlas, name: str) -> GetPromptResult:
    if name != "atlas-context":
        return GetPromptResult(messages=[])
    if not atlas.is_initialized:
        text = "Atlas: project not initialized — run `atlas init`"
    else:
        text = atlas.build_session_brief()
    return GetPromptResult(messages=[
        PromptMessage(role="user", content=TextContent(type="text", text=text))
    ])
```

**Two new handlers** wired to the server:
```python
@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    return build_prompt_list()

@server.get_prompt()
async def get_prompt(name: str, arguments: dict | None = None) -> GetPromptResult:
    return build_prompt_result(_get_atlas(), name)
```

### `tests/test_server.py`

New imports:
```python
from atlas.server import build_prompt_list, build_prompt_result
```

New class `TestPromptHandlers` with 7 tests:

| Test | Asserts |
|---|---|
| `test_list_prompts_always_returns_atlas_context` | result has one prompt named `"atlas-context"` |
| `test_list_prompts_contains_description` | description field is non-empty string |
| `test_get_prompt_not_initialized_returns_not_initialized_message` | text contains "not initialized" |
| `test_get_prompt_initialized_returns_brief` | calls `build_session_brief()`, returns its output |
| `test_get_prompt_unknown_name_returns_empty_messages` | unknown name → `messages == []` |
| `test_get_prompt_result_has_user_role` | message role is `"user"` |
| `test_get_prompt_result_is_text_content` | content type is `"text"` |

## Acceptance Criteria

- `list_prompts` and `get_prompt` handlers registered on the MCP server
- `build_prompt_list` and `build_prompt_result` exported from `server.py`
- 7 new tests in `test_server.py`, all passing
- All existing tests still pass (no regressions)
