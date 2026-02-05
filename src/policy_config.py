"""Parse policy config files (.info) and filter violations accordingly.

Policy config files use Boost INFO format (HCL-like) with:
- Blocks: name { ... } or name "label" { ... }
- Key-value: key value or key = value
- Lists: secrets { "item1" "item2" }
- Comments: ; (semicolon)
"""

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

from parse_report import BlockingPolicy


@dataclass
class Filter:
    """A filter from the policy config (secrets, policies, or triaged block)."""
    enabled: bool
    matches: str  # "file", "path", "root"
    pattern: str  # filename, glob, or "*"
    reason: str
    filter_type: str  # "secrets", "policies", "triaged"
    secrets: list[str] = field(default_factory=list)
    policies: list[str] = field(default_factory=list)
    cves: list[str] = field(default_factory=list)
    vex_reasons: dict[str, str] = field(default_factory=dict)


@dataclass
class FilteredItem:
    """Record of a filtered policy/component for logging."""
    policy_id: str
    component_path: str
    reason: str


@dataclass
class PolicyConfig:
    """Parsed policy config with disabled policies and filters."""
    disabled_policies: set[str] = field(default_factory=set)
    filters: list[Filter] = field(default_factory=list)


def tokenize(text: str) -> list[str]:
    """Tokenize Boost INFO format text into tokens."""
    tokens = []
    i = 0
    while i < len(text):
        c = text[i]
        if c in " \t\n\r":
            i += 1
        elif c == ";":
            # Comment - skip to end of line
            while i < len(text) and text[i] != "\n":
                i += 1
        elif c in "{}=":
            tokens.append(c)
            i += 1
        elif c == '"':
            # Quoted string
            i += 1
            start = i
            while i < len(text) and text[i] != '"':
                if text[i] == "\\" and i + 1 < len(text):
                    i += 2
                else:
                    i += 1
            tokens.append(text[start:i])
            if i < len(text):
                i += 1
        else:
            # Unquoted word
            start = i
            while i < len(text) and text[i] not in " \t\n\r{}=;\"":
                i += 1
            if start < i:
                tokens.append(text[start:i])
    return tokens


def _parse_block(tokens: list[str], pos: int) -> tuple[dict, int]:
    """Parse a block starting at pos, returns (block_dict, new_pos)."""
    block = {"_items": []}
    pos += 1  # skip opening brace
    while pos < len(tokens) and tokens[pos] != "}":
        tok = tokens[pos]
        if tok == "{":
            # Anonymous nested block - skip
            nested, pos = _parse_block(tokens, pos)
        elif pos + 1 < len(tokens) and tokens[pos + 1] == "{":
            # Named block: name { ... }
            name = tok
            nested, pos = _parse_block(tokens, pos + 1)
            # Collect multiple blocks with same name as list
            if name in block:
                if isinstance(block[name], list):
                    block[name].append(nested)
                else:
                    block[name] = [block[name], nested]
            else:
                block[name] = nested
        elif pos + 2 < len(tokens) and tokens[pos + 2] == "{":
            # Labeled block: name "label" { ... }
            name = tok
            label = tokens[pos + 1]
            nested, pos = _parse_block(tokens, pos + 2)
            nested["_label"] = label
            block.setdefault(name, [])
            if isinstance(block[name], list):
                block[name].append(nested)
            else:
                block[name] = [block[name], nested]
        elif pos + 1 < len(tokens) and tokens[pos + 1] == "=":
            # Key = value
            block[tok] = tokens[pos + 2] if pos + 2 < len(tokens) else ""
            pos += 3
            continue
        elif pos + 1 < len(tokens) and tokens[pos + 1] not in "{=}":
            # Key value (no equals)
            block[tok] = tokens[pos + 1]
            pos += 2
            continue
        else:
            # Standalone item (like string in a list)
            block["_items"].append(tok)
            pos += 1
    return block, pos + 1  # skip closing brace


def parse_policy_config(text: str) -> PolicyConfig:
    """Parse policy config text and extract filters & overrides."""
    tokens = tokenize(text)
    config = PolicyConfig()

    pos = 0
    while pos < len(tokens):
        tok = tokens[pos]

        if tok == "policies" and pos + 1 < len(tokens) and tokens[pos + 1] == "{":
            # Nested format: policies { profile "name" { processing { ... } } }
            block, pos = _parse_block(tokens, pos + 1)
            _extract_from_policies_block(block, config)
        elif tok == "processing" and pos + 1 < len(tokens) and tokens[pos + 1] == "{":
            # Flat format (backwards compat): processing { secrets "*.py" { ... } }
            block, pos = _parse_block(tokens, pos + 1)
            _extract_processing_filters(block, config)
        elif tok == "overrides" and pos + 1 < len(tokens) and tokens[pos + 1] == "{":
            block, pos = _parse_block(tokens, pos + 1)
            _extract_overrides(block, config)
        elif pos + 1 < len(tokens) and tokens[pos + 1] == "{":
            # Skip other top-level blocks
            _, pos = _parse_block(tokens, pos + 1)
        else:
            pos += 1

    return config


def _extract_from_policies_block(block: dict, config: PolicyConfig) -> None:
    """Extract filters from nested policies { profile { ... } } structure."""
    profiles = block.get("profile", [])
    if isinstance(profiles, dict):
        profiles = [profiles]

    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        if "processing" in profile:
            _extract_processing_filters(profile["processing"], config)
        if "overrides" in profile:
            _extract_overrides(profile["overrides"], config)


def _extract_processing_filters(block: dict, config: PolicyConfig) -> None:
    """Extract filters from processing block.

    Supports two formats:
    1. Legacy labeled blocks: secrets "*.py" { ... }
    2. New filter blocks: filter { pattern "*.py" secrets { ... } }
    """
    # Handle new format: filter { } blocks
    filters = block.get("filter", [])
    if isinstance(filters, dict):
        filters = [filters]
    for f in filters:
        if not isinstance(f, dict):
            continue
        filt = _extract_filter_block(f)
        if filt:
            config.filters.append(filt)

    # Handle legacy format: secrets/policies/triaged "pattern" { }
    for filter_type in ("secrets", "policies", "triaged"):
        labeled_blocks = block.get(filter_type, [])
        if isinstance(labeled_blocks, dict):
            labeled_blocks = [labeled_blocks]
        for f in labeled_blocks:
            if not isinstance(f, dict):
                continue
            filt = _extract_legacy_filter(f, filter_type)
            if filt:
                config.filters.append(filt)


def _extract_filter_block(f: dict) -> Filter | None:
    """Extract filter from new format: filter { pattern "..." secrets { } }."""
    enabled_val = f.get("enabled", "true")
    enabled = str(enabled_val).lower() != "false"
    matches = f.get("matches", "file")
    pattern = f.get("pattern", "*")
    reason = f.get("reason", "")

    # Determine filter type from inner block
    filter_type = None
    if "secrets" in f:
        filter_type = "secrets"
    elif "policies" in f:
        filter_type = "policies"
    elif "triaged" in f:
        filter_type = "triaged"

    if not filter_type:
        return None

    filt = Filter(
        enabled=enabled,
        matches=matches,
        pattern=pattern,
        reason=reason,
        filter_type=filter_type,
    )

    _populate_filter_items(filt, f, filter_type)
    return filt


def _extract_legacy_filter(f: dict, filter_type: str) -> Filter | None:
    """Extract filter from legacy format: secrets "pattern" { ... }."""
    enabled_val = f.get("enabled", "true")
    enabled = str(enabled_val).lower() != "false"
    matches = f.get("matches", "file")
    pattern = f.get("_label", "*")
    reason = f.get("reason", "")

    # For policies filter, check blocker - only suppress when blocker=pass
    if filter_type == "policies":
        blocker = f.get("blocker", "fail")
        if blocker.lower() != "pass":
            return None

    filt = Filter(
        enabled=enabled,
        matches=matches,
        pattern=pattern,
        reason=reason,
        filter_type=filter_type,
    )

    _populate_filter_items(filt, f, filter_type)
    return filt


def _populate_filter_items(filt: Filter, f: dict, filter_type: str) -> None:
    """Populate filter items (secrets, policies, or CVEs) from block."""
    if filter_type == "secrets":
        secrets_block = f.get("secrets", {})
        if isinstance(secrets_block, dict):
            filt.secrets = secrets_block.get("_items", [])
    elif filter_type == "policies":
        policies_block = f.get("policies", {})
        if isinstance(policies_block, dict):
            filt.policies = policies_block.get("_items", [])
    elif filter_type == "triaged":
        triaged_block = f.get("triaged", {})
        if isinstance(triaged_block, dict):
            for cve in triaged_block.get("_items", []):
                filt.cves.append(cve)
            # Check for VEX reasons (key-value pairs)
            for key, val in triaged_block.items():
                if key.startswith("CVE-"):
                    filt.cves.append(key)
                    filt.vex_reasons[key] = val


def _extract_overrides(block: dict, config: PolicyConfig) -> None:
    """Extract disabled policies from overrides block."""
    policies = block.get("policies", [])
    if isinstance(policies, dict):
        policies = [policies]
    for p in policies:
        if not isinstance(p, dict):
            continue
        if p.get("enabled", "true").lower() == "false":
            policy_id = p.get("_label", "")
            if policy_id:
                config.disabled_policies.add(policy_id)


def load_policy_config(path: Path) -> PolicyConfig:
    """Load and parse a policy config file."""
    text = path.read_text(encoding="utf-8")
    return parse_policy_config(text)


def find_policy_config(search_dir: Path) -> Path | None:
    """Auto-detect policy config file in order of precedence."""
    levels = ("package", "project", "repository")
    prefixes = ("", ".")
    subdirs = ("", ".rl-secure")

    for level in levels:
        for subdir in subdirs:
            base = search_dir / subdir if subdir else search_dir
            if not base.exists():
                continue
            for prefix in prefixes:
                # Try both naming conventions
                names = [
                    f"{prefix}{level}-policy.info",      # package-policy.info
                    f"{prefix}{level}_policy.info",      # .package_policy.info
                ]
                for name in names:
                    path = base / name
                    if path.exists():
                        return path
    return None


def _matches_path(pattern: str, component_path: str, match_type: str) -> bool:
    """Check if component path matches the filter pattern."""
    if pattern == "*":
        return True

    # Normalize path separators
    path = component_path.replace("\\", "/")

    if match_type == "file":
        # Match against filename only
        filename = path.rsplit("/", 1)[-1]
        return fnmatch(filename, pattern)
    elif match_type == "path":
        # Match against full path
        return fnmatch(path, pattern)
    elif match_type == "root":
        # Match from archive root (strip leading /)
        path = path.lstrip("/")
        return fnmatch(path, pattern)
    return False


def _matches_policy_id(patterns: list[str], policy_id: str) -> bool:
    """Check if policy ID matches any pattern (supports wildcards)."""
    return any(fnmatch(policy_id, p) for p in patterns)


def _all_cves_triaged(cve_ids: list[str], triaged_cves: list[str]) -> bool:
    """Check if ALL CVEs are covered by triaged patterns."""
    if not cve_ids:
        return False
    for cve in cve_ids:
        if not any(fnmatch(cve, pattern) for pattern in triaged_cves):
            return False
    return True


def filter_policies(
    policies: list[BlockingPolicy],
    config: PolicyConfig,
) -> tuple[list[BlockingPolicy], list[FilteredItem]]:
    """Filter policies based on policy config.

    Returns:
        Tuple of (remaining_policies, filtered_items)
    """
    filtered_items = []
    result = []

    for policy in policies:
        # Check if policy is disabled
        if policy.policy_id in config.disabled_policies:
            for comp in policy.components:
                filtered_items.append(FilteredItem(
                    policy_id=policy.policy_id,
                    component_path=comp.path,
                    reason="Policy disabled in overrides",
                ))
            continue

        # Check disabled via wildcard
        disabled = False
        for disabled_id in config.disabled_policies:
            if fnmatch(policy.policy_id, disabled_id):
                for comp in policy.components:
                    filtered_items.append(FilteredItem(
                        policy_id=policy.policy_id,
                        component_path=comp.path,
                        reason="Policy disabled in overrides",
                    ))
                disabled = True
                break
        if disabled:
            continue

        # Filter components
        remaining_components = []
        for comp in policy.components:
            suppressed = False
            reason = ""

            for filt in config.filters:
                if not filt.enabled:
                    continue
                if not _matches_path(filt.pattern, comp.path, filt.matches):
                    continue

                if filt.filter_type == "secrets" and policy.category == "secrets":
                    # Secrets filter - check if secret type matches
                    if not filt.secrets or _matches_policy_id(filt.secrets, policy.policy_id):
                        suppressed = True
                        reason = filt.reason or "Suppressed by secrets filter"
                        break

                elif filt.filter_type == "policies":
                    if _matches_policy_id(filt.policies, policy.policy_id):
                        suppressed = True
                        reason = filt.reason or "Suppressed by policies filter"
                        break

                elif filt.filter_type == "triaged":
                    if _all_cves_triaged(policy.cve_ids, filt.cves):
                        suppressed = True
                        vex = ", ".join(f"{c}: {filt.vex_reasons.get(c, 'triaged')}"
                                       for c in policy.cve_ids if c in filt.vex_reasons)
                        reason = filt.reason or f"All CVEs triaged ({vex})" if vex else "All CVEs triaged"
                        break

            if suppressed:
                filtered_items.append(FilteredItem(
                    policy_id=policy.policy_id,
                    component_path=comp.path,
                    reason=reason,
                ))
            else:
                remaining_components.append(comp)

        # Keep policy only if it has remaining components
        if remaining_components:
            result.append(BlockingPolicy(
                policy_id=policy.policy_id,
                category=policy.category,
                severity=policy.severity,
                priority=policy.priority,
                effort=policy.effort,
                components=remaining_components,
                cve_ids=policy.cve_ids,
            ))

    return result, filtered_items
