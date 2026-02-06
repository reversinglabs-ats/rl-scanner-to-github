# Claude Code Guidelines for rl-scanner-to-github

## Core Principles

**Every line of code must have a purpose.** If you can't explain why a line exists, delete it.

## Workflow

1. **Plan first, code later**
   - Always use `/plan` mode before making changes
   - Refine the plan until it's crystal clear
   - Small, incremental changes only
   - Verify each change before the next

2. **Before writing any code, ask:**
   - Is this necessary?
   - Is there a simpler way?
   - Does this duplicate existing code?
   - Will this be easy to test?

## Code Quality Rules

### Do
- One function, one job
- Clear variable names (no `x`, `temp`, `data`)
- Docstrings for every function
- Type hints for function signatures
- Handle errors explicitly
- Return early to reduce nesting

### Don't
- No commented-out code
- No TODO comments (do it or delete it)
- No unused imports
- No unused functions
- No debug print statements
- No copy-paste duplication
- No "just in case" code

## Testing

- Run `pytest tests/ -v` after every change
- Add tests for new functionality
- Test edge cases (empty input, malformed input, missing fields)
- Mock external services (GitHub API)

## File Structure

```
src/
  main.py           # CLI entrypoint only
  parse_report.py   # Report parsing only
  policy_config.py  # Policy config parsing only
  enrich.py         # Metadata enrichment only
  github_issues.py  # GitHub API only
tests/
  fixtures/         # Test data files
  test_*.py         # Test files mirror src/
```

## When Reviewing Code

Check for:
1. Dead code — functions never called
2. Redundant logic — same thing done twice
3. Over-engineering — complex solution for simple problem
4. Missing error handling
5. Unclear variable names
6. Missing tests

## Commands

```bash
# Lint
ruff check src/ tests/

# Format
black src/ tests/

# Test
pytest tests/ -v

# Check for dead code
vulture src/

# Check imports
isort --check src/ tests/
```

## Project Context

This is a **reusable GitHub workflow** that:
1. Parses rl-secure scan reports
2. Respects policy config suppressions
3. Creates GitHub issues for blocking policies
4. Enriches with metadata (severity, remediation)

Primary interface: GitHub Actions workflow
Secondary interface: CLI for local testing

## Current Focus

See `implementation-plan.md` for the detailed task list.
Execute one phase at a time. Verify before moving on.

## Logging Changes

**After completing any task, update `CHANGELOG-DEV.md`:**
1. Add entry at top of Changelog section
2. List files modified
3. Explain what and why (brief)
4. Note if tests/lints pass