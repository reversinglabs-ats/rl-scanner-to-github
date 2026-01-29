"""Test parse_report module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from parse_report import parse_report


def test_filtering_and_aggregation():
    """Test that we filter correctly and aggregate by policy_id."""
    fixture = Path(__file__).parent / "fixtures" / "sample_report.json"
    result = parse_report(fixture)
    
    # Basic scan info
    assert result.artifact_name == "test-app-v1.0.tar.gz"
    assert result.scan_level == 3
    assert result.scan_status == "fail"
    
    # 5 violations -> 2 blocking policies
    # v1, v2 (SQ31102, fail) -> 1 policy with 2 components
    # v3 (SQ34108, fail) -> 1 policy with 1 component
    # v4 (pass) -> filtered out
    # v5 (warning) -> filtered out
    assert len(result.blocking_policies) == 2, \
        f"Expected 2 policies, got {len(result.blocking_policies)}"
    
    policy_ids = {p.policy_id for p in result.blocking_policies}
    assert policy_ids == {"SQ31102", "SQ34108"}
    
    # Check SQ31102 aggregated 2 components
    sq31102 = next(p for p in result.blocking_policies if p.policy_id == "SQ31102")
    assert len(sq31102.components) == 2
    
    # Check CVE linked
    assert "CVE-2024-1234" in sq31102.cve_ids
    assert result.cve_details["CVE-2024-1234"]["exploited"] is True
    
    print("PASS: 5 violations filtered to 2 blocking policies")
    print(f"  - SQ31102: {len(sq31102.components)} components")
    print(f"  - SQ34108: 1 component")
    print(f"  - Filtered out: v4 (pass), v5 (warning)")


if __name__ == "__main__":
    test_filtering_and_aggregation()
    print("\nAll tests passed!")