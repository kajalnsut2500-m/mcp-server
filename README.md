# MCP Server for AI Coding Agents

![Python](https://img.shields.io/badge/Python-3.13-blue)
![MCP](https://img.shields.io/badge/Protocol-MCP-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

A lightweight [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that extends AI coding agents with two categories of capability:

- **Structured data retrieval** — deterministic lookups against external public sources
- **Authenticated write actions** — permission-scoped operations on a user's behalf via the GitHub REST API

Tested with Claude Code and Claude Desktop; works with any MCP-compliant client.

Built as part of the [Coding Challenges: Build Your Own MCP Server](https://codingchallenges.fyi) project.

---

## Why This Exists

Modern AI agents increasingly ship with general-purpose web browsing. That capability has a hard boundary: it can only read what is already public, and it cannot take authenticated write actions on a user's behalf.

This project draws a clear, working line across that boundary:

- `CodingChallengesSolutionFinder` — returns exact links from the source rather than generated ones, making results reliable and deterministic
- `create_github_issue` — a real authenticated write action against a user's GitHub account, gated by a narrowly scoped personal access token; something read-only browsing cannot do

The contrast between these two tools is the point of the project.

---

## Tools

| Tool | Description | Auth Required |
|---|---|---|
| `hello(name)` | Returns a greeting. Used as a protocol sanity check. | No |
| `CodingChallengesSolutionFinder(challenge_name)` | Fetches the CodingChallengesFYI shared solutions README and returns links matching the given challenge name. | No |
| `create_github_issue(repo, title, body)` | Creates a GitHub issue in the specified repository via the GitHub REST API. | Yes — `GITHUB_TOKEN` |
| `list_github_issues(repo)` | Lists all open issues in the specified repository via the GitHub REST API. | Yes — `GITHUB_TOKEN` |

---

## Architecture

```
User (natural language)
        │
        ▼
MCP Client (Claude Code / Claude Desktop / any MCP-compliant client)
        │  tools/list  →  discovers available tools
        │  tools/call  →  invokes a tool with structured input
        ▼
MCP Server  (this project — stdio transport)
        │
        ├──▶  httpx.get()   →  GitHub README     (public, read-only)
        └──▶  httpx.post()  →  GitHub REST API   (authenticated write)
        │
        ▼
Structured result returned to the agent, then surfaced to the user
```

The server communicates over MCP's standard JSON-RPC protocol via stdio. This means zero client-specific integration code — the same `server.py`, unmodified, works across all supported clients.

---

## Security

- The GitHub token is read from the environment at call time via `os.environ.get("GITHUB_TOKEN")`. It is never hardcoded, logged, or committed to source control.
- The token should be a **fine-grained personal access token** scoped to specific repositories with only the permissions needed: **Issues: Read and write** and (optionally) **Pull requests: Read and write**.
- Tools that require authentication return a clear error message if the token is absent — the server starts and serves unauthenticated tools regardless.
- All external HTTP calls are wrapped in explicit error handling. Network failures and unexpected API responses surface as clean messages to the calling agent rather than unhandled exceptions.

---

## Setup

### 1. Clone and install dependencies

```bash
git clone <this-repo-url>
cd mcp-server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Set your GitHub token

Create a fine-grained personal access token with **Issues: Read and write** permissions on the repositories you need, then export it:

```bash
export GITHUB_TOKEN="your_token_here"
```

### 3. Verify with MCP Inspector

```bash
npx @modelcontextprotocol/inspector python3 server.py
```

> **Note:** The MCP SDK's `StdioClientTransport` only forwards a small allowlist of environment variables (`HOME`, `PATH`, `USER`, etc.) to the subprocess — `GITHUB_TOKEN` is intentionally excluded. In the Inspector UI, add `GITHUB_TOKEN` under **Environment Variables** in the connection config before clicking Connect.

### 4. Connect to a client

**Claude Code:**

```bash
claude mcp add mcp-server --scope user -- /path/to/.venv/bin/python3 /path/to/server.py
```

**Claude Desktop** — add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mcp-server": {
      "command": "/path/to/.venv/bin/python3",
      "args": ["/path/to/server.py"],
      "env": {
        "GITHUB_TOKEN": "your_token_here"
      }
    }
  }
}
```

---

## Example Usage

```
User: Is there a shared solution for the Redis coding challenge?

Agent: Build your own Redis Server:
       https://github.com/CodingChallengesFYI/SharedSolutions/blob/main/Solutions/challenge-redis.md
       Build your own Redis CLI:
       https://github.com/CodingChallengesFYI/SharedSolutions/blob/main/Solutions/challenge-redis-cli.md

User: Create a GitHub issue in my mcp-server repo titled "Add caching to solution finder"

Agent: Created issue #2: https://github.com/kajalnsut2500-m/mcp-server/issues/2
```

> A short screen recording showing an agent creating a GitHub issue via this server would go here.

---

## Known Limitations

- `CodingChallengesSolutionFinder` makes a live HTTP request on every call — there is no caching.
- Link extraction depends on the upstream README's markdown structure. A formatting change in that file could silently reduce match accuracy.
- The server runs over stdio, making it a local per-machine process rather than a remotely accessible shared service.

---

## Roadmap

- [ ] Add response caching to `CodingChallengesSolutionFinder`
- [ ] Resolve language-specific solutions from within a linked challenge page
- [ ] Migrate to streamable-HTTP transport for remote, multi-user deployment

---

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| MCP framework | MCP Python SDK |
| HTTP client | httpx |
| External API | GitHub REST API v3 |
