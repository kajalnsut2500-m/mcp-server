"""State manager for tracking multi-agent activities and project changes."""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class StateManager:
    """Manages persistent state of agent activities and project changes."""

    def __init__(self, state_file: str = ".mcp_state.json"):
        """Initialize state manager with optional state file path.
        
        Args:
            state_file: Path to JSON file storing state (relative to project root).
        """
        self.state_file = Path(state_file)
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Load state from file, or initialize if doesn't exist."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self._default_state()
        return self._default_state()

    def _default_state(self) -> Dict[str, Any]:
        """Return default state structure."""
        return {
            "agent_activities": [],  # List of actions taken by agents
            "project_changes": [],   # Git commits and file changes
            "last_sync": None,       # Timestamp of last sync
            "active_agents": {},     # Which agents are currently active
        }

    def _save_state(self) -> None:
        """Save state to file."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.state, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save state: {e}")

    def log_agent_activity(
        self, agent_name: str, action: str, description: str, details: Optional[Dict] = None
    ) -> None:
        """Log an action performed by an agent.
        
        Args:
            agent_name: Name/identifier of the agent.
            action: Type of action (create_issue, commit, query, etc.).
            description: Human-readable description of what was done.
            details: Optional additional data.
        """
        activity = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent_name,
            "action": action,
            "description": description,
            "details": details or {},
        }
        self.state["agent_activities"].append(activity)
        self.state["last_sync"] = datetime.utcnow().isoformat()
        self._save_state()

    def log_project_change(
        self, change_type: str, description: str, details: Optional[Dict] = None
    ) -> None:
        """Log a project change (git commit, file modification, etc.).
        
        Args:
            change_type: Type of change (commit, file_modified, etc.).
            description: Human-readable description.
            details: Optional additional data (commit hash, files changed, etc.).
        """
        change = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": change_type,
            "description": description,
            "details": details or {},
        }
        self.state["project_changes"].append(change)
        self.state["last_sync"] = datetime.utcnow().isoformat()
        self._save_state()

    def get_recent_activities(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent agent activities.
        
        Args:
            limit: Maximum number of activities to return.
            
        Returns:
            List of recent activities, sorted by timestamp (newest first).
        """
        activities = sorted(
            self.state["agent_activities"],
            key=lambda x: x["timestamp"],
            reverse=True,
        )
        return activities[:limit]

    def get_recent_changes(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent project changes.
        
        Args:
            limit: Maximum number of changes to return.
            
        Returns:
            List of recent changes, sorted by timestamp (newest first).
        """
        changes = sorted(
            self.state["project_changes"],
            key=lambda x: x["timestamp"],
            reverse=True,
        )
        return changes[:limit]

    def get_project_status(self) -> Dict[str, Any]:
        """Get overall project status summary.
        
        Returns:
            Dict with recent activities, changes, and sync info.
        """
        return {
            "last_sync": self.state["last_sync"],
            "recent_activities": self.get_recent_activities(limit=5),
            "recent_changes": self.get_recent_changes(limit=5),
            "active_agents": self.state["active_agents"],
            "total_activities": len(self.state["agent_activities"]),
            "total_changes": len(self.state["project_changes"]),
        }

    def set_agent_active(self, agent_name: str) -> None:
        """Mark an agent as currently active.
        
        Args:
            agent_name: Name/identifier of the agent.
        """
        self.state["active_agents"][agent_name] = {
            "last_seen": datetime.utcnow().isoformat()
        }
        self._save_state()

    def set_agent_inactive(self, agent_name: str) -> None:
        """Mark an agent as inactive.
        
        Args:
            agent_name: Name/identifier of the agent.
        """
        if agent_name in self.state["active_agents"]:
            del self.state["active_agents"][agent_name]
            self._save_state()
