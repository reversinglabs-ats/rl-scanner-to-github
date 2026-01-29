# rl-github-issue-creator

Create GitHub Issues from ReversingLabs Spectra Assure scan results.

## What It Does

- Parses `rl-json` reports from Spectra Assure scans
- Extracts **only blocking policies** (status: fail)
- Creates **one issue per policy** (not per file)
- **Deduplicates** by checking for existing open issues
- Enriches with metadata from rl-scanner-metadata (optional)

## Filtering Logic

From 100+ violations, you might get 3-5 issues:

```
6 violations with status=fail for SQ31102  →  1 issue for SQ31102
2 violations with status=fail for SQ34108  →  1 issue for SQ34108
50 violations with status=pass             →  0 issues (not blocking)
```

## Usage

### As Reusable Workflow

```yaml
jobs:
  scan:
    # ... your scan job that uploads report artifact ...
    
  create-issues:
    needs: scan
    if: failure()
    uses: reversinglabs/rl-github-issue-creator/.github/workflows/create-issues.yml@main
    with:
      artifact-name: scan-reports
      report-filename: report.rl.json
      max-issues: 10
    secrets:
      token: ${{ secrets.GITHUB_TOKEN }}
```

### Standalone

```bash
git clone https://github.com/reversinglabs/rl-github-issue-creator.git
cd rl-github-issue-creator
pip install -r requirements.txt

# Set credentials
export GITHUB_TOKEN=ghp_...
export GITHUB_REPOSITORY=owner/repo

# Run
python src/main.py --report /path/to/report.rl.json

# Or preview first
python src/main.py --report /path/to/report.rl.json --dry-run
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--report` | required | Path to report.rl.json |
| `--metadata` | none | Path to rl-scanner-metadata |
| `--dry-run` | false | Preview without creating |
| `--max-issues` | 10 | Safety limit |

## Environment

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | Token with `issues:write` |
| `GITHUB_REPOSITORY` | Target repo (`owner/repo`) |
