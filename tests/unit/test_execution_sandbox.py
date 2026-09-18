"""Unit tests for experiment execution sandbox."""

import pytest
from pydantic import ValidationError
from zero_gaze.execution import ExecutionResult, SandboxRunner


def test_sandbox_executes_valid_script() -> None:
    sandbox = SandboxRunner(timeout_seconds=5.0)
    code = 'print("Hello from sandbox")'
    result = sandbox.execute_script(code)

    assert result.success is True
    assert result.exit_code == 0
    assert "Hello from sandbox" in result.stdout
    assert result.error_message is None
    assert result.runtime_seconds >= 0.0


def test_sandbox_captures_stdout_metrics() -> None:
    sandbox = SandboxRunner(timeout_seconds=5.0)
    code = """
print("Starting evaluation...")
print("Metric (Accuracy): 94.2%")
print("Metric 'Loss': 0.015")
print("F1 = 91.8")
"""
    result = sandbox.execute_script(code)

    assert result.success is True
    assert result.output_metrics["Accuracy"] == 94.2
    assert result.output_metrics["Loss"] == 0.015
    assert result.output_metrics["F1"] == 91.8


def test_sandbox_handles_script_runtime_error() -> None:
    sandbox = SandboxRunner(timeout_seconds=5.0)
    code = 'raise RuntimeError("Deliberate error")'
    result = sandbox.execute_script(code)

    assert result.success is False
    assert result.exit_code != 0
    assert "Deliberate error" in result.stderr
    assert result.error_message is not None


def test_sandbox_enforces_timeout() -> None:
    sandbox = SandboxRunner(timeout_seconds=0.3)
    code = """
import time
time.sleep(5)
"""
    result = sandbox.execute_script(code)

    assert result.success is False
    assert result.exit_code == -1
    assert "timed out" in (result.error_message or "")


def test_execution_result_immutability() -> None:
    res = ExecutionResult(
        success=True,
        exit_code=0,
        stdout="done",
        stderr="",
        runtime_seconds=1.0,
    )
    with pytest.raises(ValidationError):
        res.success = False  # type: ignore[misc]
