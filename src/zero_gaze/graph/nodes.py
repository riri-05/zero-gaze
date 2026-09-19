"""Node functions for Zero Gaze LangGraph state machine."""

from __future__ import annotations

import datetime
import logging
from typing import Any
from langgraph.types import interrupt
from zero_gaze.core.models.claims import ClaimItem
from zero_gaze.core.models.discovery import CodeResource
from zero_gaze.core.models.paper import PaperArtifact
from zero_gaze.core.models.plan import ReplicationPlan, ReplicationReport
from zero_gaze.core.models.state import AgentState, HumanApproval, HumanDecision
from zero_gaze.discovery.engine import ArtifactDiscoveryEngine
from zero_gaze.ingestion.engine import PaperIngestionEngine
from zero_gaze.llm.coder import IterativeCoder
from zero_gaze.llm.extractor import ClaimExtractor, ReplicationPlanner

logger = logging.getLogger(__name__)


class NodeFactory:
    """Factory creating state graph node callables with injectable dependencies."""

    def __init__(
        self,
        ingestion_engine: PaperIngestionEngine | None = None,
        discovery_engine: ArtifactDiscoveryEngine | None = None,
        claim_extractor: ClaimExtractor | None = None,
        replication_planner: ReplicationPlanner | None = None,
    ) -> None:
        self.ingestion_engine = ingestion_engine or PaperIngestionEngine()
        self.discovery_engine = discovery_engine or ArtifactDiscoveryEngine()
        self.claim_extractor = claim_extractor or ClaimExtractor()
        self.replication_planner = replication_planner or ReplicationPlanner()
        self.iterative_coder = IterativeCoder()

    def fetch_paper_node(self, state: AgentState) -> dict[str, Any]:
        """Ingest paper from arXiv URL or ID and extract structured markdown."""
        logger.info("Executing node: fetch_paper for target '%s'", state.paper_target)
        try:
            artifact = self.ingestion_engine.ingest(state.paper_target)
            return {"paper": artifact}
        except Exception as err:
            logger.error("Failed to fetch paper: %s", err)
            return {"errors": [f"fetch_paper failed: {err}"]}

    def extract_claims_node(self, state: AgentState) -> dict[str, Any]:
        """Extract benchmark claims and published metric numbers in parallel."""
        logger.info("Executing node: extract_claims")
        if not state.paper:
            return {"errors": ["Cannot extract claims: paper artifact missing"]}

        try:
            claims_list = self.claim_extractor.extract_claims(
                paper_markdown=state.paper.full_text_markdown,
                paper_title=state.paper.title,
            )
            return {"claims": claims_list.claims}
        except Exception as err:
            logger.error("Failed to extract claims: %s", err)
            return {"errors": [f"extract_claims failed: {err}"]}

    def find_code_dataset_node(self, state: AgentState) -> dict[str, Any]:
        """Search GitHub, Hugging Face, and PapersWithCode in parallel."""
        logger.info("Executing node: find_code_dataset")
        if not state.paper:
            return {"errors": ["Cannot discover code: paper artifact missing"]}

        try:
            resource = self.discovery_engine.discover(
                paper_id=state.paper.paper_id,
                paper_title=state.paper.title,
            )
            return {"code_resource": resource}
        except Exception as err:
            logger.error("Failed to discover code resource: %s", err)
            return {"errors": [f"find_code_dataset failed: {err}"]}

    def plan_baseline_node(self, state: AgentState) -> dict[str, Any]:
        """Synthesize replication plan joining claims and discovered resources."""
        logger.info("Executing node: plan_baseline")
        if not state.paper:
            return {"errors": ["Cannot plan baseline: paper artifact missing"]}

        try:
            plan = self.replication_planner.plan_replication(
                paper=state.paper,
                claims=state.claims,
                code_resource=state.code_resource,
                target_hardware="cpu",
            )
            return {"plan": plan}
        except Exception as err:
            logger.error("Failed to plan baseline: %s", err)
            return {"errors": [f"plan_baseline failed: {err}"]}

    def human_approval_node(self, state: AgentState) -> dict[str, Any]:
        """Interrupt graph execution to request human operator review."""
        logger.info("Executing node: human_approval (triggering interrupt)")

        plan_data = state.plan.model_dump() if state.plan else {}
        code_data = state.code_resource.model_dump() if state.code_resource else {}

        # Interrupt payload surfaced to the operator or UI
        user_response = interrupt({
            "prompt": "Please review the proposed replication plan and confirm execution.",
            "paper_id": state.paper.paper_id if state.paper else state.paper_target,
            "paper_title": state.paper.title if state.paper else "",
            "plan": plan_data,
            "code_resource": code_data,
        })

        if not isinstance(user_response, dict):
            user_response = {"decision": str(user_response)}

        raw_decision = user_response.get("decision", "approved").lower()
        if raw_decision in ("approved", "approve", "ok", "yes"):
            decision = HumanDecision.APPROVED
        elif raw_decision in ("aborted", "abort", "cancel", "no"):
            decision = HumanDecision.ABORTED
        elif raw_decision in ("revised", "revise"):
            decision = HumanDecision.REVISED
        else:
            decision = HumanDecision.APPROVED

        approval = HumanApproval(
            decision=decision,
            reviewer_comments=user_response.get("comments"),
            config_overrides=user_response.get("overrides", {}),
        )
        return {"approval": approval}

    def execute_baseline_node(self, state: AgentState) -> dict[str, Any]:
        """Execute generated code iteratively with LLM correction."""
        logger.info("Executing node: execute_baseline")
        if state.approval.decision != HumanDecision.APPROVED:
            return {}

        try:
            claims = state.claims
            # For claims List we pass an object, but IterativeCoder needs ClaimsList
            # The extractor returns ClaimsList, but AgentState stores list[ClaimItem].
            # Let's rebuild a ClaimsList for the coder.
            from zero_gaze.core.models.claims import ClaimsList
            claims_list = ClaimsList(claims=claims) if claims else None
            
            paper_ctx = state.paper.markdown_content if state.paper else state.paper_target
            best_code, result = self.iterative_coder.generate_and_refine(claims=claims_list, paper_context=paper_ctx)
            
            if state.plan:
                # Update plan to include generated code
                state.plan.execution_command = "python baseline_experiment.py" # just a marker
            
            return {"execution_result": result}
        except Exception as err:
            logger.error("Failed to execute baseline: %s", err)
            return {"errors": [f"execute_baseline failed: {err}"]}

    def write_report_node(self, state: AgentState) -> dict[str, Any]:
        """Generate final replication report summary."""
        logger.info("Executing node: write_report")
        paper_title = state.paper.title if state.paper else state.paper_target
        decision_str = state.approval.decision.value

        verdict = "approved_for_replication" if state.approval.decision == HumanDecision.APPROVED else "aborted"

        claims_md = "\n".join(
            f"- **{c.benchmark_name}**: {c.target_metric} = {c.paper_value} ({c.baseline_algorithm})"
            for c in state.claims
        ) if state.claims else "*No quantitative claims recorded.*"

        code_md = "Synthetic Baseline"
        if state.code_resource and state.code_resource.repo_url:
            code_md = f"[{state.code_resource.repo_url}]({state.code_resource.repo_url}) ({state.code_resource.stars} stars)"
        execution_md = "Execution was not attempted."
        if state.execution_result:
            if state.execution_result.success:
                metrics_str = ", ".join(f"{k}: {v:.4f}" for k, v in state.execution_result.output_metrics.items())
                execution_md = f"**Status**: SUCCESS\n**Runtime**: {state.execution_result.runtime_seconds}s\n**Metrics**: {metrics_str or 'None extracted'}"
            else:
                execution_md = f"**Status**: FAILED\n**Exit Code**: {state.execution_result.exit_code}\n**Error**:\n```\n{state.execution_result.stderr.strip()[:500]}\n```"

        summary = f"""# Replication Summary: {paper_title}

- **Review Verdict**: {decision_str.upper()}
- **Implementation Target**: {code_md}
- **Planned Hardware**: {state.plan.target_hardware if state.plan else 'N/A'}

## Execution Results
{execution_md}

## Extracted Paper Claims
{claims_md}
"""

        metric_deltas = {}
        for c in state.claims:
            metric_deltas[c.benchmark_name] = {
                "target_metric": c.target_metric,
                "published_value": c.paper_value,
                "baseline_target": c.paper_value,
            }

        report = ReplicationReport(
            verdict=verdict,
            summary_markdown=summary.strip(),
            metric_deltas=metric_deltas,
            generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
        return {"report": report}


# Module-level default node functions
_default_factory = NodeFactory()

fetch_paper_node = _default_factory.fetch_paper_node
extract_claims_node = _default_factory.extract_claims_node
find_code_dataset_node = _default_factory.find_code_dataset_node
plan_baseline_node = _default_factory.plan_baseline_node
human_approval_node = _default_factory.human_approval_node
execute_baseline_node = _default_factory.execute_baseline_node
write_report_node = _default_factory.write_report_node
