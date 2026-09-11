# solution-finder — An MCP Server for AI Coding Agents

An MCP (Model Context Protocol) server that extends AI coding agents — Claude Code, Claude Desktop, Cursor, and any other MCP-compliant client — with two categories of capability: structured retrieval of external public data, and authenticated, permission-scoped actions on a user's behalf.

Built as an implementation of the [Coding Challenges: Build Your Own MCP Server](https://codingchallenges.fyi) project.

## Why this exists

Modern AI agents increasingly ship with general-purpose web browsing built in. That capability, however, has a hard boundary: it can only ever read what's already public. It cannot authenticate, and it cannot take a write action on a user's behalf.

This project draws a clear, working line across that boundary. `CodingChallengesSolutionFinder` sits on one side — a structured, deterministic lookup an agent could partially approximate itself. `create_github_issue` sits on the other — a real, authenticated write action against a user's account, gated by a narrowly scoped access token, something no general-purpose browsing tool can replicate. The distinction is the point of the project.

## Tools exposed

| Tool | What it does | Auth required | Data class |
|---|---|---|---|
| `hello(name)` | Returns a greeting — protocol sanity check | No | N/A |
| `CodingChallengesSolutionFinder(challenge_name)` | Fetches and parses the CodingChallengesFYI/SharedSolutions README for matching challenge solutions | No | Public, read-only |
| `create_github_issue(repo, title, body)` | Creates a real GitHub issue via the GitHub REST API | Yes — scoped personal access token | Private/authenticated, write |
| `list_github_issues(repo)` | Lists open issues in a GitHub repo via the GitHub REST API | Yes — scoped personal access token | Private/authenticated, read |

## Architecture

```
User (natural language)
        │
        ▼
MCP Client (Claude Code / Claude Desktop / any MCP-compliant client)
        │  tools/list → discovers available tools
        │  tools/call → invokes one with structured input
        ▼
This MCP Server (stdio transport)
        │
        ├─→ httpx.get()  → GitHub README (public data)
        └─→ httpx.post() → GitHub REST API (authenticated write, scoped token)
        │
        ▼
Structured result returned to the agent, then the user
```

The server speaks MCP's standard JSON-RPC protocol over stdio, meaning it required zero client-specific integration code — the same `server.py`, unmodified, was verified against multiple independent MCP clients.

## Security model

- Authentication uses a fine-grained GitHub personal access token, scoped to exactly two permissions: **Issues: Read and write** and **Pull requests: Read and write**. No broader account access is granted.
- The token is read from the environment at call time (`os.environ.get("GITHUB_TOKEN")`) inside each tool that needs it, and is never hardcoded, logged, or committed to source control. The server starts and serves unauthenticated tools regardless of whether the token is present; authenticated tools return a clear error message if it is unset.
- All external calls are wrapped in explicit error handling — network failures and unexpected API responses return a clean message to the calling agent rather than an unhandled exception.

## Setup

### 1. Install

```bash
git clone <this-repo-url>
cd mcp-server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure a GitHub token (required only for `create_github_issue`)

Create a fine-grained personal access token scoped to the specific repositories you want writable, with **Issues: Read and write** and **Pull requests: Read and write** permissions.

```bash
export GITHUB_TOKEN="your_token_here"
```

### 3. Verify with the MCP Inspector

```bash
npx @modelcontextprotocol/inspector python3 server.py
```

> **Note:** The MCP SDK's `StdioClientTransport` only forwards a small allowlist of environment variables (`HOME`, `PATH`, `USER`, etc.) to the subprocess — `GITHUB_TOKEN` is intentionally excluded. After the Inspector opens in your browser, add `GITHUB_TOKEN` in the **Environment Variables** panel of the connection config before clicking Connect.

### 4. Connect to a client

**Claude Code:**

```bash
claude mcp add solution-finder --scope user -- /path/to/.venv/bin/python3 /path/to/server.py
```

**Claude Desktop** — add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "solution-finder": {
      "command": "/path/to/.venv/bin/python3",
      "args": ["/path/to/server.py"],
      "env": { "GITHUB_TOKEN": "your_token_here" }
    }
  }
}
```

## Example interaction

```
> Is there a shared solution for the Redis coding challenge?

Build your own Redis Server: https://github.com/CodingChallengesFYI/SharedSolutions/blob/main/Solutions/challenge-redis.md
Build your own Redis Cli: https://github.com/CodingChallengesFYI/SharedSolutions/blob/main/Solutions/challenge-redis-cli.md

> Create a GitHub issue in kajalmaurya/mcp-server titled "Test issue from MCP server"

Created issue #1: https://github.com/kajalmaurya/mcp-server/issues/1
```

## Known limitations

- `CodingChallengesSolutionFinder` performs no caching — every call re-fetches the source README.
- Link extraction relies on the README's current markdown structure; an upstream formatting change could silently reduce match accuracy.
- The server currently runs over stdio, meaning it operates as a local process per machine rather than a shared, remotely accessible service.

## Roadmap

- Add response caching to reduce redundant fetches
- Extend `CodingChallengesSolutionFinder` to resolve a specific language's solution from within a linked page
- Migrate to streamable-http transport for remote, multi-user deployment

## Stack

Python 3.13 · MCP Python SDK · httpx · GitHub REST API
