from mcp.server.mcpserver import MCPServer
from dotenv import load_dotenv
import subprocess
import shlex
import shutil
import tempfile
import fcntl
import json
import sys
import os

load_dotenv()

mcp = MCPServer("agent-connector")

WORKSPACE_ROOT = os.environ.get("WORKSPACE_ROOT", os.path.expanduser("~"))
_REAL_WORKSPACE = os.path.realpath(WORKSPACE_ROOT)
ALLOWED_COMMANDS = os.environ.get("ALLOWED_COMMANDS", "git,ls,cat,pwd,echo,python,node,npm").split(",")
MEMORY_FILE = os.path.expanduser("~/.agent_memory.json")

# Resolve allowed commands to absolute paths at startup to prevent PATH hijacking
_COMMAND_PATHS: dict[str, str] = {
    cmd: path
    for cmd in ALLOWED_COMMANDS
    if (path := shutil.which(cmd)) is not None
}


def _resolve(path: str) -> str:
    resolved = os.path.realpath(os.path.join(WORKSPACE_ROOT, path))
    if resolved != _REAL_WORKSPACE and not resolved.startswith(_REAL_WORKSPACE + os.sep):
        raise ValueError(f"Path '{path}' is outside the workspace root.")
    return resolved


def _load_store() -> dict:
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}


def _save_store(store: dict) -> None:
    dir_ = os.path.dirname(MEMORY_FILE) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(store, f, indent=2)
        fd = -1  # fdopen took ownership; don't close again
        os.replace(tmp_path, MEMORY_FILE)
    except Exception:
        if fd != -1:
            os.close(fd)
        os.unlink(tmp_path)
        raise


@mcp.tool()
def read_file(path: str) -> str:
    """Read the contents of a file. Path is relative to WORKSPACE_ROOT."""
    try:
        full_path = _resolve(path)
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except ValueError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return f"Error: file not found — {path}"
    except Exception as e:
        return f"Error reading file: {e}"


@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Write content to a file. Path is relative to WORKSPACE_ROOT. Creates the file if it doesn't exist."""
    try:
        full_path = _resolve(path)
        parent = os.path.dirname(full_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Written to {path}"
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error writing file: {e}"


@mcp.tool()
def list_directory(path: str = ".") -> str:
    """List files and folders in a directory. Path is relative to WORKSPACE_ROOT."""
    try:
        full_path = _resolve(path)
        entries = sorted(os.listdir(full_path))
        lines = []
        for entry in entries:
            prefix = "[dir] " if os.path.isdir(os.path.join(full_path, entry)) else "[file]"
            lines.append(f"{prefix} {entry}")
        return "\n".join(lines) if lines else "(empty directory)"
    except ValueError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return f"Error: directory not found — {path}"
    except Exception as e:
        return f"Error listing directory: {e}"


@mcp.tool()
def run_command(command: str) -> str:
    """Run a shell command and return its output. Allowed prefixes: git, ls, cat, pwd, echo, python, node, npm."""
    try:
        args = shlex.split(command)
    except ValueError as e:
        return f"Error: invalid command syntax — {e}"
    if not args:
        return "Error: empty command."
    exe = _COMMAND_PATHS.get(args[0])
    if exe is None:
        available = ", ".join(_COMMAND_PATHS)
        return f"Error: '{args[0]}' is not allowed or not found. Available: {available}."
    try:
        result = subprocess.run(
            [exe] + args[1:],
            shell=False,
            cwd=_REAL_WORKSPACE,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: command timed out after 30 seconds."
    except Exception as e:
        return f"Error running command: {e}"


@mcp.tool()
def shared_memory(action: str, key: str, value: str = "") -> str:
    """Store or retrieve notes shared across agents. action: 'set', 'get', 'delete', or 'list'."""
    try:
        with open(MEMORY_FILE + ".lock", "w") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            store = _load_store()

            if action == "set":
                store[key] = value
                _save_store(store)
                return f"Stored '{key}'."
            elif action == "get":
                return store.get(key, f"No entry found for '{key}'.")
            elif action == "delete":
                if key in store:
                    del store[key]
                    _save_store(store)
                    return f"Deleted '{key}'."
                return f"No entry found for '{key}'."
            elif action == "list":
                return "\n".join(store.keys()) if store else "(memory is empty)"
            else:
                return "Error: action must be one of 'set', 'get', 'delete', 'list'."
    except Exception as e:
        print(f"shared_memory error: {e}", file=sys.stderr)
        return f"Error accessing shared memory: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
