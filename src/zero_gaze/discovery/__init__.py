"""Artifact discovery module for repositories, models, and datasets."""

from zero_gaze.discovery.clients import (
    GitHubDiscoveryClient,
    HuggingFaceDiscoveryClient,
    PapersWithCodeClient,
)
from zero_gaze.discovery.engine import ArtifactDiscoveryEngine
from zero_gaze.discovery.synthetic_stub import SyntheticStubGenerator

__all__ = [
    "ArtifactDiscoveryEngine",
    "GitHubDiscoveryClient",
    "HuggingFaceDiscoveryClient",
    "PapersWithCodeClient",
    "SyntheticStubGenerator",
]
