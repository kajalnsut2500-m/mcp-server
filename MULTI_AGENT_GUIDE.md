# Multi-Agent Collaboration Guide

This MCP server now supports **multiple AI agents working together on the same project** with full awareness of what each agent is doing.

## Architecture

```
Claude Desktop (Agent A)  ─┐
                           ├─→ MCP Server (stateful via state_manager.py)
Claude Desktop (Agent B)  ─┘         ├─→ GitHub API (authenticated)
                                     ├─→ Local Git repo
                                     └─→ Shared state file (.mcp_state.json)
```

## How It Works

### 1. Agent Checkin
When you start working, call `agent_checkin(agent_name)` to register yourself:
```
Agent: "Let me check in to the project"
Call: agent_checkin("Claude-Desktop-Agent-1")
Response: "Agent 'Claude-Desktop-Agent-1' checked in. Project has 0 recent changes and 0 logged activities."
```

### 2. Get Project Knowledge
Call `get_project_knowledge()` to see what has happened since you last worked:
```
Call: get_project_knowledge()
Response:
  === PROJECT KNOWLEDGE ===
  Last sync: 2024-10-13T13:15:22.123456
  Total changes logged: 5
  Total activities: 8
  
  === ACTIVE AGENTS ===
  - Claude-Desktop-Agent-2 (last seen: 2024-10-13T13:14:00)
  
  === RECENT AGENT ACTIVITIES ===
  [2024-10-13T13:10:00] Claude-Desktop-Agent-2: created_github_issue
    → Created issue #42: "Fix regex pattern in validator"
  [2024-10-13T13:05:00] Claude-Desktop-Agent-1: created_github_issue
    → Created issue #41: "Add retry logic"
```

### 3. Log Your Work
After you complete a task, call `log_work()` so other agents see what you did:
```
Call: log_work("Claude-Desktop-Agent-1", "refactored_code", "Simplified error handling in github_connector.py")
Response: "Activity logged: refactored_code - Simplified error handling in github_connector.py"
```

### 4. Create/List Issues (Now with Logging)
When you create or list GitHub issues, the action is automatically logged:
```
Call: create_github_issue("username/repo", "Fix bug X", "Description here", agent_name="Claude-Desktop-Agent-1")
Response: "Created issue #99: https://github.com/username/repo/issues/99"
(Also logged to shared state for other agents to see)

Call: list_github_issues("username/repo", agent_name="Claude-Desktop-Agent-1")
Response: "#42: Fix regex... — URL
          #41: Add retry... — URL"
(Also logged as an activity for other agents)
```

## Workflow Example

### Agent A's Session
```
1. agent_checkin("Claude-A")
   → Registered, 0 previous activities

2. get_project_knowledge()
   → No recent changes

3. create_github_issue("myuser/myrepo", "Add feature X", agent_name="Claude-A")
   → Created issue #1
   → Automatically logged for Agent B

4. log_work("Claude-A", "design", "Designed new feature architecture")
   → Activity logged
```

### Agent B's Session (starts later)
```
1. agent_checkin("Claude-B")
   → Registered

2. get_project_knowledge()
   → Shows:
      - Active agents: Claude-A (last seen 5 min ago)
      - Recent activities: Issue #1 created by Claude-A
      - Design work done by Claude-A
   
3. "I see Claude-A created issue #1 and designed the feature. Let me list issues to see details"
   list_github_issues("myuser/myrepo", agent_name="Claude-B")
   → Shows issue #1 created by Claude-A
   
4. "Great! I'll implement this feature now"
   log_work("Claude-B", "implementation", "Implemented feature X with full test coverage")
   → Activity logged for Claude-A to see
```

### Agent A's Second Session
```
1. agent_checkin("Claude-A")
   → Registered again

2. get_project_knowledge()
   → Shows Claude-B's implementation work
   → Can now build on Claude-B's implementation
```

## Shared State File

The `.mcp_state.json` file stores:

```json
{
  "agent_activities": [
    {
      "timestamp": "2024-10-13T13:10:00.000000",
      "agent": "Claude-A",
      "action": "created_github_issue",
      "description": "Created issue #1: Add feature X",
      "details": {"repo": "myuser/myrepo", "issue_number": 1, "url": "..."}
    }
  ],
  "project_changes": [],
  "last_sync": "2024-10-13T13:10:00.000000",
  "active_agents": {
    "Claude-A": {"last_seen": "2024-10-13T13:10:00.000000"}
  }
}
```

## Best Practices

1. **Always check in first**: Call `agent_checkin()` when you start
2. **Check knowledge before acting**: Call `get_project_knowledge()` to see what's been done
3. **Log important work**: Call `log_work()` after completing tasks
4. **Use agent names**: Always pass `agent_name` parameter to GitHub tools
5. **Review active agents**: See who else is working right now
6. **Timestamp awareness**: Times in `.mcp_state.json` are UTC ISO format

## Tools Summary

| Tool | Purpose | When to use |
|------|---------|-----------|
| `agent_checkin(agent_name)` | Register you're active | At session start |
| `get_project_knowledge()` | See all activities & changes | Before deciding what to work on |
| `log_work(agent_name, action, description)` | Share what you did | After completing tasks |
| `create_github_issue(..., agent_name)` | Create issue (now logged) | When creating GitHub issues |
| `list_github_issues(..., agent_name)` | List issues (now logged) | When reviewing issues |

## Limitations & Future Work

- State file is local JSON (single machine)
- No conflict detection (yet) — both agents can edit same file
- No request queuing — simultaneous operations may race
- No git-aware change tracking (yet)

## Deployment

Both Claude Desktop instances need access to the same `.mcp_state.json` file. If on the same machine, this works automatically. For remote collaboration, the state file would need to be:
- Synced via git
- Or stored in a shared location
- Or served by a network MCP server (future enhancement)
