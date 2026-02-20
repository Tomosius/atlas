"""Atlas CLI — thin wrapper around the Atlas runtime.

Provides a terminal interface that mirrors the MCP tool's single-string
input model.  All routing goes through the same Atlas runtime class used
by the MCP server.

Usage:
    atlas <input>        # e.g. "atlas python", "atlas init", "atlas add ruff"
    atlas                # prints current status / help
"""

from __future__ import annotations

import json
import sys

from atlas.core.errors import error_result
from atlas.parser import parse_input
from atlas.runtime import Atlas


def _print_result(result: object) -> None:
    """Print a result to stdout in a human-readable form."""
    if isinstance(result, str):
        print(result)
    elif isinstance(result, dict):
        if result.get("ok") is False:
            # Error — print error code + detail to stderr
            msg = result.get("detail") or result.get("error") or str(result)
            print(f"Error: {msg}", file=sys.stderr)
        else:
            # Success dict — pretty-print as JSON
            print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(str(result))


def run(raw: str, project_dir: str | None = None) -> int:
    """Parse *raw*, route to Atlas, print the result.

    Returns 0 on success, 1 on error.
    """
    atlas = Atlas(project_dir)
    parsed = parse_input(raw)

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

    _print_result(result)

    if isinstance(result, dict) and result.get("ok") is False:
        return 1
    return 0


def main() -> None:
    """Console script entry point: ``atlas``."""
    # Join all CLI arguments as a single space-separated string,
    # matching the MCP tool's single-string-input model.
    raw = " ".join(sys.argv[1:])
    sys.exit(run(raw))
