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
    def get_sanitized_environment(extra_env: dict[str, str] | None = None) -> dict[str, str]:
        """Construct an isolated environment whitelist, stripping host secrets."""
        allowed_keys = {
            "PATH", "VIRTUAL_ENV", "LANG", "LC_ALL", "TMPDIR", "TEMP", "TMP",
            "PYTHONPATH", "PYTHONIOENCODING", "HOME", "USER", "LD_LIBRARY_PATH",
            "CUDA_VISIBLE_DEVICES", "TORCH_CUDA_ARCH_LIST",
        }
        safe_env = {k: v for k, v in os.environ.items() if k in allowed_keys}
        secret_indicators = (
            "KEY", "SECRET", "TOKEN", "PASSWORD", "AUTH", "CREDENTIAL",
            "OPENROUTER", "OPENAI", "ANTHROPIC", "AWS_", "GCP_",
        )
        for k in list(safe_env.keys()):
            if any(ind in k.upper() for ind in secret_indicators):
                safe_env.pop(k, None)

        if extra_env:
            safe_env.update(extra_env)
        return safe_env

    @staticmethod
    def parse_metrics_from_stdout(stdout_text: str) -> dict[str, float]:
        """Parse key-value metrics emitted in stdout during execution.

        Filters out loop counters and hyperparameter assignments like epoch=1 or step=10.
        """
        import re

        metrics: dict[str, float] = {}
        ignored_variables = {
            "epoch", "step", "iter", "iteration", "batch", "batch_size",
            "lr", "learning_rate", "seed", "rank", "device", "workers",
            "num_workers", "layers", "heads", "hidden_size", "i", "j", "k", "n",
        }
        patterns = [
            re.compile(r"Metric\s*\(([^)]+)\)\s*:\s*([0-9.]+)", re.IGNORECASE),
            re.compile(r"Metric\s*['\"]([^'\"]+)['\"]\s*:\s*([0-9.]+)", re.IGNORECASE),
            re.compile(r"([a-zA-Z0-9_\-]+)\s*=\s*([0-9.]+)%?", re.IGNORECASE),
        ]
        for line in stdout_text.splitlines():
            for idx, pat in enumerate(patterns):
                match = pat.search(line)
                if match:
                    name = match.group(1).strip()
                    if idx == 2 and name.lower() in ignored_variables:
                        continue
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
        on_stdout_chunk: Any = None,
    ) -> ExecutionResult:
        """Execute Python script in an isolated temporary directory with bounded timeout and process group containment."""
        import signal
        py_bin = python_executable or sys.executable
        env = self.get_sanitized_environment(env_vars)

        with tempfile.TemporaryDirectory(prefix="zero_gaze_sandbox_") as tmpdir:
            script_path = Path(tmpdir) / "run_replication.py"
            script_path.write_text(script_code, encoding="utf-8")

            cwd = str(self.working_dir or tmpdir)
            start_time = time.time()

            try:
                proc = subprocess.Popen(
                    [py_bin, str(script_path)],
                    cwd=cwd,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    start_new_session=True,
                )

                try:
                    stdout, stderr = proc.communicate(timeout=self.timeout_seconds)
                except subprocess.TimeoutExpired:
                    try:
                        pgid = os.getpgid(proc.pid)
                        os.killpg(pgid, signal.SIGTERM)
                        time.sleep(0.1)
                        os.killpg(pgid, signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        pass
                    proc.kill()
                    out, err = proc.communicate()
                    elapsed = time.time() - start_time
                    return ExecutionResult(
                        success=False,
                        exit_code=-1,
                        stdout=out or "",
                        stderr=err or "",
                        runtime_seconds=round(elapsed, 3),
                        error_message=f"Execution timed out after {self.timeout_seconds} seconds.",
                    )

                elapsed = time.time() - start_time
                if on_stdout_chunk and stdout:
                    for line in stdout.splitlines(keepends=True):
                        on_stdout_chunk(line)

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
