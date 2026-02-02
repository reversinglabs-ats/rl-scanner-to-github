"""Parse rl-json reports to extract blocking policy violations.

Filtering: Only violations with status="fail" are extracted.
Aggregation: One BlockingPolicy per policy_id (not per file).
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

# Safety limit: max components per issue to keep issues readable
MAX_COMPONENTS_PER_ISSUE = 50


@dataclass
class Component:
    """A component affected by a violation."""
    name: str
    path: str


@dataclass
class BlockingPolicy:
    """A policy blocking the scan (status=fail), with aggregated components."""
    policy_id: str
    category: str
    severity: str
    priority: int  # 0=P0 (highest) to 4=P4 (lowest)
    effort: str    # "high", "medium", "low"
    components: list[Component] = field(default_factory=list)
    cve_ids: list[str] = field(default_factory=list)


@dataclass
class ScanResult:
    """Parsed scan result."""
    artifact_name: str
    scan_level: int
    scan_status: str  # "pass" or "fail"
    blocking_policies: list[BlockingPolicy] = field(default_factory=list)
    cve_details: dict[str, dict] = field(default_factory=dict)


def parse_report(report_path: Path) -> ScanResult:
    """Parse rl-json report and extract blocking policies.
    
    Args:
        report_path: Path to report.rl.json file
        
    Returns:
        ScanResult with only status="fail" policies, grouped by policy_id
        
    Raises:
        FileNotFoundError: If report file doesn't exist
        json.JSONDecodeError: If report is not valid JSON
    """
    with open(report_path, encoding="utf-8") as f:
        data = json.load(f)
    
    report = data.get("report", {})
    info = report.get("info", {})
    metadata = report.get("metadata", {})
    
    artifact_name = info.get("file", {}).get("name", "unknown")
    scan_level = info.get("inhibitors", {}).get("scan_level", 0)
    scan_status = info.get("statistics", {}).get("quality", {}).get("status", "unknown")
    
    # No blocking policies if scan passed
    if scan_status != "fail":
        return ScanResult(
            artifact_name=artifact_name,
            scan_level=scan_level,
            scan_status=scan_status,
        )
    
    blocking = _extract_blocking_policies(metadata)
    cve_details = _extract_cve_details(metadata, blocking)
    
    return ScanResult(
        artifact_name=artifact_name,
        scan_level=scan_level,
        scan_status=scan_status,
        blocking_policies=blocking,
        cve_details=cve_details,
    )


def _extract_blocking_policies(metadata: dict) -> list[BlockingPolicy]:
    """Extract and aggregate policies with status=fail."""
    violations = metadata.get("violations", {})
    components = metadata.get("components", {})
    vulnerabilities = metadata.get("vulnerabilities", {})
    
    # Group by policy_id to aggregate
    by_policy: dict[str, list[dict]] = {}
    for v in violations.values():
        if v.get("status") != "fail":
            continue
        policy_id = v.get("rule_id")
        if policy_id:
            by_policy.setdefault(policy_id, []).append(v)
    
    result = []
    for policy_id, violation_list in by_policy.items():
        first = violation_list[0]
        
        # Aggregate components from all violations of this policy
        affected = []
        seen_paths = set()
        for v in violation_list:
            for comp_id in v.get("references", {}).get("component", []):
                comp = components.get(comp_id, {})
                path = comp.get("path", "")
                if path and path not in seen_paths:
                    seen_paths.add(path)
                    affected.append(Component(
                        name=comp.get("name", "unknown"),
                        path=path,
                    ))
        
        # Find CVEs that triggered this policy
        cve_ids = [
            cve_id for cve_id, cve_data in vulnerabilities.items()
            if policy_id in cve_data.get("violations", [])
        ]
        
        result.append(BlockingPolicy(
            policy_id=policy_id,
            category=first.get("category", "unknown"),
            severity=first.get("severity", "unknown"),
            priority=first.get("priority", 4),
            effort=first.get("effort", "unknown"),
            components=affected[:MAX_COMPONENTS_PER_ISSUE],
            cve_ids=sorted(cve_ids),
        ))
    
    result.sort(key=lambda p: (p.priority, p.policy_id))
    return result


def _extract_cve_details(metadata: dict, blocking: list[BlockingPolicy]) -> dict[str, dict]:
    """Extract CVE details only for CVEs referenced by blocking policies."""
    vulnerabilities = metadata.get("vulnerabilities", {})
    
    needed = set()
    for policy in blocking:
        needed.update(policy.cve_ids)
    
    details = {}
    for cve_id in needed:
        cve = vulnerabilities.get(cve_id, {})
        flags = cve.get("exploit", [])
        details[cve_id] = {
            "cvss": cve.get("cvss", {}).get("baseScore"),
            "exploited": "EXISTS" in flags,
            "fixable": "FIXABLE" in flags,
        }
    
    return details