"""Empirical claims and benchmark target models."""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class ClaimItem(BaseModel):
    """An empirical benchmark result or quantitative performance claim."""

    model_config = ConfigDict(frozen=True)

    benchmark_name: str
    target_metric: str
    paper_value: float
    baseline_algorithm: str
    hyperparameters: dict[str, Any] = Field(default_factory=dict)


class ClaimsList(BaseModel):
    """Structured extraction payload containing paper claims."""

    model_config = ConfigDict(frozen=True)

    paper_title: str | None = None
    claims: list[ClaimItem] = Field(default_factory=list)
    summary: str = ""
