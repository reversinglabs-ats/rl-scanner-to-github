"""Test policy_config module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from policy_config import (
    tokenize, parse_policy_config, load_policy_config, find_policy_config,
    filter_policies, _matches_path, _matches_policy_id, _all_cves_triaged,
)
from parse_report import BlockingPolicy, Component


def test_tokenizer_basic():
    """Test tokenizer handles basic elements."""
    tokens = tokenize('key value')
    assert tokens == ["key", "value"]


def test_tokenizer_strings():
    """Test tokenizer handles quoted strings."""
    tokens = tokenize('key "value with spaces"')
    assert tokens == ["key", "value with spaces"]


def test_tokenizer_braces():
    """Test tokenizer handles braces."""
    tokens = tokenize('block { inner }')
    assert tokens == ["block", "{", "inner", "}"]


def test_tokenizer_comments():
    """Test tokenizer skips semicolon comments."""
    tokens = tokenize('key value ; comment\nnext line')
    assert tokens == ["key", "value", "next", "line"]


def test_tokenizer_equals():
    """Test tokenizer handles key=value syntax."""
    tokens = tokenize('key = value')
    assert tokens == ["key", "=", "value"]


def test_parser_extracts_override():
    """Test parser extracts disabled policies from overrides."""
    config_text = '''
    overrides {
        policies "SQ12345" {
            enabled false
        }
    }
    '''
    config = parse_policy_config(config_text)
    assert "SQ12345" in config.disabled_policies


def test_parser_extracts_secrets_filter_legacy():
    """Test parser extracts secrets filter from legacy processing block."""
    config_text = '''
    processing {
        secrets "*.config" {
            enabled true
            matches file
            reason "Config secrets OK"
            secrets {
                "SQ34108"
            }
        }
    }
    '''
    config = parse_policy_config(config_text)
    assert len(config.filters) == 1
    f = config.filters[0]
    assert f.filter_type == "secrets"
    assert f.pattern == "*.config"
    assert f.matches == "file"
    assert f.reason == "Config secrets OK"
    assert "SQ34108" in f.secrets


def test_parser_extracts_secrets_filter_nested():
    """Test parser extracts secrets filter from nested filter block."""
    config_text = '''
    policies {
        profile "test" {
            processing {
                filter {
                    enabled true
                    matches file
                    pattern "*.config"
                    reason "Config secrets OK"
                    secrets { "SQ34108" }
                }
            }
        }
    }
    '''
    config = parse_policy_config(config_text)
    assert len(config.filters) == 1
    f = config.filters[0]
    assert f.filter_type == "secrets"
    assert f.pattern == "*.config"
    assert f.matches == "file"
    assert "SQ34108" in f.secrets


def test_parser_extracts_policies_filter_legacy():
    """Test parser extracts policies filter with blocker=pass (legacy format)."""
    config_text = '''
    processing {
        policies "/vendor/*" {
            enabled true
            matches path
            blocker pass
            reason "Vendor code accepted"
            policies {
                "SQ311*"
            }
        }
    }
    '''
    config = parse_policy_config(config_text)
    assert len(config.filters) == 1
    f = config.filters[0]
    assert f.filter_type == "policies"
    assert f.policies == ["SQ311*"]


def test_parser_extracts_policies_filter_nested():
    """Test parser extracts policies filter from nested filter block."""
    config_text = '''
    policies {
        profile "test" {
            processing {
                filter {
                    enabled true
                    matches path
                    pattern "/vendor/*"
                    reason "Vendor code accepted"
                    policies { "SQ311*" }
                }
            }
        }
    }
    '''
    config = parse_policy_config(config_text)
    assert len(config.filters) == 1
    f = config.filters[0]
    assert f.filter_type == "policies"
    assert f.pattern == "/vendor/*"
    assert f.policies == ["SQ311*"]


def test_parser_skips_blocker_fail():
    """Test parser skips policies filter when blocker=fail."""
    config_text = '''
    processing {
        policies "/app/*" {
            enabled true
            blocker fail
            policies { "SQ123" }
        }
    }
    '''
    config = parse_policy_config(config_text)
    assert len(config.filters) == 0


def test_parser_extracts_triaged_filter_legacy():
    """Test parser extracts triaged filter with VEX reasons (legacy format)."""
    config_text = '''
    processing {
        triaged "*" {
            enabled true
            reason "Triaged CVEs"
            triaged {
                CVE-2024-1234 vulnerable-code-not-present
                "CVE-2023-5678"
            }
        }
    }
    '''
    config = parse_policy_config(config_text)
    assert len(config.filters) == 1
    f = config.filters[0]
    assert f.filter_type == "triaged"
    assert "CVE-2024-1234" in f.cves
    assert "CVE-2023-5678" in f.cves
    assert f.vex_reasons.get("CVE-2024-1234") == "vulnerable-code-not-present"


def test_parser_extracts_triaged_filter_nested():
    """Test parser extracts triaged filter from nested filter block."""
    config_text = '''
    policies {
        profile "test" {
            processing {
                filter {
                    enabled true
                    matches root
                    pattern "*"
                    reason "Triaged CVEs"
                    triaged {
                        CVE-2024-1234 vulnerable-code-not-present
                        "CVE-2023-5678"
                    }
                }
            }
        }
    }
    '''
    config = parse_policy_config(config_text)
    assert len(config.filters) == 1
    f = config.filters[0]
    assert f.filter_type == "triaged"
    assert "CVE-2024-1234" in f.cves
    assert "CVE-2023-5678" in f.cves
    assert f.vex_reasons.get("CVE-2024-1234") == "vulnerable-code-not-present"


def test_filter_removes_disabled_policy():
    """Test filter_policies removes disabled policies."""
    from policy_config import PolicyConfig

    policies = [
        BlockingPolicy("SQ12345", "test", "high", 0, "high",
                       [Component("test", "/app/test")], []),
    ]
    config = PolicyConfig(disabled_policies={"SQ12345"})

    result, filtered = filter_policies(policies, config)
    assert len(result) == 0
    assert len(filtered) == 1
    assert filtered[0].reason == "Policy disabled in overrides"


def test_filter_removes_matched_component():
    """Test filter_policies removes matched components."""
    from policy_config import PolicyConfig, Filter

    policies = [
        BlockingPolicy("SQ34108", "secrets", "high", 0, "high",
                       [Component("config", "/app/config.py"),
                        Component("main", "/app/main.py")], []),
    ]
    config = PolicyConfig(filters=[
        Filter(enabled=True, matches="file", pattern="config.py",
               reason="Config OK", filter_type="secrets", secrets=["SQ34108"]),
    ])

    result, filtered = filter_policies(policies, config)
    assert len(result) == 1
    assert len(result[0].components) == 1
    assert result[0].components[0].path == "/app/main.py"
    assert len(filtered) == 1


def test_filter_removes_policy_when_all_components_filtered():
    """Test filter_policies removes policy when no components remain."""
    from policy_config import PolicyConfig, Filter

    policies = [
        BlockingPolicy("SQ34108", "secrets", "high", 0, "high",
                       [Component("config", "/app/config.py")], []),
    ]
    config = PolicyConfig(filters=[
        Filter(enabled=True, matches="file", pattern="*.py",
               reason="Python OK", filter_type="secrets", secrets=["SQ34108"]),
    ])

    result, filtered = filter_policies(policies, config)
    assert len(result) == 0
    assert len(filtered) == 1


def test_path_matching_file():
    """Test path matching with matches=file."""
    assert _matches_path("*.py", "/app/main.py", "file") is True
    assert _matches_path("*.py", "/app/main.js", "file") is False


def test_path_matching_path():
    """Test path matching with matches=path."""
    assert _matches_path("/lib/*", "/lib/ssl.so", "path") is True
    assert _matches_path("/lib/*", "/app/main.py", "path") is False


def test_path_matching_root():
    """Test path matching with matches=root."""
    assert _matches_path("lib/*", "/lib/ssl.so", "root") is True
    assert _matches_path("app/*", "/app/main.py", "root") is True


def test_path_matching_wildcard():
    """Test path matching with * pattern."""
    assert _matches_path("*", "/any/path/here", "file") is True


def test_policy_id_wildcard():
    """Test policy ID wildcard matching."""
    assert _matches_policy_id(["SQ311*"], "SQ31102") is True
    assert _matches_policy_id(["SQ311*"], "SQ34108") is False
    assert _matches_policy_id(["SQ*"], "SQ12345") is True


def test_cve_wildcard():
    """Test CVE wildcard matching."""
    assert _all_cves_triaged(["CVE-2024-1234"], ["CVE-2024-*"]) is True
    assert _all_cves_triaged(["CVE-2024-1234"], ["CVE-2023-*"]) is False
    assert _all_cves_triaged(["CVE-2024-1234", "CVE-2024-5678"], ["CVE-2024-*"]) is True


def test_triaged_requires_all_cves():
    """Test triaged filter only applies when ALL CVEs are triaged."""
    assert _all_cves_triaged(["CVE-2024-1234", "CVE-2025-9999"],
                             ["CVE-2024-1234"]) is False
    assert _all_cves_triaged(["CVE-2024-1234", "CVE-2025-9999"],
                             ["CVE-2024-*", "CVE-2025-*"]) is True


def test_load_policy_config():
    """Test loading policy config from file."""
    fixture = Path(__file__).parent / "fixtures" / "sample_policy.info"
    config = load_policy_config(fixture)

    assert "SQ14102" in config.disabled_policies
    assert len(config.filters) >= 3


def test_load_real_policy_config():
    """Test loading real analyst-workbench policy config."""
    fixture = Path(__file__).parent / "fixtures" / "real_policy.info"
    config = load_policy_config(fixture)

    assert len(config.filters) == 1
    f = config.filters[0]
    assert f.filter_type == "secrets"
    assert f.pattern == "http.py"
    assert f.matches == "file"
    assert "Authorization: Bearer deadbeef12346" in f.secrets


def test_parser_nested_override():
    """Test parser extracts overrides from nested profile."""
    config_text = '''
    policies {
        profile "test" {
            overrides {
                policies "SQ99999" {
                    enabled false
                }
            }
        }
    }
    '''
    config = parse_policy_config(config_text)
    assert "SQ99999" in config.disabled_policies


def test_find_policy_config_not_found():
    """Test find_policy_config returns None when no config exists."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        result = find_policy_config(Path(tmp))
        assert result is None


def test_find_policy_config_priority():
    """Test find_policy_config returns most specific config."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "package-policy.info").write_text("overrides {}")
        (tmp_path / "repository-policy.info").write_text("overrides {}")

        result = find_policy_config(tmp_path)
        assert result.name == "package-policy.info"


def test_find_policy_config_dot_prefix():
    """Test find_policy_config finds dot-prefixed files."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / ".repository_policy.info").write_text("overrides {}")

        result = find_policy_config(tmp_path)
        assert result is not None


def test_find_policy_config_rl_secure_subdir():
    """Test find_policy_config finds configs in .rl-secure subdir."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        rl_secure = tmp_path / ".rl-secure"
        rl_secure.mkdir()
        (rl_secure / "repository-policy.info").write_text("overrides {}")

        result = find_policy_config(tmp_path)
        assert result is not None
        assert ".rl-secure" in str(result)


if __name__ == "__main__":
    import traceback

    tests = [
        test_tokenizer_basic,
        test_tokenizer_strings,
        test_tokenizer_braces,
        test_tokenizer_comments,
        test_tokenizer_equals,
        test_parser_extracts_override,
        test_parser_extracts_secrets_filter_legacy,
        test_parser_extracts_secrets_filter_nested,
        test_parser_extracts_policies_filter_legacy,
        test_parser_extracts_policies_filter_nested,
        test_parser_skips_blocker_fail,
        test_parser_extracts_triaged_filter_legacy,
        test_parser_extracts_triaged_filter_nested,
        test_filter_removes_disabled_policy,
        test_filter_removes_matched_component,
        test_filter_removes_policy_when_all_components_filtered,
        test_path_matching_file,
        test_path_matching_path,
        test_path_matching_root,
        test_path_matching_wildcard,
        test_policy_id_wildcard,
        test_cve_wildcard,
        test_triaged_requires_all_cves,
        test_load_policy_config,
        test_load_real_policy_config,
        test_parser_nested_override,
        test_find_policy_config_not_found,
        test_find_policy_config_priority,
        test_find_policy_config_dot_prefix,
        test_find_policy_config_rl_secure_subdir,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS: {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}")
            traceback.print_exc()
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
