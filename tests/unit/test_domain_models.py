"""Unit tests for Zero Gaze core domain contracts and models."""

import pytest
from pydantic import ValidationError
from zero_gaze.core.errors import (
    DiscoveryError,
    ExtractionError,
    GraphExecutionError,
    IngestionError,
    ZeroGazeError,
)
from zero_gaze.core.models import (
    AgentState,
    ClaimItem,
    ClaimsList,
    CodeResource,
    HumanApproval,
    HumanDecision,
    PaperArtifact,
    PaperExtractionSource,
    ReplicationPlan,
    ReplicationReport,
    RepoStatus,
)


def test_paper_artifact_valid_instantiation() -> None:
    paper = PaperArtifact(
        paper_id="2106.09685",
        title="LoRA: Low-Rank Adaptation of Large Language Models",
        authors=["Edward J. Hu", "Yelong Shen"],
        published_date="2021-06-17",
        abstract="Low-rank adaptation hypothesis.",
        pdf_url="https://arxiv.org/pdf/2106.09685.pdf",
        full_text_markdown="# LoRA",
        extraction_source=PaperExtractionSource.PYMUPDF_MARKDOWN,
        section_headers=["Intro", "Method"],
        tables=[{"id": 1, "score": 88.5}],
    )
    assert paper.paper_id == "2106.09685"
    assert paper.title == "LoRA: Low-Rank Adaptation of Large Language Models"
    assert paper.extraction_source == PaperExtractionSource.PYMUPDF_MARKDOWN
    assert len(paper.authors) == 2


def test_paper_artifact_immutability() -> None:
    paper = PaperArtifact(
        paper_id="1234.5678",
        title="Immutable Paper",
        abstract="Abstract content",
        pdf_url="https://arxiv.org/pdf/1234.5678.pdf",
        full_text_markdown="Text",
    )
    with pytest.raises(ValidationError):
        paper.title = "Modified Title"  # type: ignore[misc]


def test_code_resource_defaults_and_validation() -> None:
    code = CodeResource(
        status=RepoStatus.OFFICIAL,
        repo_url="https://github.com/microsoft/LoRA",
        stars=5000,
    )
    assert code.primary_language == "python"
    assert code.status == RepoStatus.OFFICIAL
    assert code.stars == 5000


def test_code_resource_rejects_negative_stars() -> None:
    with pytest.raises(ValidationError):
        CodeResource(status=RepoStatus.COMMUNITY, stars=-1)


def test_claims_list_and_claim_item() -> None:
    claim = ClaimItem(
        benchmark_name="GLUE",
        target_metric="F1",
        paper_value=89.4,
        baseline_algorithm="BERT-Base",
        hyperparameters={"lr": 0.001, "batch_size": 32},
    )
    claims_list = ClaimsList(paper_title="Paper Title", claims=[claim])
    assert len(claims_list.claims) == 1
    assert claims_list.claims[0].paper_value == 89.4
    assert claims_list.claims[0].hyperparameters["lr"] == 0.001


def test_replication_plan_validation() -> None:
    plan = ReplicationPlan(
        target_hardware="gpu_t4",
        estimated_runtime_minutes=12,
        execution_command="pytest",
        baseline_script="print('hello')",
    )
    assert plan.estimated_runtime_minutes == 12

    with pytest.raises(ValidationError):
        ReplicationPlan(
            target_hardware="cpu",
            estimated_runtime_minutes=0,
            execution_command="pytest",
            baseline_script="",
        )


def test_replication_report() -> None:
    report = ReplicationReport(
        verdict="replicated",
        summary_markdown="## Success",
        metric_deltas={"f1": {"expected": 89.4, "actual": 89.1}},
    )
    assert report.verdict == "replicated"
    assert "Success" in report.summary_markdown


def test_human_approval_and_decision_enum() -> None:
    approval = HumanApproval(decision=HumanDecision.REVISED, reviewer_comments="Increase epochs")
    assert approval.decision == HumanDecision.REVISED
    assert approval.reviewer_comments == "Increase epochs"


def test_agent_state_roundtrip_serialization() -> None:
    paper = PaperArtifact(
        paper_id="2106.09685",
        title="LoRA",
        abstract="Summary",
        pdf_url="https://arxiv.org/pdf/2106.09685.pdf",
        full_text_markdown="# LoRA",
    )
    state = AgentState(
        paper_target="2106.09685",
        paper=paper,
        claims=[
            ClaimItem(
                benchmark_name="GLUE",
                target_metric="Acc",
                paper_value=90.0,
                baseline_algorithm="LoRA",
            )
        ],
        code_resource=CodeResource(status=RepoStatus.SYNTHETIC_STUB),
        approval=HumanApproval(decision=HumanDecision.APPROVED),
    )
    raw_json = state.model_dump_json()
    reconstructed = AgentState.model_validate_json(raw_json)

    assert reconstructed.paper_target == "2106.09685"
    assert reconstructed.paper is not None
    assert reconstructed.paper.title == "LoRA"
    assert reconstructed.approval.decision == HumanDecision.APPROVED
    assert reconstructed.code_resource is not None
    assert reconstructed.code_resource.status == RepoStatus.SYNTHETIC_STUB


def test_agent_state_error_accumulation() -> None:
    state = AgentState(paper_target="2106.09685", errors=["Initial error"])
    assert state.errors == ["Initial error"]


def test_domain_errors_hierarchy() -> None:
    err = IngestionError("PDF download timeout", details={"status_code": 408})
    assert isinstance(err, ZeroGazeError)
    assert err.message == "PDF download timeout"
    assert err.details["status_code"] == 408

    assert issubclass(DiscoveryError, ZeroGazeError)
    assert issubclass(ExtractionError, ZeroGazeError)
    assert issubclass(GraphExecutionError, ZeroGazeError)
