"""Replication plan and execution report domain models."""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ReplicationPlan(BaseModel):
    """Specification of experiment execution scope and commands."""

    model_config = ConfigDict(frozen=True)

    target_hardware: str = "cpu"
    estimated_runtime_minutes: int = Field(default=10, ge=1)
    execution_command: str
    dependencies: list[str] = Field(default_factory=list)
    dataset_preparation_steps: list[str] = Field(default_factory=list)
    baseline_script: str


class ReplicationReport(BaseModel):
    """Final summary verdict and metric comparison report."""

    model_config = ConfigDict(frozen=True)

    verdict: str
    summary_markdown: str
    metric_deltas: dict[str, Any] = Field(default_factory=dict)
    generated_at: str | None = None
