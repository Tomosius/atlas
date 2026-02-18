# Atlas

MCP server that gives AI coding agents structured project knowledge.

**[Documentation](https://tomosius.github.io/atlas/)**

## Installation

```bash
uvx atlas-mcp
```

## Usage

Configure in your MCP-compatible editor (Claude Desktop, Zed, etc.):

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

## Status

In beta — breaking changes may occur at any time.

## License

**Free to use during beta**, including for commercial internal use.

Licensed under the [Business Source License 1.1](LICENSE).  
Created by [Tomas Pecukevicius](https://github.com/Tomosius/atlas).

- Individual developers: free, forever.
- Companies using it as a tool: free during beta.
- Companies building a product on top of Atlas: [contact for a commercial license](mailto:pecukevicius@gmail.com).
- Converts to MIT on **2027-01-01**.

If you build something with Atlas, attribution is required — see [LICENSE](LICENSE).
