# rl-scanner-to-github

Create GitHub Issues from ReversingLabs Spectra Assure scan results.

---

## Example Issue

<img width="945" height="912" alt="exampleissuemade" src="https://github.com/user-attachments/assets/c6eb6127-049b-498b-b63d-25fb6e2cb6e2" />

---

## Disclaimer of Warranty

This application is provided "as is" and "as available" without any warranties of any kind, either express or implied.

Reversing Labs make no representations or warranties of any kind, including but not limited to:

- The accuracy, completeness, or timeliness of the information submitted or received via this application;
- The functionality, availability, or performance of the application;
- The security, integrity, or confidentiality of submitted files or user data; or
- The fitness of this application for any particular purpose.

Use of this application is at your own risk. By using this application, you acknowledge that any data submitted to third-party services (e.g., ReversingLabs Spectra Analyze) may be subject to their own terms and conditions.

In no event shall the developer be liable for any direct, indirect, incidental, special, exemplary, or consequential damages arising out of or in any way connected with the use or misuse of this application.

## What It Does

- Parses `rl-json` reports from Spectra Assure scans
- Extracts **only blocking policies** (status: fail)
- Creates **one issue per policy** (not per file)
- **Deduplicates** by checking for existing open issues
- Enriches with metadata from rl-scanner-metadata (labels, descriptions, remediation steps)
- Supports **level filtering** to only include policies at or above a specified rl-level
- Optionally links each issue to the **full SAFE report** for download

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
    uses: reversinglabs-ats/rl-scanner-to-github/.github/workflows/create-issues.yml@v1
    with:
      report-path: ./rl-reports/report.rl.json
      max-issues: 10
      level: 5  # optional: only L5 blocking policies
      report-url: https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}
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
| `report-url` | No | — | URL to the full SAFE report (e.g. GitHub Actions run URL). Adds a download link to each issue. |

---

### SAFE Report Link

When `report-url` is provided, each issue includes a link at the top of the body:

> 📊 [Download full SAFE report](https://github.com/org/repo/actions/runs/12345678)
> _Download the artifact, unzip, and open `rl-html/sdlc.html`_

To use this feature:

1. Add `--format=rl-json,rl-html` to your `rl-secure report` command so the SAFE report is generated alongside the rl-json report
2. Upload the report directory as a workflow artifact
3. Pass `report-url` pointing to the Actions run: `https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}`

The link takes users to the Actions run page where they can download the artifact containing the interactive SAFE report.

This feature is **off by default**. Omitting `report-url` produces issues identical to previous versions.

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

# With SAFE report link
python src/main.py --report /path/to/report.rl.json --report-url "https://github.com/org/repo/actions/runs/12345"
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
| `--report-url` | — | URL to full SAFE report. Adds a download link to each issue. |

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
