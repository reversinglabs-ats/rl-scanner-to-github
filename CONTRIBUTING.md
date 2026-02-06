# Contributing to rl-scanner-to-github

## Development Setup

```bash
git clone https://github.com/reversinglabs-ats/rl-scanner-to-github.git
cd rl-scanner-to-github
pip install requests pyyaml ruff black pytest
```

## Running Tests

```bash
pytest tests/ -v
```

All tests use mocks for external services (GitHub API). No tokens or network access required.

## Linting and Formatting

```bash
# Check for lint errors
ruff check src/ tests/

# Format code
black src/ tests/
```

## Code Style

- **Formatter:** black (default settings)
- **Linter:** ruff
- Docstrings for every function
- Type hints for function signatures
- No commented-out code, unused imports, or debug prints

## Project Structure

```
src/
  main.py           # CLI entrypoint (argparse)
  parse_report.py   # rl-json report parsing
  policy_config.py  # Policy config (.info) parsing and filtering
  enrich.py         # Metadata enrichment (severity, remediation)
  github_issues.py  # GitHub API client
tests/
  fixtures/         # Test data files
  test_*.py         # Test files mirror src/
.github/workflows/
  create-issues.yml # Reusable workflow (primary interface)
```

## Architecture

- **Primary interface:** Reusable GitHub Actions workflow via `uses:`
- **Secondary interface:** CLI for local testing and debugging
- Other repositories consume this via `uses: reversinglabs-ats/rl-scanner-to-github/.github/workflows/create-issues.yml@main`
