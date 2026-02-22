"""Atlas MCP server — single 'atlas' tool with dynamic description.

One tool, one string input.  The tool description changes on every
list_tools call to reflect the current project state (installed modules,
available verbs).  All routing goes through the Atlas runtime class.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    GetPromptResult,
    Prompt,
    PromptMessage,
    Resource,
    TextContent,
    Tool,
)

from atlas.core.errors import error_result
from atlas.parser import parse_input
from atlas.runtime import Atlas

# ---------------------------------------------------------------------------
# Module-level Atlas instance (one per server session)
# ---------------------------------------------------------------------------

_atlas: Atlas | None = None


def _get_atlas() -> Atlas:
    global _atlas
    if _atlas is None:
        _atlas = Atlas()
    return _atlas


# ---------------------------------------------------------------------------
# Dynamic description helpers
# ---------------------------------------------------------------------------


def build_description(atlas: Atlas) -> str:
    """Return the dynamic tool description based on project state."""
    if not atlas.is_initialized:
        return "Atlas project assistant. Run: atlas init — or: atlas list"

    modules = ", ".join(atlas.installed_modules)
    verbs = ["add", "create", "edit", "remove", "list", "sync"]

    if (
        atlas.router.find_all_with_command("check")
        or atlas.router.find_all_with_command("test")
    ):
        verbs.append("just")
    if atlas.router.has_category_installed("vcs"):
        verbs.append("vcs")
    if atlas.router.has_category_installed("platform"):
        verbs.append("crud")

    return (
        f"Atlas project assistant.\n"
        f"Modules: {modules}\n"
        f"Verbs: {', '.join(verbs)}\n"
        f"Retrieve: atlas <module> [filter] — "
        f"Syntax: spaces filter, commas combine, -- separates\n"
        f"Help: atlas list"
    )


def build_input_help(atlas: Atlas) -> str:
    """Return the dynamic input field description."""
    if not atlas.is_initialized:
        return (
            "Atlas command string. "
            "Examples: 'init', 'list', 'list modules'"
        )

    examples: list[str] = []
    for name in atlas.installed_modules[:3]:
        examples.append(f"'{name}'")
    if len(atlas.installed_modules) > 1:
        pair = ", ".join(atlas.installed_modules[:2])
        examples.append(f"'{pair}'")

    example_str = ", ".join(examples) if examples else "'python', 'python linter'"
    return (
        f"Atlas command string. "
        f"Retrieve: {example_str}. "
        f"Verb: 'add <module>', 'just <task>', 'list modules'. "
        f"Passthrough: '<module> -- <message>'."
    )


# ---------------------------------------------------------------------------
# Result serialisation
# ---------------------------------------------------------------------------


def _serialise(result: object) -> str:
    """Convert a result to a plain string for the MCP TextContent."""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return json.dumps(result, indent=2, ensure_ascii=False)
    return str(result)


def build_prompt_list() -> list[Prompt]:
    """Return the list of MCP prompts Atlas exposes."""
    return [
        Prompt(
            name="atlas-context",
            description="Project context — auto-injected at session start",
            arguments=[],
        )
    ]


def build_prompt_result(atlas: Atlas, name: str) -> GetPromptResult:
    """Build the GetPromptResult for the named prompt."""
    if name != "atlas-context":
        raise ValueError(f"Unknown prompt: {name!r}")
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


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

server = Server("atlas")


@server.list_tools()
async def list_tools() -> list[Tool]:
    atlas = _get_atlas()
    return [
        Tool(
            name="atlas",
            description=build_description(atlas),
            inputSchema={
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "description": build_input_help(atlas),
                    }
                },
                "required": ["input"],
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name != "atlas":
        result = error_result("INVALID_ARGUMENT", f"Unknown tool: {name}")
        return [TextContent(type="text", text=_serialise(result))]

    raw = arguments.get("input", "")
    atlas = _get_atlas()
    parsed = parse_input(raw)

    # Route to Atlas handlers
    if parsed.verb is None:
        result = atlas.query(parsed.contexts, parsed.message)
    elif parsed.verb == "init":
        result = atlas.init(parsed.args)
    elif parsed.verb == "add":
        result = atlas.add_modules(parsed.args)
    elif parsed.verb in ("create", "edit", "remove") and parsed.resource_type:
        result = atlas.manage_resource(parsed.verb, parsed.resource_type, parsed.args)
    elif parsed.verb == "remove":
        result = atlas.remove_module(parsed.args[0] if parsed.args else "")
    elif parsed.verb == "list":
        result = atlas.list_resources(parsed.args[0] if parsed.args else "all")
    elif parsed.verb == "just":
        result = atlas.just(
            parsed.args[0] if parsed.args else "",
            parsed.args[1:],
        )
    elif parsed.verb == "vcs":
        result = atlas.vcs(parsed.args)
    elif parsed.verb == "crud":
        result = atlas.crud(parsed.args)
    elif parsed.verb == "sync":
        result = atlas.sync(parsed.args)
    else:
        result = error_result("INVALID_ARGUMENT", f"Unknown verb: {parsed.verb}")

    return [TextContent(type="text", text=_serialise(result))]


@server.list_resources()
async def list_resources() -> list[Resource]:
    atlas = _get_atlas()
    resources: list[Resource] = []

    if not atlas.is_initialized:
        return resources

    retrieve_dir = Path(atlas.atlas_dir) / "retrieve"
    if not retrieve_dir.is_dir():
        return resources

    for md_file in sorted(retrieve_dir.glob("*.md")):
        module_name = md_file.stem
        resources.append(
            Resource(
                uri=f"atlas://retrieve/{module_name}",
                name=f"Atlas: {module_name}",
                description=f"Pre-built retrieve context for module '{module_name}'",
                mimeType="text/markdown",
            )
        )

    return resources


@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    return build_prompt_list()


@server.get_prompt()
async def get_prompt(name: str, arguments: dict | None = None) -> GetPromptResult:
    return build_prompt_result(_get_atlas(), name)


@server.read_resource()
async def read_resource(uri: str) -> str:
    prefix = "atlas://retrieve/"
    if not uri.startswith(prefix):
        return ""

    module_name = uri[len(prefix):]
    atlas = _get_atlas()
    md_path = Path(atlas.atlas_dir) / "retrieve" / f"{module_name}.md"

    if not md_path.is_file():
        return ""

    try:
        return md_path.read_text(encoding="utf-8")
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main_sync() -> None:
    """Synchronous entry point for console_scripts."""
    import asyncio

    async def _run() -> None:
        async with stdio_server() as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())

    asyncio.run(_run())


if __name__ == "__main__":
    main_sync()
