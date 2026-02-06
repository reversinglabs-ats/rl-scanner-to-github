"""Test workflow YAML stays in sync with CLI definitions."""

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

WORKFLOW_PATH = Path(__file__).parent.parent / ".github" / "workflows" / "create-issues.yml"
MAIN_PY_PATH = Path(__file__).parent.parent / "src" / "main.py"

WORKFLOW_TO_CLI = {
    "report-path": "--report",
    "metadata-dir": "--metadata-dir",
    "max-issues": "--max-issues",
    "level": "--level",
}


def _load_workflow_inputs() -> dict:
    """Load workflow inputs from YAML."""
    with open(WORKFLOW_PATH, encoding="utf-8") as f:
        wf = yaml.safe_load(f)
    return wf[True]["workflow_call"]["inputs"]


def _load_workflow_run_step() -> str:
    """Load the run: string from the step that calls main.py."""
    with open(WORKFLOW_PATH, encoding="utf-8") as f:
        wf = yaml.safe_load(f)
    for job in wf["jobs"].values():
        for step in job["steps"]:
            run_cmd = step.get("run", "")
            if "main.py" in run_cmd:
                return run_cmd
    raise ValueError("No step calling main.py found in workflow")


def test_workflow_has_required_inputs():
    """YAML defines exactly: report-path, metadata-dir, max-issues, level."""
    inputs = _load_workflow_inputs()
    expected = {"report-path", "metadata-dir", "max-issues", "level"}
    assert set(inputs.keys()) == expected


def test_report_path_is_required():
    """report-path has required: true."""
    inputs = _load_workflow_inputs()
    assert inputs["report-path"]["required"] is True


def test_max_issues_default_matches():
    """Workflow default is 10; main.py source contains default=10."""
    inputs = _load_workflow_inputs()
    assert inputs["max-issues"]["default"] == 10

    main_src = MAIN_PY_PATH.read_text(encoding="utf-8")
    assert "default=10" in main_src


def test_workflow_inputs_map_to_cli_args():
    """Run step contains each CLI flag and inputs.<name> reference."""
    run_step = _load_workflow_run_step()
    for input_name, cli_flag in WORKFLOW_TO_CLI.items():
        assert cli_flag in run_step, f"CLI flag {cli_flag} not found in run step"
        assert f"inputs.{input_name}" in run_step, f"inputs.{input_name} not referenced in run step"


def test_level_type_is_number():
    """level input has type: number."""
    inputs = _load_workflow_inputs()
    assert inputs["level"]["type"] == "number"


def test_workflow_step_passes_all_inputs():
    """Run step references every defined input."""
    inputs = _load_workflow_inputs()
    run_step = _load_workflow_run_step()
    for input_name in inputs:
        assert f"inputs.{input_name}" in run_step, f"Input '{input_name}' not passed in run step"
