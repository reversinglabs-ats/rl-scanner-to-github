# GitHub Issue Creator - Implementation Plan

## Overview

This document outlines the exact steps to refine the `rl-scanner-to-github` tool based on code review feedback. Each phase must be completed and verified before moving to the next.

**Principles:**
- Tight, meaningful code — every line has a purpose
- No redundant or dead code
- Simple over complex
- Plan extensively, execute in small increments

---

## Current State Assessment

### What Exists
- `src/main.py` — CLI entrypoint + issue creation logic
- `src/parse_report.py` — Parses rl-json reports
- `src/policy_config.py` — Parses .info policy configs for suppression
- `src/enrich.py` — Loads metadata from rl-scanner-metadata submodule
- `src/github_issues.py` — GitHub API interaction
- `.github/workflows/create-issues.yml` — Reusable workflow
- `tests/` — Unit tests with fixtures

### What Needs Work (Fernando's Notes)
1. Add unit tests for GitHub issue interaction with workflow
2. Remove pineapple references, clean up claude.md
3. Clarify packaging — is it a reusable workflow? public/private?
4. Improve README (examples: discord.py, yara)
5. Test with real analyst-workbench policy config
6. Evaluate CLI removal — is it needed or just workflow?
7. Add code quality workflows (ruff, black, trivy, dependabot)
8. Version and release (last step)

---

## Phase 1: Code Cleanup & Dead Code Removal

**Goal:** Remove all unnecessary code, ensure every line has a purpose

### Task 1.1: Audit src/policy_config.py
- [ ] Review tokenizer — is every function used?
- [ ] Review parser — any dead branches?
- [ ] Check for debug print statements
- [ ] Remove any commented-out code
- [ ] Verify all helper functions are called

**Verification:** `grep -r "def " src/policy_config.py` → every function should have a caller

### Task 1.2: Audit src/main.py
- [ ] Check for unused imports
- [ ] Check for unused variables
- [ ] Ensure error handling is consistent
- [ ] Remove any TODO comments that are done

**Verification:** Run `ruff check src/` with no warnings

### Task 1.3: Audit src/parse_report.py
- [ ] Verify all dataclass fields are used
- [ ] Check for redundant parsing logic
- [ ] Ensure CVE extraction is clean

### Task 1.4: Audit src/enrich.py
- [ ] Check metadata loading is minimal
- [ ] No unnecessary file reads

### Task 1.5: Audit src/github_issues.py
- [ ] API calls are clean
- [ ] Error handling is consistent
- [ ] No redundant retry logic

### Task 1.6: Remove pineapple references
- [ ] Search entire repo for "pineapple"
- [ ] Remove any test artifacts or joke code

**Command:** `grep -ri "pineapple" . --include="*.py" --include="*.md" --include="*.yml"`

**Note:** Keep `claude.md` — it contains our coding guidelines. Remove it only at the very end (Phase 7) before public release if desired.

---

## Phase 2: Test Robustness

**Goal:** Add comprehensive tests for GitHub interaction and workflow calling conventions

### Task 2.1: Mock GitHub API tests
Create `tests/test_github_issues.py`:

```python
"""Tests for GitHub issue creation with mocked API."""

def test_create_issue_success():
    """Test successful issue creation returns issue URL."""
    # Mock requests.post to return 201
    # Verify correct payload sent
    # Verify URL returned

def test_create_issue_already_exists():
    """Test duplicate detection skips creation."""
    # Mock search to return existing issue
    # Verify no POST called
    # Verify returns existing URL

def test_create_issue_auth_failure():
    """Test handles 401 gracefully."""
    # Mock 401 response
    # Verify appropriate error message

def test_create_issue_rate_limit():
    """Test handles 429 rate limit."""
    # Mock 429 response
    # Verify retry or graceful failure

def test_issue_body_format():
    """Test issue body contains required sections."""
    # Verify markdown structure
    # Verify CVE table format
    # Verify remediation steps present
```

### Task 2.2: Workflow integration tests
Create `tests/test_workflow_integration.py`:

```python
"""Tests for workflow calling conventions."""

def test_workflow_inputs_match_cli_args():
    """Verify workflow inputs map to CLI arguments correctly."""
    # Parse workflow YAML
    # Parse argparse in main.py
    # Verify 1:1 mapping

def test_workflow_default_values():
    """Verify workflow defaults match expected behavior."""
    # Check metadata-dir default
    # Check max-issues default
    # Check policy-config auto-detection

def test_env_vars_set_correctly():
    """Verify GITHUB_TOKEN and GITHUB_REPOSITORY are used."""
    # Mock environment
    # Verify client uses correct values
```

### Task 2.3: Policy config edge case tests
Add to `tests/test_policy_config.py`:

```python
def test_empty_config_file():
    """Empty file returns empty PolicyConfig."""

def test_malformed_braces():
    """Unmatched braces don't crash, return partial result."""

def test_missing_required_fields():
    """Filter without pattern uses default '*'."""

def test_deeply_nested_structure():
    """Handles 5+ levels of nesting."""

def test_unicode_in_secrets():
    """Handles unicode characters in secret strings."""

def test_very_long_config():
    """Handles config with 100+ filters without timeout."""
```

**Verification:** `python -m pytest tests/ -v` — all pass, no warnings

---

## Phase 3: Packaging Clarification

**Goal:** Make it crystal clear how this is packaged and used

### Task 3.1: Determine primary use case
Answer these questions in README:
- Is this a reusable workflow called by other repos? **YES**
- Is the CLI for local testing only? **YES**
- Should other repos vendor this or reference it? **Reference via `uses:`**

### Task 3.2: Update README structure
Follow examples from discord.py and yara repos:

```markdown
# rl-scanner-to-github

Create GitHub Issues from ReversingLabs Spectra Assure scan results.

## Quick Start (Reusable Workflow)

```yaml
jobs:
  create-issues:
    uses: reversinglabs-ats/rl-scanner-to-github/.github/workflows/create-issues.yml@v1
    with:
      report-path: ./report.rl.json
    secrets:
      github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Features
- One issue per blocking policy (not per file)
- Deduplicates against existing open issues
- Respects policy config suppressions
- Enriches with severity, priority, remediation steps

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `report-path` | Yes | — | Path to report.rl.json |
| `policy-config` | No | auto-detect | Path to policy config |
| `max-issues` | No | 10 | Safety limit |
| `level` | No | — | Filter by rl-level |

## Local Testing (CLI)

For testing without CI:
```bash
python src/main.py --report report.rl.json --dry-run
```

## Policy Config Support

Automatically reads `.repository-policy.info` to skip suppressed findings...
```

### Task 3.3: Add CONTRIBUTING.md
```markdown
# Contributing

## Development Setup
1. Clone repo
2. `pip install requests ruff black pytest`
3. Run tests: `pytest tests/`
4. Run lints: `ruff check src/`

## Code Style
- Use `black` for formatting
- Use `ruff` for linting
- Every function needs a docstring
- Every line of code needs a purpose
```

---

## Phase 4: Real-World Testing

**Goal:** Verify with actual analyst-workbench data

### Task 4.1: Create test repo
- Create `reversinglabs-ats/rl-scanner-test` (or similar)
- Add a simple FastAPI project with intentional secrets
- Add `.repository-policy.info` with suppressions

### Task 4.2: Get real rl-secure report
- Run rl-secure scan on test repo
- Export report.rl.json
- Copy to `tests/fixtures/analyst_workbench_report.json`

### Task 4.3: Test with real policy config
Use the actual file:
```
https://github.com/reversinglabs-ats/analyst-workbench/blob/main/.rl-secure-config/.repository-policy.info
```

- Copy to `tests/fixtures/analyst_workbench_policy.info`
- Add test that parses it successfully
- Verify both filters (http.py and networks.py) are found

### Task 4.4: End-to-end dry run
```bash
python src/main.py \
  --report tests/fixtures/analyst_workbench_report.json \
  --policy-config tests/fixtures/analyst_workbench_policy.info \
  --metadata-dir data/rl-scanner-metadata/data \
  --dry-run
```

**Verify:**
- Correct policies identified
- Suppressed items filtered
- Issue bodies look correct

---

## Phase 5: CLI Evaluation

**Goal:** Decide if CLI stays, goes, or gets simplified

### Task 5.1: Evaluate CLI usage
Questions:
- Who uses the CLI? (developers testing locally)
- Is it documented? (yes, in README)
- Does it add complexity? (minimal — just argparse)

### Task 5.2: Decision
**Recommendation:** Keep CLI for local testing, but:
- Mark it clearly as "for testing only"
- Don't add new CLI-only features
- Primary interface is the reusable workflow

### Task 5.3: If removing CLI (optional)
- Move logic from `main.py` into module functions
- Workflow calls functions directly via inline Python
- Remove argparse entirely

**Skip this unless team decides CLI adds no value**

---

## Phase 6: Code Quality Workflows

**Goal:** Add automated quality checks

### Task 6.1: Create `.github/workflows/ci.yml`
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install ruff black
      - run: ruff check src/ tests/
      - run: black --check src/ tests/

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: true
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install requests pytest
      - run: pytest tests/ -v

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Trivy
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
```

### Task 6.2: Create `dependabot.yml`
```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

### Task 6.3: Create `pyproject.toml`
```toml
[tool.ruff]
line-length = 100
select = ["E", "F", "W", "I", "N", "UP", "B", "C4"]

[tool.black]
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### Task 6.4: Fix any lint errors
- Run `ruff check src/ tests/ --fix`
- Run `black src/ tests/`
- Commit fixes

---

## Phase 7: Versioning & Release

**Goal:** Set up proper versioning (do this LAST)

### Task 7.1: Add version to code
In `src/__init__.py`:
```python
__version__ = "1.0.0"
```

### Task 7.2: Create release workflow
```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          generate_release_notes: true
```

### Task 7.3: Tag first release
```bash
git tag -a v1.0.0 -m "Initial release"
git push origin v1.0.0
```

### Task 7.4: Update workflow reference
Other repos should use:
```yaml
uses: reversinglabs-ats/rl-scanner-to-github/.github/workflows/create-issues.yml@v1
```

---

## Execution Checklist

```
Phase 1: Code Cleanup
  [ ] 1.1 Audit policy_config.py
  [ ] 1.2 Audit main.py
  [ ] 1.3 Audit parse_report.py
  [ ] 1.4 Audit enrich.py
  [ ] 1.5 Audit github_issues.py
  [ ] 1.6 Remove pineapple/claude.md
      ↓
Phase 2: Test Robustness
  [ ] 2.1 Mock GitHub API tests
  [ ] 2.2 Workflow integration tests
  [ ] 2.3 Policy config edge cases
      ↓
Phase 3: Packaging Clarification
  [ ] 3.1 Determine primary use case
  [ ] 3.2 Update README
  [ ] 3.3 Add CONTRIBUTING.md
      ↓
Phase 4: Real-World Testing
  [ ] 4.1 Create test repo
  [ ] 4.2 Get real report
  [ ] 4.3 Test with real policy config
  [ ] 4.4 End-to-end dry run
      ↓
Phase 5: CLI Evaluation
  [ ] 5.1 Evaluate usage
  [ ] 5.2 Make decision
  [ ] 5.3 Implement if removing
      ↓
Phase 6: Code Quality Workflows
  [ ] 6.1 Create ci.yml
  [ ] 6.2 Create dependabot.yml
  [ ] 6.3 Create pyproject.toml
  [ ] 6.4 Fix lint errors
      ↓
Phase 7: Versioning & Release
  [ ] 7.1 Add version
  [ ] 7.2 Create release workflow
  [ ] 7.3 Tag first release
  [ ] 7.4 Update docs
```

---

## Notes for Claude Code

When executing this plan:

1. **Use /plan mode first** — Don't write code until plan is approved
2. **Small changes** — One task at a time, verify before next
3. **Show don't tell** — Run commands, show output, prove it works
4. **No fluff** — Every line of code must have a purpose
5. **Test after each change** — `pytest tests/ -v` must pass

**Quality bar:**
- `ruff check src/` returns 0 errors
- `black --check src/` returns 0 errors  
- All tests pass
- No TODO comments left in code
- No commented-out code
- No unused imports
- No unused functions