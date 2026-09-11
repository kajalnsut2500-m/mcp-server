from mcp.server.mcpserver import MCPServer
import httpx
import re
import os
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]


mcp = MCPServer("solution-finder")

README_URL = "https://raw.githubusercontent.com/CodingChallengesFYI/SharedSolutions/main/README.md"

@mcp.tool()
def hello(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}"

@mcp.tool()
def create_github_issue(repo: str, title: str, body: str = "") -> str:
    """Create a new issue in one of the user's GitHub repos. repo should be 'username/repo-name'."""
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    payload = {"title": title, "body": body}
    try:
        response = httpx.post(f"https://api.github.com/repos/{repo}/issues",
                               headers=headers, json=payload, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        return f"Error creating issue: {e.response.status_code} - {e.response.text}"
    except httpx.RequestError:
        return "Error: could not reach GitHub right now."

    issue = response.json()
    return f"Created issue #{issue['number']}: {issue['html_url']}"

@mcp.tool()
def CodingChallengesSolutionFinder(challenge_name: str) -> str:
    """Find the Shared Solutions page link for a given Coding Challenge name (or part of it)."""
    try:
        response = httpx.get(README_URL, timeout=10.0)
        response.raise_for_status()
    except httpx.RequestError:
        return "Error: could not reach GitHub right now. Please try again shortly."
    except httpx.HTTPStatusError as e:
        return f"Error: GitHub returned status {e.response.status_code}."

    content = response.text


    # Matches lines like: [Build your own Redis Server](https://github.com/.../challenge-redis.md)
    links = re.findall(r"\[([^\]]*" + re.escape(challenge_name) + r"[^\]]*)\]\(([^\)]+)\)",
                        content, re.IGNORECASE)

    if not links:
        return f"No challenge found matching '{challenge_name}'."

    base = "https://github.com/CodingChallengesFYI/SharedSolutions/blob/main/"
    return "\n".join(f"{title}: {base}{url}" for title, url in links)

if __name__ == "__main__":
    mcp.run(transport="stdio")