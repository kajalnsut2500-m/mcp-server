"""GitHub API connector module for MCP server tools."""

import os
import httpx
from typing import Optional, Dict, Any


class GitHubConnector:
    """Handles all GitHub API interactions with consistent error handling and authentication."""

    BASE_URL = "https://api.github.com"
    DEFAULT_HEADERS = {
        "Accept": "application/vnd.github+json",
    }
    TIMEOUT = 10.0

    def __init__(self):
        """Initialize connector with optional GitHub token from environment."""
        self.token = os.environ.get("GITHUB_TOKEN")
        self.headers = self.DEFAULT_HEADERS.copy()
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"

    def requires_token(self) -> Optional[str]:
        """Return error message if token is not set, None otherwise."""
        if not self.token:
            return "Error: GITHUB_TOKEN environment variable is not set."
        return None

    def get_headers(self) -> Dict[str, str]:
        """Get current headers (with or without authorization)."""
        return self.headers.copy()

    def get_issues(self, repo: str, state: str = "open") -> Dict[str, Any]:
        """
        Fetch issues from a GitHub repository.
        
        Args:
            repo: Repository in 'username/repo-name' format.
            state: Issue state filter (open, closed, all).
            
        Returns:
            Dict with 'success' bool, 'data' (list of issues), and 'error' (if failed).
        """
        try:
            response = httpx.get(
                f"{self.BASE_URL}/repos/{repo}/issues",
                headers=self.headers,
                params={"state": state},
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return {"success": True, "data": response.json(), "error": None}
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "data": None,
                "error": f"Error fetching issues: {e.response.status_code} - {e.response.text}",
            }
        except httpx.RequestError:
            return {
                "success": False,
                "data": None,
                "error": "Error: could not reach GitHub right now.",
            }

    def create_issue(self, repo: str, title: str, body: str = "") -> Dict[str, Any]:
        """
        Create a new issue in a GitHub repository.
        
        Args:
            repo: Repository in 'username/repo-name' format.
            title: Issue title.
            body: Issue body/description.
            
        Returns:
            Dict with 'success' bool, 'data' (issue details), and 'error' (if failed).
        """
        try:
            response = httpx.post(
                f"{self.BASE_URL}/repos/{repo}/issues",
                headers=self.headers,
                json={"title": title, "body": body},
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return {"success": True, "data": response.json(), "error": None}
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "data": None,
                "error": f"Error creating issue: {e.response.status_code} - {e.response.text}",
            }
        except httpx.RequestError:
            return {
                "success": False,
                "data": None,
                "error": "Error: could not reach GitHub right now.",
            }
