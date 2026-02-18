# Installation

## Requirements

- Python 3.10 or newer
- An MCP-compatible editor (Claude Desktop, Zed, Cursor, etc.)

## Zero-install (recommended)

```bash
# No installation needed — uvx runs atlas-mcp in an isolated env
uvx atlas-mcp
```

Configure your editor to use `uvx`:

```json
{
  "mcpServers": {
    "atlas": {
      "command": "uvx",
      "args": ["atlas-mcp"]
    }
  }
}
```

## Install as a global tool

```bash
uv tool install atlas-mcp
# or
pipx install atlas-mcp
```

## Install into a project venv

```bash
uv add atlas-mcp
# or
pip install atlas-mcp
```

## Verify installation

```bash
atlas --version
atlas status
```
