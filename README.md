# rl-scanner-to-github

Create GitHub Issues from ReversingLabs Spectra Assure scan results.

---

## Example Issue

**Title:** `[SQ31102] Detected presence of severe vulnerabilities with active exploitation.`

**Body:**

> **Severity:** high  
> **Priority:** P0  
> **Effort:** high
>
> Software composition analysis has identified a component with one or more known severe vulnerabilities...
>
> ### Affected Components
> - `bins/release/amd64/mip_ClientTelemetry.dll`
> - `bins/debug/amd64/mip_ClientTelemetry.dll`
>
> ### CVEs
> | CVE | CVSS | Exploited | Fixable |
> |-----|------|-----------|---------|
> | CVE-2022-37434 | 9.8 | Yes | Yes |
>
> ### Remediation Steps
> 1. We strongly advise updating the component to the latest version.
> 2. If the update can't resolve the issue, create a plan to isolate or replace the affected component.

---

## What It Does

- Parses `rl-json` reports from Spectra Assure scans
- Extracts **only blocking policies** (status: fail)
- Creates **one issue per policy** (not per file)
- **Deduplicates** by checking for existing open issues
- Enriches with metadata from rl-scanner-metadata (labels, descriptions, remediation steps)
- Supports **level filtering** to only include policies at or above a specified rl-level

---

## Filtering Logic

From 100+ violations, you might get 3-5 issues:

| Violations | Result |
|------------|--------|
| 6 violations with `status=fail` for SQ31102 | 1 issue for SQ31102 |
| 2 violations with `status=fail` for SQ34108 | 1 issue for SQ34108 |
| 50 violations with `status=pass` | 0 issues (not blocking) |

---

## Usage

### Reusable Workflow
```yaml
jobs:
  scan:
    # ... your rl-secure scan job that outputs report.rl.json ...

  create-issues:
    needs: scan
    if: failure()
    uses: reversinglabs-ats/rl-scanner-to-github/.github/workflows/create-issues.yml@main
    with:
      report-path: ./rl-reports/report.rl.json
      max-issues: 10
      level: 5  # optional: only L5 blocking policies
    secrets:
      github-token: ${{ secrets.GITHUB_TOKEN }}
```

#### Workflow Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `report-path` | Yes | — | Path to report.rl.json |
| `metadata-dir` | No | bundled | Path to rl-scanner-metadata |
| `max-issues` | No | 10 | Maximum issues to create |
| `level` | No | — | Only include policies with rl-level ≥ this value (1-5) |

---

### Local Testing (CLI)
```bash
git clone https://github.com/reversinglabs-ats/rl-scanner-to-github.git
cd rl-scanner-to-github
pip install requests
```

**Set credentials:**
```bash
export GITHUB_TOKEN=ghp_...
export GITHUB_REPOSITORY=owner/repo
```

**Run:**
```bash
# Preview what would be created
python src/main.py --report /path/to/report.rl.json --dry-run

# Create issues
python src/main.py --report /path/to/report.rl.json

# With metadata enrichment
python src/main.py --report /path/to/report.rl.json --metadata-dir data/rl-scanner-metadata/data

# Filter to only L5 policies
python src/main.py --report /path/to/report.rl.json --metadata-dir data/rl-scanner-metadata/data --level 5
```

#### CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--report` | required | Path to report.rl.json |
| `--metadata-dir` | — | Path to rl-scanner-metadata/data |
| `--dry-run` | false | Preview without creating issues |
| `--max-issues` | 10 | Safety limit |
| `--level` | — | Only include policies with rl-level ≥ this value (1-5) |
| `--policy-config` | auto-detect | Path to policy config file (.info) |

---

### Policy Config Support

The tool respects repository policy config files (Boost INFO format) to suppress known or accepted violations:

- **Auto-detection:** Looks for `*-policy.info` files in the repo root and `.rl-secure/` directory
- **Manual override:** Use `--policy-config path/to/file.info` in CLI mode
- **What gets suppressed:**
  - Policies disabled in `overrides` blocks
  - Components matching `secrets`, `policies`, or `triaged` filters
  - CVEs marked as triaged (with optional VEX reasons)

Suppressed items are logged in the CLI output under "Filtered by Policy Config" for transparency.

---

#### Environment Variables

| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | Token with `issues:write` permission |
| `GITHUB_REPOSITORY` | Target repo (`owner/repo`) |
