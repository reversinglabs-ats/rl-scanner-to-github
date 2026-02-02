"""GitHub Issues API wrapper with deduplication."""

import os

import requests


class GitHubClient:
    """GitHub API client for issue management."""

    def __init__(self) -> None:
        """Initialize client. Raises ValueError if env vars missing."""
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN environment variable not set")

        self.repo = os.environ.get("GITHUB_REPOSITORY")
        if not self.repo:
            raise ValueError("GITHUB_REPOSITORY environment variable not set")

        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def find_open_issue(self, policy_id: str) -> dict | None:
        """Find existing open issue for a policy. Returns issue dict or None."""
        query = f'repo:{self.repo} is:issue is:open "[{policy_id}]" in:title'
        resp = requests.get(
            "https://api.github.com/search/issues",
            headers=self.headers,
            params={"q": query},
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return items[0] if items else None

    def create_issue(self, title: str, body: str) -> dict:
        """Create a new issue. Returns created issue dict."""
        resp = requests.post(
            f"https://api.github.com/repos/{self.repo}/issues",
            headers=self.headers,
            json={"title": title, "body": body},
        )
        resp.raise_for_status()
        return resp.json()

    def create_if_new(self, policy_id: str, title: str, body: str) -> tuple[dict, bool]:
        """Create issue only if none exists for policy. Returns (issue, was_created)."""
        existing = self.find_open_issue(policy_id)
        if existing:
            return (existing, False)
        return (self.create_issue(title, body), True)
