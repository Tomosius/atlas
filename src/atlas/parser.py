"""Universal input parser for the atlas MCP tool.

One tool, one string input.  The parser extracts:
- verb          — action word (init, add, create, edit, remove, list, just, vcs, crud, sync)
- resource_type — sub-type for create/edit/remove (note, prompt, task, scope)
- contexts      — retrieve query groups: [["python", "linter"], ["svelte"]]
- args          — remaining positional arguments
- message       — agent passthrough text after " -- "
"""

from __future__ import annotations

from dataclasses import dataclass, field

VERBS: frozenset[str] = frozenset({
    "init", "add", "create", "edit", "remove",
    "list", "just", "vcs", "crud", "sync",
})

RESOURCE_TYPES: frozenset[str] = frozenset({"note", "prompt", "task", "scope"})


@dataclass
class ParsedInput:
    """Structured representation of a single atlas tool invocation."""

    verb: str | None = None
    resource_type: str | None = None
    contexts: list[list[str]] = field(default_factory=list)
    args: list[str] = field(default_factory=list)
    message: str | None = None


def parse_input(raw: str) -> ParsedInput:
    """Parse a raw atlas tool input string into a :class:`ParsedInput`.

    Syntax rules:
    - First word is a verb → verb mode (args follow).
    - No verb → context query mode (commas combine, spaces filter).
    - ``" -- "`` separator extracts agent passthrough into ``message``.
    - ``create``/``edit`` + resource_type word → ``resource_type`` set, rest → ``args``.
    - ``remove`` + resource_type + ≥1 more word → ``resource_type`` set, rest → ``args``.
    """
    raw = raw.strip()
    result = ParsedInput()

    # Split on " -- " for agent passthrough
    if " -- " in raw:
        atlas_part, result.message = raw.split(" -- ", 1)
    else:
        atlas_part = raw

    words = atlas_part.split()
    if not words:
        return result

    first = words[0].lower()
    if first in VERBS:
        result.verb = first
        rest = words[1:]

        if result.verb in ("create", "edit") and rest and rest[0] in RESOURCE_TYPES:
            result.resource_type = rest[0]
            result.args = rest[1:]
        elif result.verb == "remove" and len(rest) >= 2 and rest[0] in RESOURCE_TYPES:
            result.resource_type = rest[0]
            result.args = rest[1:]
        else:
            result.args = rest
    else:
        # No verb → context query: split by comma, then by space
        groups = [g.strip() for g in atlas_part.split(",")]
        result.contexts = [g.split() for g in groups if g]

    return result
