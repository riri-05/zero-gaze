"""Unit tests for LangGraph state machine, nodes, and runner."""

from unittest.mock import MagicMock
import pytest
from langgraph.graph import END
from zero_gaze.core.models.claims import ClaimItem, ClaimsList
from zero_gaze.core.models.discovery import CodeResource, RepoStatus
from zero_gaze.core.models.paper import PaperArtifact, PaperExtractionSource
from zero_gaze.core.models.plan import ReplicationPlan
from zero_gaze.core.models.state import AgentState, HumanApproval, HumanDecision
from zero_gaze.graph.nodes import NodeFactory
from zero_gaze.graph.runner import ZeroGazeRunner
from zero_gaze.graph.workflow import build_zero_gaze_graph, route_after_approval


@pytest.fixture
def sample_paper() -> PaperArtifact:
    return PaperArtifact(
        paper_id="2106.09685",
        title="LoRA: Low-Rank Adaptation of Large Language Models",
        authors=["Edward J. Hu"],
        abstract="Hypothesis of low-rank adaptation.",
        pdf_url="https://arxiv.org/pdf/2106.09685.pdf",
        full_text_markdown="# LoRA",
        extraction_source=PaperExtractionSource.PYMUPDF_MARKDOWN,
    )


@pytest.fixture
def mock_node_factory(sample_paper: PaperArtifact) -> NodeFactory:
    mock_ingest = MagicMock()
    mock_ingest.ingest.return_value = sample_paper

    mock_discovery = MagicMock()
    mock_discovery.discover.return_value = CodeResource(
        status=RepoStatus.OFFICIAL,
        repo_url="https://github.com/microsoft/LoRA",
        stars=13800,
    )

    mock_extractor = MagicMock()
    mock_extractor.extract_claims.return_value = ClaimsList(
        paper_title="LoRA",
        claims=[
            ClaimItem(
                benchmark_name="GLUE",
                target_metric="Acc",
                paper_value=90.2,
                baseline_algorithm="RoBERTa",
            )
        ],
    )

    mock_planner = MagicMock()
    mock_planner.plan_replication.return_value = ReplicationPlan(
        target_hardware="cpu",
        estimated_runtime_minutes=5,
        execution_command="python run.py",
        dependencies=["torch"],
        baseline_script="print('baseline')",
    )

    return NodeFactory(
        ingestion_engine=mock_ingest,
        discovery_engine=mock_discovery,
        claim_extractor=mock_extractor,
        replication_planner=mock_planner,
    )


def test_node_factory_fetch_paper_success(mock_node_factory: NodeFactory) -> None:
    state = AgentState(paper_target="2106.09685")
    res = mock_node_factory.fetch_paper_node(state)
    assert "paper" in res
    assert res["paper"].paper_id == "2106.09685"


def test_node_factory_fetch_paper_handles_error() -> None:
    mock_ingest = MagicMock()
    mock_ingest.ingest.side_effect = RuntimeError("Network down")
    factory = NodeFactory(ingestion_engine=mock_ingest)

    state = AgentState(paper_target="invalid")
    res = factory.fetch_paper_node(state)
    assert "errors" in res
    assert "Network down" in res["errors"][0]


def test_node_factory_extract_claims_missing_paper() -> None:
    factory = NodeFactory()
    state = AgentState(paper_target="test", paper=None)
    res = factory.extract_claims_node(state)
    assert "errors" in res
    assert "paper artifact missing" in res["errors"][0]


def test_node_factory_find_code_dataset_success(
    mock_node_factory: NodeFactory, sample_paper: PaperArtifact
) -> None:
    state = AgentState(paper_target="2106.09685", paper=sample_paper)
    res = mock_node_factory.find_code_dataset_node(state)
    assert "code_resource" in res
    assert res["code_resource"].status == RepoStatus.OFFICIAL


def test_node_factory_plan_baseline_success(
    mock_node_factory: NodeFactory, sample_paper: PaperArtifact
) -> None:
    state = AgentState(paper_target="2106.09685", paper=sample_paper)
    res = mock_node_factory.plan_baseline_node(state)
    assert "plan" in res
    assert res["plan"].execution_command == "python run.py"


def test_node_factory_write_report(sample_paper: PaperArtifact) -> None:
    factory = NodeFactory()
    state = AgentState(
        paper_target="2106.09685",
        paper=sample_paper,
        claims=[
            ClaimItem(
                benchmark_name="GLUE",
                target_metric="Acc",
                paper_value=90.2,
                baseline_algorithm="RoBERTa",
            )
        ],
        code_resource=CodeResource(status=RepoStatus.OFFICIAL, repo_url="https://github.com/lora"),
        plan=ReplicationPlan(
            target_hardware="cpu",
            execution_command="pytest",
            baseline_script="",
        ),
        approval=HumanApproval(decision=HumanDecision.APPROVED),
    )
    res = factory.write_report_node(state)
    assert "report" in res
    report = res["report"]
    assert report.verdict == "approved_for_replication"
    assert "GLUE" in report.summary_markdown
    assert "Execution was not attempted." in report.summary_markdown
    assert "GLUE" in report.metric_deltas


def test_route_after_approval() -> None:
    approved_state = AgentState(
        paper_target="test",
        approval=HumanApproval(decision=HumanDecision.APPROVED),
    )
    assert route_after_approval(approved_state) == "execute_baseline"

    revised_state = AgentState(
        paper_target="test",
        approval=HumanApproval(decision=HumanDecision.REVISED),
    )
    assert route_after_approval(revised_state) == "execute_baseline"

    aborted_state = AgentState(
        paper_target="test",
        approval=HumanApproval(decision=HumanDecision.ABORTED),
    )
    assert route_after_approval(aborted_state) == END


def test_runner_full_lifecycle(mock_node_factory: NodeFactory) -> None:
    graph = build_zero_gaze_graph(node_factory=mock_node_factory)
    runner = ZeroGazeRunner(graph=graph)

    # 1. Start execution -> should pause at human_approval
    state, tid, interrupted = runner.start_replication(
        paper_target="2106.09685",
        thread_id="test-thread-full",
    )
    assert interrupted is True
    assert state["paper"].title == "LoRA: Low-Rank Adaptation of Large Language Models"
    assert len(state["claims"]) == 1
    assert state["code_resource"].status == RepoStatus.OFFICIAL
    assert state["plan"].execution_command == "python run.py"

    # 2. Check get_state
    snap = runner.get_state(tid)
    assert snap["paper"].paper_id == "2106.09685"

    # 3. Resume with APPROVAL
    final_state = runner.resolve_approval(
        thread_id=tid,
        decision=HumanDecision.APPROVED,
        comments="Looks great",
    )
    assert final_state["approval"].decision == HumanDecision.APPROVED
    assert final_state["report"].verdict == "approved_for_replication"


def test_runner_abort_lifecycle(mock_node_factory: NodeFactory) -> None:
    graph = build_zero_gaze_graph(node_factory=mock_node_factory)
    runner = ZeroGazeRunner(graph=graph)

    state, tid, interrupted = runner.start_replication(
        paper_target="2106.09685",
        thread_id="test-thread-abort",
    )
    assert interrupted is True

    aborted_state = runner.resolve_approval(
        thread_id=tid,
        decision=HumanDecision.ABORTED,
        comments="Aborting run",
    )
    assert aborted_state["approval"].decision == HumanDecision.ABORTED
    assert aborted_state.get("report") is None
