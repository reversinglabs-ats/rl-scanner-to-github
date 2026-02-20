"""Tests for build_body() in main.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import build_body
from parse_report import BlockingPolicy, Component


def _make_policy():
    """Create a minimal BlockingPolicy for build_body tests."""
    return BlockingPolicy(
        policy_id="SQ31102",
        category="vulnerabilities",
        severity="high",
        priority=0,
        effort="high",
        components=[Component(name="libssl.so", path="/lib/libssl.so.1.1")],
        cve_ids=["CVE-2024-1234"],
    )


def test_build_body_without_report_url():
    body = build_body(_make_policy(), None, {})
    assert "SAFE report" not in body
    assert "\U0001f4ca" not in body
    assert body.lstrip().startswith("**Severity:**")


def test_build_body_with_report_url():
    url = "https://github.com/org/repo/actions/runs/12345"
    body = build_body(_make_policy(), None, {}, report_url=url)
    assert body.startswith("> \U0001f4ca")
    assert url in body
    assert "[Download full SAFE report]" in body
    assert "sdlc.html" in body
    assert "**Severity:** high" in body


def test_build_body_with_report_url_none_explicitly():
    body = build_body(_make_policy(), None, {}, report_url=None)
    assert "SAFE report" not in body


def test_build_body_with_empty_string_report_url():
    body = build_body(_make_policy(), None, {}, report_url="")
    assert "SAFE report" not in body
