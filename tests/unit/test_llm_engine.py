"""Unit tests for LLM engine, model gateway, and structured extractors."""

from unittest.mock import MagicMock, patch
import pytest
from pydantic import BaseModel
from zero_gaze.core.errors import ExtractionError
from zero_gaze.core.models.claims import ClaimItem, ClaimsList
from zero_gaze.core.models.discovery import CodeResource, RepoStatus
from zero_gaze.core.models.paper import PaperArtifact, PaperExtractionSource
from zero_gaze.core.models.plan import ReplicationPlan
from zero_gaze.llm.budget import TokenBudgeter
from zero_gaze.llm.extractor import ClaimExtractor, ReplicationPlanner
from zero_gaze.llm.gateway import ModelGateway


class DummySchema(BaseModel):
    value: str


def test_token_budgeter_strip_bibliography() -> None:
    text = (
        "# Introduction\n\nContent here.\n\n"
        + ("Long paragraph text describing empirical evaluation.\n\n" * 30)
        + "# References\n\n[1] Smith et al. 2020."
    )
    stripped = TokenBudgeter.strip_bibliography(text)
    assert "# References" not in stripped
    assert "[1] Smith" not in stripped
    assert "# Introduction" in stripped


def test_token_budgeter_respects_max_characters() -> None:
    long_text = "This is a sentence inside a long paragraph.\n\n" * 500
    budgeted = TokenBudgeter.budget_paper_text(long_text, max_characters=1000)
    assert len(budgeted) <= 1200
    assert "truncated to fit model context budget" in budgeted


def test_model_gateway_initialization() -> None:
    gateway = ModelGateway(
        api_key="test-api-key",
        base_url="https://openrouter.ai/api/v1",
        models_cascade=["model-a", "model-b"],
    )
    assert gateway.api_key == "test-api-key"
    assert gateway.models_cascade == ["model-a", "model-b"]


def test_model_gateway_missing_api_key_raises() -> None:
    with patch.dict("os.environ", {}, clear=True), patch("zero_gaze.llm.gateway.load_env_file", return_value={}):
        with pytest.raises(ExtractionError) as exc_info:
            ModelGateway(api_key=None)
        assert "OPENROUTER_API_KEY is required" in str(exc_info.value)


def test_model_gateway_invoke_structured_success() -> None:
    gateway = ModelGateway(api_key="test-key", models_cascade=["model-primary"])
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_structured.invoke.return_value = DummySchema(value="extracted_ok")
    mock_llm.with_structured_output.return_value = mock_structured

    with patch.object(gateway, "get_chat_model", return_value=mock_llm):
        result = gateway.invoke_structured(DummySchema, prompt="test prompt")
        assert result.value == "extracted_ok"


def test_model_gateway_cascades_on_primary_failure() -> None:
    gateway = ModelGateway(
        api_key="test-key",
        models_cascade=["model-primary", "model-fallback"],
        max_retries_per_model=1,
    )

    mock_fail_llm = MagicMock()
    mock_fail_struct = MagicMock()
    mock_fail_struct.invoke.side_effect = RuntimeError("429 Rate Limit Exceeded")
    mock_fail_llm.with_structured_output.return_value = mock_fail_struct

    mock_ok_llm = MagicMock()
    mock_ok_struct = MagicMock()
    mock_ok_struct.invoke.return_value = DummySchema(value="fallback_success")
    mock_ok_llm.with_structured_output.return_value = mock_ok_struct

    def mock_get_chat(model_name: str, **kwargs):
        if model_name == "model-primary":
            return mock_fail_llm
        return mock_ok_llm

    with patch.object(gateway, "get_chat_model", side_effect=mock_get_chat):
        result = gateway.invoke_structured(DummySchema, prompt="test prompt")
        assert result.value == "fallback_success"


def test_model_gateway_all_models_fail_raises() -> None:
    gateway = ModelGateway(
        api_key="test-key",
        models_cascade=["model-1", "model-2"],
        max_retries_per_model=1,
    )
    mock_fail_llm = MagicMock()
    mock_fail_struct = MagicMock()
    mock_fail_struct.invoke.side_effect = RuntimeError("Gateway Timeout")
    mock_fail_llm.with_structured_output.return_value = mock_fail_struct

    with patch.object(gateway, "get_chat_model", return_value=mock_fail_llm):
        with pytest.raises(ExtractionError) as exc_info:
            gateway.invoke_structured(DummySchema, prompt="test")
        assert "All models in cascade failed" in str(exc_info.value)


def test_claim_extractor_invokes_gateway() -> None:
    mock_gateway = MagicMock()
    expected_claims = ClaimsList(
        paper_title="LoRA Paper",
        claims=[
            ClaimItem(
                benchmark_name="MNLI",
                target_metric="Accuracy",
                paper_value=90.2,
                baseline_algorithm="RoBERTa",
            )
        ],
    )
    mock_gateway.invoke_structured.return_value = expected_claims

    extractor = ClaimExtractor(gateway=mock_gateway)
    res = extractor.extract_claims(paper_markdown="Some text", paper_title="LoRA Paper")
    assert res.paper_title == "LoRA Paper"
    assert len(res.claims) == 1
    assert res.claims[0].paper_value == 90.2


def test_replication_planner_plan_synthesis() -> None:
    mock_gateway = MagicMock()
    expected_plan = ReplicationPlan(
        target_hardware="gpu_t4",
        estimated_runtime_minutes=8,
        execution_command="python run.py",
        dependencies=["torch"],
        baseline_script="print('baseline code script for experiment execution')",
    )
    mock_gateway.invoke_structured.return_value = expected_plan

    planner = ReplicationPlanner(gateway=mock_gateway)
    paper = PaperArtifact(
        paper_id="2106.09685",
        title="LoRA",
        abstract="Abstract",
        pdf_url="https://arxiv.org/pdf/2106.09685.pdf",
        full_text_markdown="# LoRA",
        extraction_source=PaperExtractionSource.PYMUPDF_MARKDOWN,
    )
    plan = planner.plan_replication(
        paper=paper,
        claims=[ClaimItem(benchmark_name="GLUE", target_metric="Acc", paper_value=90.0, baseline_algorithm="Algo")],
        target_hardware="gpu_t4",
    )
    assert plan.target_hardware == "gpu_t4"
    assert plan.estimated_runtime_minutes == 8
    assert "baseline code" in plan.baseline_script


def test_replication_planner_enriches_short_script() -> None:
    mock_gateway = MagicMock()
    short_plan = ReplicationPlan(
        target_hardware="cpu",
        estimated_runtime_minutes=5,
        execution_command="python run.py",
        dependencies=["torch"],
        baseline_script="run",
    )
    mock_gateway.invoke_structured.return_value = short_plan

    code_res = CodeResource(
        status=RepoStatus.SYNTHETIC_STUB,
        generated_baseline_code="def run(): pass  # complete synthetic stub",
    )
    paper = PaperArtifact(
        paper_id="2106.09685",
        title="LoRA",
        abstract="Abstract",
        pdf_url="https://arxiv.org/pdf/2106.09685.pdf",
        full_text_markdown="# LoRA",
    )

    planner = ReplicationPlanner(gateway=mock_gateway)
    plan = planner.plan_replication(paper=paper, claims=[], code_resource=code_res)
    assert plan.baseline_script == "def run(): pass  # complete synthetic stub"
