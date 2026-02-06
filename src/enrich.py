"""Load policy metadata from rl-scanner-metadata."""

import json
from pathlib import Path

PREFIX_TO_FILE = {
    "SQ12": "licenses.json",
    "SQ14": "windows.json",
    "SQ18": "linux.json",
    "SQ20": "signatures.json",
    "SQ25": "integrity.json",
    "SQ30": "threats.json",
    "SQ31": "vulnerabilities.json",
    "SQ34": "secrets.json",
    "SQ40": "containers.json",
    "TH": "hunting.json",
}


def _get_file_for_policy(policy_id: str) -> str | None:
    """Return filename for policy ID based on prefix."""
    for prefix, filename in PREFIX_TO_FILE.items():
        if policy_id.startswith(prefix):
            return filename
    return None


def load_policy_metadata(policy_ids: list[str], metadata_dir: Path) -> dict[str, dict]:
    """Load metadata for given policy IDs.

    Args:
        policy_ids: List of policy IDs like ["SQ31102", "SQ34101"]
        metadata_dir: Path to metadata directory containing JSON files

    Returns:
        Dict mapping policy_id to {label, description, steps}
    """
    files_to_load: dict[str, list[str]] = {}
    for pid in policy_ids:
        filename = _get_file_for_policy(pid)
        if filename:
            files_to_load.setdefault(filename, []).append(pid)

    result = {}
    for filename, pids in files_to_load.items():
        filepath = metadata_dir / filename
        if not filepath.exists():
            continue
        data = json.loads(filepath.read_text(encoding="utf-8"))
        for pid in pids:
            if pid not in data:
                continue
            policy_loc = data[pid].get("policy", {}).get("localization", [])
            en_loc = next((loc for loc in policy_loc if loc.get("language") == "en-US"), None)
            if not en_loc:
                continue
            result[pid] = {
                "label": en_loc.get("label", ""),
                "description": en_loc.get("description", ""),
                "steps": [s["content"] for s in en_loc.get("steps", []) if "content" in s],
                "rl_level": data[pid].get("quality", {}).get("rl-level"),
            }
    return result
