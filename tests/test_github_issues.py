"""Test github_issues module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from github_issues import GitHubClient


def _make_client() -> GitHubClient:
    """Create GitHubClient with mocked env vars."""
    with patch.dict(
        "os.environ",
        {
            "GITHUB_TOKEN": "ghp_test123",
            "GITHUB_REPOSITORY": "owner/repo",
        },
    ):
        return GitHubClient()


def test_init_success():
    """Constructor sets self.repo and self.headers correctly."""
    client = _make_client()
    assert client.repo == "owner/repo"
    assert client.headers["Authorization"] == "Bearer ghp_test123"
    assert client.headers["Accept"] == "application/vnd.github+json"
    assert client.headers["X-GitHub-Api-Version"] == "2022-11-28"


def test_init_missing_token():
    """Raises ValueError matching 'GITHUB_TOKEN' when token absent."""
    with patch.dict("os.environ", {"GITHUB_REPOSITORY": "owner/repo"}, clear=True):
        with pytest.raises(ValueError, match="GITHUB_TOKEN"):
            GitHubClient()


def test_init_missing_repository():
    """Raises ValueError matching 'GITHUB_REPOSITORY' when repo absent."""
    with patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_test123"}, clear=True):
        with pytest.raises(ValueError, match="GITHUB_REPOSITORY"):
            GitHubClient()


def test_init_empty_token():
    """Raises ValueError when token is empty string (falsy)."""
    with patch.dict(
        "os.environ",
        {
            "GITHUB_TOKEN": "",
            "GITHUB_REPOSITORY": "owner/repo",
        },
        clear=True,
    ):
        with pytest.raises(ValueError, match="GITHUB_TOKEN"):
            GitHubClient()


@patch("github_issues.requests.get")
def test_find_open_issue_found(mock_get):
    """Returns first issue dict when API returns items."""
    client = _make_client()
    issue = {
        "number": 42,
        "title": "[SQ123] Test",
        "html_url": "https://github.com/owner/repo/issues/42",
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"items": [issue, {"number": 99}]}
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    result = client.find_open_issue("SQ123")
    assert result == issue
    mock_get.assert_called_once()


@patch("github_issues.requests.get")
def test_find_open_issue_not_found(mock_get):
    """Returns None when API returns empty items."""
    client = _make_client()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"items": []}
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    result = client.find_open_issue("SQ999")
    assert result is None


@patch("github_issues.requests.get")
def test_find_open_issue_auth_error(mock_get):
    """Raises HTTPError on 401 via raise_for_status()."""
    client = _make_client()
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")
    mock_get.return_value = mock_resp

    with pytest.raises(requests.HTTPError):
        client.find_open_issue("SQ123")


@patch("github_issues.requests.get")
def test_find_open_issue_rate_limit(mock_get):
    """Raises HTTPError on 429 via raise_for_status()."""
    client = _make_client()
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = requests.HTTPError("429 Too Many Requests")
    mock_get.return_value = mock_resp

    with pytest.raises(requests.HTTPError):
        client.find_open_issue("SQ123")


@patch("github_issues.requests.post")
def test_create_issue_success(mock_post):
    """Returns issue dict; verifies POST URL, headers, and JSON body."""
    client = _make_client()
    issue = {"number": 1, "html_url": "https://github.com/owner/repo/issues/1"}
    mock_resp = MagicMock()
    mock_resp.json.return_value = issue
    mock_resp.raise_for_status.return_value = None
    mock_post.return_value = mock_resp

    result = client.create_issue("[SQ123] Test Policy", "Issue body")
    assert result == issue
    mock_post.assert_called_once_with(
        "https://api.github.com/repos/owner/repo/issues",
        headers=client.headers,
        json={"title": "[SQ123] Test Policy", "body": "Issue body"},
    )


@patch("github_issues.requests.post")
def test_create_issue_api_failure(mock_post):
    """Raises HTTPError on 500."""
    client = _make_client()
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = requests.HTTPError("500 Internal Server Error")
    mock_post.return_value = mock_resp

    with pytest.raises(requests.HTTPError):
        client.create_issue("[SQ123] Test", "body")


def test_create_if_new_creates():
    """find_open_issue returns None, so create_issue is called."""
    client = _make_client()
    new_issue = {"number": 5, "html_url": "https://github.com/owner/repo/issues/5"}

    with patch.object(client, "find_open_issue", return_value=None) as mock_find, patch.object(
        client, "create_issue", return_value=new_issue
    ) as mock_create:
        result, was_created = client.create_if_new("SQ123", "[SQ123] Title", "body")

    assert result == new_issue
    assert was_created is True
    mock_find.assert_called_once_with("SQ123")
    mock_create.assert_called_once_with("[SQ123] Title", "body")


def test_create_if_new_skips():
    """find_open_issue returns existing issue, so create_issue is not called."""
    client = _make_client()
    existing = {"number": 3, "html_url": "https://github.com/owner/repo/issues/3"}

    with patch.object(client, "find_open_issue", return_value=existing) as mock_find, patch.object(
        client, "create_issue"
    ) as mock_create:
        result, was_created = client.create_if_new("SQ123", "[SQ123] Title", "body")

    assert result == existing
    assert was_created is False
    mock_find.assert_called_once_with("SQ123")
    mock_create.assert_not_called()
