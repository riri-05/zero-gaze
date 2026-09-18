"""Core domain contracts, state definitions, and exceptions."""

from zero_gaze.core.errors import (
    DiscoveryError,
    ExtractionError,
    GraphExecutionError,
    IngestionError,
    ZeroGazeError,
)
from zero_gaze.core.models.claims import ClaimItem, ClaimsList
from zero_gaze.core.models.discovery import CodeResource, RepoStatus
from zero_gaze.core.models.paper import PaperArtifact, PaperExtractionSource
from zero_gaze.core.models.plan import ReplicationPlan, ReplicationReport
from zero_gaze.core.models.state import AgentState, HumanApproval, HumanDecision

__all__ = [
    "AgentState",
    "ClaimItem",
    "ClaimsList",
    "CodeResource",
    "DiscoveryError",
    "ExtractionError",
    "GraphExecutionError",
    "HumanApproval",
    "HumanDecision",
    "IngestionError",
    "PaperArtifact",
    "PaperExtractionSource",
    "ReplicationPlan",
    "ReplicationReport",
    "RepoStatus",
    "ZeroGazeError",
]
