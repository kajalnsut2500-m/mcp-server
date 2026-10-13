import os
import re

import httpx

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("solution-finder")

README_URL = "https://raw.githubusercontent.com/CodingChallengesFYI/SharedSolutions/main/README.md"
GITHUB_API_URL = "https://api.github.com/repos"
GITHUB_HEADERS = {
    "Accept": "application/vnd.github+json",
}


def _get_github_headers() -> dict:
    """Get GitHub API headers with authorization token if available."""
    token = os.environ.get("GITHUB_TOKEN")
    headers = GITHUB_HEADERS.copy()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _requires_token() -> str:
    """Return error message if GITHUB_TOKEN is not set."""
    if not os.environ.get("GITHUB_TOKEN"):
        return "Error: GITHUB_TOKEN environment variable is not set."
    return ""


@mcp.tool()
def hello(name: str) -> str:
    """Say hello to someone.
    
    Args:
        name: The name to greet.
    """
    return f"Hello, {name}"


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
def create_github_issue(repo: str, title: str, body: str = "") -> str:
    """Create a new issue in one of the user's GitHub repos.
    
    Args:
        repo: Repository in 'username/repo-name' format.
        title: The issue title.
        body: The issue body/description (optional).
    """
    token_error = _requires_token()
    if token_error:
        return token_error

    headers = _get_github_headers()
    payload = {"title": title, "body": body}

    try:
        response = httpx.post(
            f"{GITHUB_API_URL}/{repo}/issues",
            headers=headers,
            json=payload,
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        return f"Error creating issue: {e.response.status_code} - {e.response.text}"
    except httpx.RequestError:
        return "Error: could not reach GitHub right now."

    issue = response.json()
    return f"Created issue #{issue['number']}: {issue['html_url']}"


@mcp.tool()
def list_github_issues(repo: str) -> str:
    """List open issues in a GitHub repo.
    
    Args:
        repo: Repository in 'username/repo-name' format.
    """
    token_error = _requires_token()
    if token_error:
        return token_error

    headers = _get_github_headers()

    try:
        response = httpx.get(
            f"{GITHUB_API_URL}/{repo}/issues",
            headers=headers,
            params={"state": "open"},
            timeout=10.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        return f"Error fetching issues: {e.response.status_code} - {e.response.text}"
    except httpx.RequestError:
        return "Error: could not reach GitHub right now."

    issues = response.json()
    if not issues:
        return f"No open issues in {repo}."
    return "\n".join(f"#{i['number']}: {i['title']} — {i['html_url']}" for i in issues)


if __name__ == "__main__":
    mcp.run(transport="stdio")
