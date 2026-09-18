"""Artifact discovery and repository domain models."""

from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class RepoStatus(str, Enum):
    """Categorization of code implementation origin."""

    OFFICIAL = "official"
    COMMUNITY = "community"
    SYNTHETIC_STUB = "synthetic_stub"
    UNAVAILABLE = "unavailable"


class CodeResource(BaseModel):
    """Discovered code repository, benchmark dataset, or synthetic baseline."""

    model_config = ConfigDict(frozen=True)

    status: RepoStatus
    repo_url: str | None = None
    commit_sha: str | None = None
    primary_language: str = "python"
    entry_point_script: str | None = None
    dataset_name: str | None = None
    dataset_download_url: str | None = None
    huggingface_model_id: str | None = None
    stars: int = Field(default=0, ge=0)
    license: str | None = None
    generated_baseline_code: str | None = None
