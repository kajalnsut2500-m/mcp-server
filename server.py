import os
import re

import httpx

from mcp.server.mcpserver import MCPServer
from github_connector import GitHubConnector
from state_manager import StateManager

mcp = MCPServer("solution-finder")

README_URL = "https://raw.githubusercontent.com/CodingChallengesFYI/SharedSolutions/main/README.md"
github = GitHubConnector()
state = StateManager()


@mcp.tool()
def hello(name: str) -> str:
    """Say hello to someone.
    
    Args:
        name: The name to greet.
    """
    return f"Hello, {name}"


@mcp.tool()
def agent_checkin(agent_name: str) -> str:
    """Register that an agent is active and aware of the project.
    
    Call this when you start working to let other agents know you're here.
    
    Args:
        agent_name: Identifier for this agent (e.g., 'Claude-Desktop-1').
    """
    state.set_agent_active(agent_name)
    status = state.get_project_status()
    return f"Agent '{agent_name}' checked in. Project has {status['total_changes']} recent changes and {status['total_activities']} logged activities."


@mcp.tool()
def get_project_knowledge() -> str:
    """Get comprehensive project status and what other agents have done.
    
    Shows recent changes, activities, and what other agents are working on.
    Call this first when starting to understand what's been done.
    """
    status = state.get_project_status()
    
    result = "=== PROJECT KNOWLEDGE ===\n\n"
    result += f"Last sync: {status['last_sync']}\n"
    result += f"Total changes logged: {status['total_changes']}\n"
    result += f"Total activities: {status['total_activities']}\n\n"
    
    if status["active_agents"]:
        result += "=== ACTIVE AGENTS ===\n"
        for agent, info in status["active_agents"].items():
            result += f"- {agent} (last seen: {info['last_seen']})\n"
        result += "\n"
    
    if status["recent_changes"]:
        result += "=== RECENT PROJECT CHANGES ===\n"
        for change in status["recent_changes"]:
            result += f"[{change['timestamp']}] {change['type']}: {change['description']}\n"
        result += "\n"
    
    if status["recent_activities"]:
        result += "=== RECENT AGENT ACTIVITIES ===\n"
        for activity in status["recent_activities"]:
            result += f"[{activity['timestamp']}] {activity['agent']}: {activity['action']}\n  → {activity['description']}\n"
    
    return result


@mcp.tool()
def log_work(agent_name: str, action: str, description: str) -> str:
    """Log work you've done so other agents can see it.
    
    Args:
        agent_name: Your agent identifier.
        action: Type of work (e.g., 'created_issue', 'fixed_bug', 'refactored_code').
        description: What you did and why.
    """
    state.log_agent_activity(agent_name, action, description)
    return f"Activity logged: {action} - {description}"


@mcp.tool()
def CodingChallengesSolutionFinder(challenge_name: str) -> str:
    """Find the Shared Solutions page link for a given Coding Challenge name (or part of it).
    
    Args:
        challenge_name: The name or part of the name of the coding challenge to search for.
    """
    try:
        response = httpx.get(README_URL, timeout=10.0)
        response.raise_for_status()
    except httpx.RequestError:
        return "Error: could not reach GitHub right now. Please try again shortly."
    except httpx.HTTPStatusError as e:
        return f"Error: GitHub returned status {e.response.status_code}."

    content = response.text

    # Matches lines like: [Build your own Redis Server](https://github.com/.../challenge-redis.md)
    links = re.findall(
        r"\[([^\]]*" + re.escape(challenge_name) + r"[^\]]*)\]\(([^\)]+)\)",
        content,
        re.IGNORECASE,
    )

    if not links:
        return f"No challenge found matching '{challenge_name}'."

    base = "https://github.com/CodingChallengesFYI/SharedSolutions/blob/main/"
    return "\n".join(f"{title}: {base}{url}" for title, url in links)


@mcp.tool()
def create_github_issue(repo: str, title: str, body: str = "", agent_name: str = "unknown") -> str:
    """Create a new issue in one of the user's GitHub repos.
    
    Args:
        repo: Repository in 'username/repo-name' format.
        title: The issue title.
        body: The issue body/description (optional).
        agent_name: Your agent identifier (for logging).
    """
    token_error = github.requires_token()
    if token_error:
        return token_error

    result = github.create_issue(repo, title, body)
    if not result["success"]:
        return result["error"]

    issue = result["data"]
    issue_url = issue['html_url']
    
    # Log this activity for other agents to see
    state.log_agent_activity(
        agent_name,
        "created_github_issue",
        f"Created issue #{issue['number']}: {title}",
        {"repo": repo, "issue_number": issue['number'], "url": issue_url}
    )
    
    return f"Created issue #{issue['number']}: {issue_url}"


@mcp.tool()
def list_github_issues(repo: str, agent_name: str = "unknown") -> str:
    """List open issues in a GitHub repo.
    
    Args:
        repo: Repository in 'username/repo-name' format.
        agent_name: Your agent identifier (for logging).
    """
    token_error = github.requires_token()
    if token_error:
        return token_error

    result = github.get_issues(repo)
    if not result["success"]:
        return result["error"]

    issues = result["data"]
    
    # Log this activity
    state.log_agent_activity(
        agent_name,
        "listed_github_issues",
        f"Listed open issues in {repo}",
        {"repo": repo, "issue_count": len(issues) if issues else 0}
    )
    
    if not issues:
        return f"No open issues in {repo}."
    return "\n".join(f"#{i['number']}: {i['title']} — {i['html_url']}" for i in issues)


if __name__ == "__main__":
    mcp.run(transport="stdio")
