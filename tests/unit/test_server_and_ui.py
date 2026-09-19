"""Unit tests for FastAPI server, AG-UI SSE protocol, and CLI entry points."""

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pytest
from zero_gaze.cli import main
from zero_gaze.core.models.claims import ClaimItem
from zero_gaze.core.models.discovery import CodeResource, RepoStatus
from zero_gaze.core.models.paper import PaperArtifact, PaperExtractionSource
from zero_gaze.core.models.plan import ReplicationPlan
from zero_gaze.core.models.state import HumanApproval, HumanDecision
from zero_gaze.execution.sandbox import ExecutionResult
from zero_gaze.graph import NodeFactory, build_zero_gaze_graph
from zero_gaze.graph.runner import ZeroGazeRunner
from zero_gaze.server.app import create_app
import zero_gaze.server.routes as server_routes
from zero_gaze.server.sse import (
    format_agent_error,
    format_agent_finish,
    format_agent_start,
    format_interrupt_requested,
    format_interrupt_resolved,
    format_state_delta,
    format_state_snapshot,
)


@pytest.fixture
def mock_runner() -> ZeroGazeRunner:
    mock_factory = MagicMock(spec=NodeFactory)
    mock_paper = PaperArtifact(
        paper_id="2106.09685",
        title="LoRA",
        authors=["Author"],
        abstract="Abstract",
        pdf_url="https://arxiv.org/pdf/2106.09685.pdf",
        full_text_markdown="# LoRA",
        extraction_source=PaperExtractionSource.PYMUPDF_MARKDOWN,
    )
    mock_factory.fetch_paper_node.return_value = {"paper": mock_paper}
    mock_factory.extract_claims_node.return_value = {
        "claims": [ClaimItem(benchmark_name="GLUE", target_metric="Acc", paper_value=90.0, baseline_algorithm="LoRA")]
    }
    mock_factory.find_code_dataset_node.return_value = {
        "code_resource": CodeResource(status=RepoStatus.OFFICIAL, repo_url="https://github.com/lora")
    }
    mock_factory.plan_baseline_node.return_value = {
        "plan": ReplicationPlan(target_hardware="cpu", execution_command="pytest", baseline_script="print(1)")
    }
    mock_factory.execute_baseline_node.return_value = {
        "execution_result": ExecutionResult(success=True, exit_code=0, stdout="Mock output", stderr="", runtime_seconds=0.1)
    }
    real_factory = NodeFactory()
    mock_factory.human_approval_node = real_factory.human_approval_node
    mock_factory.write_report_node = real_factory.write_report_node

    graph = build_zero_gaze_graph(node_factory=mock_factory)
    runner = ZeroGazeRunner(graph=graph)
    return runner


@pytest.fixture
def client(mock_runner: ZeroGazeRunner) -> TestClient:
    server_routes.runner = mock_runner
    app = create_app()
    return TestClient(app)


def test_sse_event_formatting() -> None:
    start_event = format_agent_start("t-1", "2106.09685")
    assert "event: agent:start" in start_event
    assert "t-1" in start_event
    assert "AG-UI/1.0" in start_event

    delta_event = format_state_delta("t-1", {"step": 1})
    assert "event: state:delta" in delta_event
    assert '"step": 1' in delta_event

    snapshot_event = format_state_snapshot("t-1", {"val": "ok"})
    assert "event: state:snapshot" in snapshot_event

    interrupt_event = format_interrupt_requested("t-1", prompt="Approve plan")
    assert "event: interrupt:requested" in interrupt_event
    assert "Approve plan" in interrupt_event

    resolved_event = format_interrupt_resolved("t-1", decision="approved")
    assert "event: interrupt:resolved" in resolved_event
    assert "approved" in resolved_event

    finish_event = format_agent_finish("t-1", report={"verdict": "replicated"})
    assert "event: agent:finish" in finish_event
    assert "replicated" in finish_event

    error_event = format_agent_error("t-1", "network timeout")
    assert "event: agent:error" in error_event
    assert "network timeout" in error_event


def test_health_check(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "zero-gaze-agent"


def test_index_dashboard(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Zero Gaze" in resp.text
    assert "AG-UI 1.0 Active" in resp.text


def test_copilotkit_handshake(client: TestClient) -> None:
    resp = client.post("/api/copilotkit", json={"message": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["protocol"] == "AG-UI/1.0"
    assert data["agent"] == "zero_gaze_agent"


def test_start_and_approve_lifecycle(client: TestClient) -> None:
    # 1. Start replication
    resp_start = client.post(
        "/api/replication/start",
        json={"paper_target": "2106.09685", "thread_id": "test-thread-ui"},
    )
    assert resp_start.status_code == 200
    start_data = resp_start.json()
    assert start_data["thread_id"] == "test-thread-ui"
    assert start_data["is_interrupted"] is True
    assert start_data["status"] == "interrupted_awaiting_approval"

    # 2. Get state
    resp_state = client.get("/api/replication/state/test-thread-ui")
    assert resp_state.status_code == 200
    state_data = resp_state.json()
    assert state_data["thread_id"] == "test-thread-ui"

    # 3. Stream SSE
    resp_stream = client.get("/api/replication/stream/test-thread-ui")
    assert resp_stream.status_code == 200
    assert "event: interrupt:requested" in resp_stream.text

    # 4. Approve
    resp_approve = client.post(
        "/api/replication/approve",
        json={"thread_id": "test-thread-ui", "decision": "approved", "comments": "LGTM"},
    )
    assert resp_approve.status_code == 200
    approve_data = resp_approve.json()
    assert approve_data["status"] == "completed"
    assert approve_data["is_interrupted"] is False
    assert approve_data["state"]["report"]["verdict"] == "approved_for_replication"


def test_get_state_not_found(client: TestClient) -> None:
    resp = client.get("/api/replication/state/non-existent-thread-1234")
    assert resp.status_code == 404


def test_cli_argument_parsing() -> None:
    with patch("sys.argv", ["zero-gaze", "serve", "--port", "9000", "--host", "0.0.0.0"]):
        with patch("zero_gaze.cli.uvicorn.run") as mock_uvicorn:
            main()
            mock_uvicorn.assert_called_once_with(
                "zero_gaze.server.app:app", host="0.0.0.0", port=9000, reload=False
            )
