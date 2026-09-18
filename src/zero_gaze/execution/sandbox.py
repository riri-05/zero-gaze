"""Execution sandbox for running baseline replication scripts safely."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class ExecutionResult(BaseModel):
    """Result of running a replication experiment script in the sandbox."""

    model_config = ConfigDict(frozen=True)

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    runtime_seconds: float
    output_metrics: dict[str, float] = Field(default_factory=dict)
    error_message: str | None = None


class SandboxRunner:
    """Manages ephemeral, resource-bounded execution of experiment code."""

    def __init__(
        self,
        timeout_seconds: float = 60.0,
        working_dir: str | Path | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.working_dir = Path(working_dir) if working_dir else None

    @staticmethod
    def parse_metrics_from_stdout(stdout_text: str) -> dict[str, float]:
        """Parse key-value metrics emitted in stdout during execution.

        Looks for standard patterns like:
        Metric (Accuracy): 89.5%
        Metric (BLEU): 28.4
        Metric 'loss': 0.042
        """
        import re

        metrics: dict[str, float] = {}
        patterns = [
            re.compile(r"Metric\s*\(([^)]+)\)\s*:\s*([0-9.]+)", re.IGNORECASE),
            re.compile(r"Metric\s*['\"]([^'\"]+)['\"]\s*:\s*([0-9.]+)", re.IGNORECASE),
            re.compile(r"([a-zA-Z0-9_\-]+)\s*=\s*([0-9.]+)%?", re.IGNORECASE),
        ]
        for line in stdout_text.splitlines():
            for pat in patterns:
                match = pat.search(line)
                if match:
                    name = match.group(1).strip()
                    try:
                        val = float(match.group(2).strip())
                        metrics[name] = val
                    except ValueError:
                        pass
        return metrics

    def execute_script(
        self,
        script_code: str,
        python_executable: str | None = None,
        env_vars: dict[str, str] | None = None,
    ) -> ExecutionResult:
        """Execute Python script in an isolated temporary directory with bounded timeout."""
        py_bin = python_executable or sys.executable
        env = dict(os.environ)
        if env_vars:
            env.update(env_vars)

        with tempfile.TemporaryDirectory(prefix="zero_gaze_sandbox_") as tmpdir:
            script_path = Path(tmpdir) / "run_replication.py"
            script_path.write_text(script_code, encoding="utf-8")

            cwd = str(self.working_dir or tmpdir)
            start_time = time.time()

            try:
                proc = subprocess.run(
                    [py_bin, str(script_path)],
                    cwd=cwd,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                )
                elapsed = time.time() - start_time
                stdout = proc.stdout
                stderr = proc.stderr
                metrics = self.parse_metrics_from_stdout(stdout)

                return ExecutionResult(
                    success=(proc.returncode == 0),
                    exit_code=proc.returncode,
                    stdout=stdout,
                    stderr=stderr,
                    runtime_seconds=round(elapsed, 3),
                    output_metrics=metrics,
                    error_message=None if proc.returncode == 0 else f"Process exited with code {proc.returncode}",
                )

            except subprocess.TimeoutExpired as err:
                elapsed = time.time() - start_time
                return ExecutionResult(
                    success=False,
                    exit_code=-1,
                    stdout=err.stdout or "" if isinstance(err.stdout, str) else "",
                    stderr=err.stderr or "" if isinstance(err.stderr, str) else "",
                    runtime_seconds=round(elapsed, 3),
                    error_message=f"Execution timed out after {self.timeout_seconds} seconds.",
                )
            except Exception as err:
                elapsed = time.time() - start_time
                return ExecutionResult(
                    success=False,
                    exit_code=-1,
                    stdout="",
                    stderr=str(err),
                    runtime_seconds=round(elapsed, 3),
                    error_message=str(err),
                )
