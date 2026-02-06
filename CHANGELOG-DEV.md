# Development Changelog

This file tracks significant changes made during development. Claude Code updates this after completing each task.

---

## How to Use

After completing a task, Claude adds an entry:

```
## [Date] - Phase X.X: Task Name

**What changed:**
- File1.py: Brief description
- File2.py: Brief description

**Why:**
One sentence explaining the reason.

**Verification:**
- [ ] Tests pass
- [ ] Lints pass
```

---

## Changelog

<!-- Claude: Add new entries below this line, newest first -->

### 2026-02-06 - Phase 6: Code Quality Workflows

**What changed:**
- `pyproject.toml`: Created — ruff (E/F/W/I/N/UP/B/C4, line-length 100), black (line-length 100), pytest (testpaths) config
- `.github/workflows/ci.yml`: Created — lint, test, security jobs on push/PR to main
- `.github/dependabot.yml`: Created — weekly pip + github-actions updates
- `.gitignore`: Converted from UTF-16 to UTF-8 (black couldn't read it)
- `src/policy_config.py`: Fixed E501 line-too-long (split ternary into if/else)
- `src/*.py`, `tests/*.py`: Auto-fixed import sorting (I001), trailing whitespace (W293), missing newlines (W292) via ruff --fix; reformatted via black

**Why:**
Automated quality gates so regressions are caught on every push/PR. Ruff replaces standalone isort/flake8, black enforces consistent formatting, Trivy scans for security issues, and dependabot keeps dependencies current.

**Verification:**
- [x] `ruff check src/ tests/` — 0 errors
- [x] `black --check src/ tests/` — 0 reformats needed
- [x] `pytest tests/ -v` — 63/63 pass

---

### 2026-02-06 - Phase 4: Real-World Testing

**What changed:**
- `tests/fixtures/analyst_workbench_policy.info`: Created — full analyst-workbench config with 2 filters (http.py + networks.py), including author/timestamp fields
- `tests/test_policy_config.py`: Added `test_load_analyst_workbench_policy_config` test + updated `__main__` test list
- `CONTRIBUTING.md`: Added "End-to-End Testing" section with `--dry-run` examples

**Why:**
Validate the parser handles the actual analyst-workbench config (2 filters, author/timestamp metadata) — not just simplified single-filter fixtures.

**Verification:**
- [x] `pytest tests/ -v` passes (63/63)
- [x] `ruff check src/ tests/` passes

---

### 2026-02-06 - Phase 3: Packaging Clarification

**What changed:**
- `README.md`: Renamed "Standalone CLI" to "Local Testing (CLI)", added `--policy-config` to CLI Options table, added "Policy Config Support" section explaining auto-detection, manual override, and what gets suppressed
- `CONTRIBUTING.md`: Created — dev setup, running tests/lints, code style, project structure, architecture overview

**Why:**
Clarify that the primary interface is the reusable workflow (not CLI), document the policy config feature that was added in Phase 1 but missing from docs, and provide a minimal contributing guide.

**Verification:**
- [x] `pytest tests/ -v` passes (62/62)
- [x] `ruff check src/ tests/` passes
- [x] Visual review of README for accuracy

---

### 2026-02-06 - Phase 2: Test Robustness

**What changed:**
- `tests/test_github_issues.py`: Created — 12 mock-based tests covering GitHubClient constructor, find_open_issue, create_issue, and create_if_new
- `tests/test_workflow_integration.py`: Created — 6 contract tests validating workflow YAML inputs match CLI definitions
- `tests/test_policy_config.py`: Extended — 7 edge case tests (empty config, comments-only, whitespace-only, unicode tokenizer, malformed input, default pattern, empty secrets block)

**Why:**
Increase test coverage from 37 to 62 tests. Previously untested: github_issues module (0 tests), workflow-CLI contract (0 tests), and parser edge cases (empty/malformed inputs).

**Verification:**
- [x] `pytest tests/ -v` passes (62/62)
- [x] `ruff check tests/test_github_issues.py tests/test_workflow_integration.py` passes

---

### 2026-02-06 - Phase 1.5/1.6: Code Cleanup Audit

**What changed:**
- `src/main.py`: Removed unused `ScanResult` import (line 8)

**Why:**
Audit of all `src/` files found one unused import. No pineapple references, dead code, commented code, debug prints, or TODOs in any source file.

**Verification:**
- [x] `pytest tests/ -v` passes (37/37)
- [x] `ruff check src/` passes

---

### [Template Entry]

**What changed:**
- (files modified)

**Why:**
(reason for change)

**Verification:**
- [ ] `pytest tests/ -v` passes
- [ ] `ruff check src/` passes

---

<!-- 
INSTRUCTIONS FOR CLAUDE:

After completing any task from implementation-plan.md:
1. Add a new entry at the top of the Changelog section
2. List every file you modified
3. Briefly explain what changed and why
4. Note verification status

Keep entries concise but complete. Omar will review this to understand what was done.
-->
