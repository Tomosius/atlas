# Atlas MCP

**One tool. Ten verbs. Instant project knowledge for AI coding agents.**

Atlas is an MCP (Model Context Protocol) server that gives AI coding agents structured knowledge about the project they are working in. It detects your stack, extracts real config values, and serves pre-built coding rules — instantly.

## Why Atlas?

When an AI agent starts working on your codebase, it knows nothing about your project. It doesn't know you use ruff with `line-length=88`, that your pytest markers are `unit` and `integration`, or that your project follows a specific commit convention.

Atlas solves this by pre-computing a set of **retrieve files** — Markdown docs with your actual config values injected — that agents can read in milliseconds.

```
agent: "atlas retrieve python ruff"
atlas: [returns rules.md with your actual ruff config values already injected]
```

## How it works

```
atlas init          → detect stack, install modules, build retrieve files
atlas retrieve ruff → serve pre-built rules instantly (file read, no computation)
atlas add pytest    → install module, rebuild retrieve files
atlas sync          → re-scan config, update changed values
atlas just test     → run tests, augment errors with relevant rule hints
```

## Install

```bash
# Zero-install with uvx (recommended)
uvx atlas-mcp

# Or install globally
uv tool install atlas-mcp
```

## Configure in your editor

=== "Claude Desktop"
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

=== "Zed"
    ```json
    {
      "context_servers": {
        "atlas": {
          "command": "uvx",
          "args": ["atlas-mcp"]
        }
      }
    }
    ```

## Quick navigation

- [Installation →](guides/installation.md)
- [How Atlas works →](guides/how-it-works.md)
- [All 10 verbs →](guides/api.md)
- [Module catalogue →](reference/modules-overview.md)
- [Development guide →](development.md)
