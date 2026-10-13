# MCP Server — Agent Connector

![Python](https://img.shields.io/badge/Python-3.13-blue)
![MCP](https://img.shields.io/badge/Protocol-MCP-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

A lightweight [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that gives AI agents safe, sandboxed access to the local filesystem, a restricted shell, and a shared key-value memory store.

Tested with Claude Code and Claude Desktop; works with any MCP-compliant client.

---

## Tools

| Tool | Description |
|---|---|
| `read_file(path)` | Read a file. Path is relative to `WORKSPACE_ROOT`. |
| `write_file(path, content)` | Write or create a file. Path is relative to `WORKSPACE_ROOT`. |
| `list_directory(path)` | List files and folders in a directory. Defaults to workspace root. |
| `run_command(command)` | Run a shell command. Only commands in `ALLOWED_COMMANDS` are permitted. |
| `shared_memory(action, key, value)` | Get, set, delete, or list notes shared across agents. |

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
        ├──▶  filesystem  →  read / write files inside WORKSPACE_ROOT
        ├──▶  subprocess  →  run allowlisted shell commands
        └──▶  ~/.agent_memory.json  →  shared key-value store
```

---

## Security

- **Path sandboxing** — all file paths are resolved with `os.path.realpath` and checked against `WORKSPACE_ROOT`. Traversal attempts (e.g. `../../etc/passwd`) are rejected before any I/O.
- **Command allowlist** — `run_command` only accepts commands listed in `ALLOWED_COMMANDS`. Each command is resolved to an absolute path at startup to prevent `PATH` hijacking.
- **No shell injection** — commands are split with `shlex.split` and passed as a list to `subprocess.run(shell=False)`.
- **Atomic writes** — `shared_memory` writes use a file lock and an atomic `os.replace` to prevent corruption under concurrent access.

---

## Configuration

Settings are read from a `.env` file in the project root (loaded automatically at startup via `python-dotenv`).

| Variable | Default | Description |
|---|---|---|
| `WORKSPACE_ROOT` | `~` (home directory) | Root directory for all file operations |
| `ALLOWED_COMMANDS` | `git,ls,cat,pwd,echo,python,node,npm` | Comma-separated list of permitted shell commands |

Example `.env`:

```env
WORKSPACE_ROOT=/Users/you/projects
ALLOWED_COMMANDS=git,ls,cat,pwd,echo,python,node,npm
```

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

### 2. Configure your workspace

```bash
cp .env.example .env   # or create .env manually
# Set WORKSPACE_ROOT and ALLOWED_COMMANDS as needed
```

### 3. Verify with MCP Inspector

```bash
npx @modelcontextprotocol/inspector .venv/bin/python3 server.py
```

### 4. Connect to a client

**Claude Code:**

```bash
claude mcp add agent-connector --scope user -- /path/to/.venv/bin/python3 /path/to/server.py
```

**Claude Desktop** — add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "agent-connector": {
      "command": "/path/to/.venv/bin/python3",
      "args": ["/path/to/server.py"]
    }
  }
}
```

---

## Example Usage

```
User: Read the contents of my server config

Agent: [calls read_file("myproject/config.json")]
       → returns file contents

User: List what's in the project root

Agent: [calls list_directory(".")]
       → [dir]  myproject
          [file] README.md
          [file] config.json

User: Run git status

Agent: [calls run_command("git status")]
       → On branch main, nothing to commit

User: Remember that the API key rotates every 30 days

Agent: [calls shared_memory("set", "api_key_rotation", "rotates every 30 days")]
       → Stored 'api_key_rotation'.
```

---

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| MCP framework | MCP Python SDK |
| Config | python-dotenv |
| Transport | stdio |
