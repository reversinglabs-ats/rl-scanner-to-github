"""Entry point for creating GitHub Issues from RL scan failures."""

import argparse
import sys
from pathlib import Path

from parse_report import parse_report, BlockingPolicy
from enrich import load_policy_metadata
from github_issues import GitHubClient


def build_body(policy: BlockingPolicy, metadata: dict | None, cve_details: dict) -> str:
    """Build issue body markdown."""
    lines = [
        f"**Severity:** {policy.severity}",
        f"**Priority:** P{policy.priority}",
        f"**Effort:** {policy.effort}",
        "",
    ]
    if metadata and metadata.get("description"):
        lines.extend([metadata["description"], ""])

    if policy.components:
        lines.append("## Affected Components")
        for c in policy.components:
            lines.append(f"- `{c.path}`")
        lines.append("")

    if policy.cve_ids:
        lines.append("## CVEs")
        lines.append("| CVE | CVSS | Exploited | Fixable |")
        lines.append("|-----|------|-----------|---------|")
        for cve_id in policy.cve_ids:
            d = cve_details.get(cve_id, {})
            cvss = d.get("cvss") or "-"
            exploited = "Yes" if d.get("exploited") else "No"
            fixable = "Yes" if d.get("fixable") else "No"
            lines.append(f"| {cve_id} | {cvss} | {exploited} | {fixable} |")
        lines.append("")

    if metadata and metadata.get("steps"):
        lines.append("## Remediation Steps")
        for i, step in enumerate(metadata["steps"], 1):
            lines.append(f"{i}. {step}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create GitHub Issues from RL scan failures")
    parser.add_argument("--report", required=True, help="Path to report.rl.json")
    parser.add_argument("--metadata-dir", help="Path to rl-scanner-metadata directory")
    parser.add_argument("--dry-run", action="store_true", help="Print issues without creating")
    parser.add_argument("--max-issues", type=int, default=10, help="Max issues to create")
    args = parser.parse_args()

    result = parse_report(Path(args.report))

    if result.scan_status != "fail":
        print(f"Scan passed ({result.scan_status}), no issues to create")
        return 0

    policies = result.blocking_policies[:args.max_issues]
    if not policies:
        print("No blocking policies found")
        return 0

    metadata = {}
    if args.metadata_dir:
        policy_ids = [p.policy_id for p in policies]
        metadata = load_policy_metadata(policy_ids, Path(args.metadata_dir))

    if not args.dry_run:
        client = GitHubClient()

    created, skipped = 0, 0
    for policy in policies:
        meta = metadata.get(policy.policy_id)
        label = meta["label"] if meta and meta.get("label") else policy.policy_id
        title = f"[{policy.policy_id}] {label}"
        body = build_body(policy, meta, result.cve_details)

        if args.dry_run:
            print(f"\n{'='*60}")
            print(f"WOULD CREATE: {title}")
            print(f"{'='*60}")
            print(body)
            created += 1
        else:
            issue, was_created = client.create_if_new(policy.policy_id, title, body)
            if was_created:
                print(f"Created: {title} -> {issue['html_url']}")
                created += 1
            else:
                print(f"Skipped (exists): {title} -> {issue['html_url']}")
                skipped += 1

    print(f"\nSummary: {created} created, {skipped} skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
