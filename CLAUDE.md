# rl-scanner-to-github

## Project Purpose
Create GitHub Issues from ReversingLabs Spectra Assure scan failures. Only blocking violations (status=fail) become issues.

## Critical Design Rules
- ONE issue per policy_id, not per file (prevents spam)
- Only status="fail" violations are blocking
- Deduplication: check for existing open issues before creating
- No hardcoded secrets - all credentials from environment variables

## Code Standards
- Every line must have clear purpose - no fluff
- Minimal dependencies (stdlib when possible)
- No logging frameworks - use print for simplicity
- Let errors bubble up with clear messages
- Type hints on function signatures
- Brief docstrings explaining what, not how

## Project Structure
- src/parse_report.py - DONE - parses rl-json, extracts blocking policies
- src/github_issues.py - TODO - GitHub API wrapper with deduplication  
- src/enrich.py - TODO - load metadata from rl-scanner-metadata
- src/main.py - TODO - entry point
- tests/fixtures/ - sample reports for testing
- data/rl-scanner-metadata/ - git submodule with policy descriptions

## Current Status
- parse_report.py: DONE, tested
- Next: github_issues.py

## Testing
Run tests with: python tests/test_parse_report.py