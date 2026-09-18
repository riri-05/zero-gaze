"""LangGraph state schema and human decision models."""

from enum import Enum
import operator
from typing import Annotated, Any
from pydantic import BaseModel, ConfigDict, Field
from zero_gaze.core.models.claims import ClaimItem
from zero_gaze.core.models.discovery import CodeResource
from zero_gaze.core.models.paper import PaperArtifact
from zero_gaze.core.models.plan import ReplicationPlan, ReplicationReport


class HumanDecision(str, Enum):
    """Enumeration of human operator decisions at the interrupt gate."""

    PENDING = "pending"
    APPROVED = "approved"
    REVISED = "revised"
    ABORTED = "aborted"


class HumanApproval(BaseModel):
    """Container for human operator review verdict and feedback."""

    model_config = ConfigDict(frozen=True)

    decision: HumanDecision = HumanDecision.PENDING
    reviewer_comments: str | None = None
    config_overrides: dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    """Central typed state container passed through LangGraph nodes."""

    paper_target: str
    paper: PaperArtifact | None = None
    claims: list[ClaimItem] = Field(default_factory=list)
    code_resource: CodeResource | None = None
    plan: ReplicationPlan | None = None
    approval: HumanApproval = Field(default_factory=HumanApproval)
    report: ReplicationReport | None = None
    errors: Annotated[list[str], operator.add] = Field(default_factory=list)
