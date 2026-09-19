"""LangGraph workflow assembly with parallel fan-out and human interrupt gate."""

from __future__ import annotations

from typing import Any
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from zero_gaze.core.models.state import AgentState, HumanDecision
from zero_gaze.graph.nodes import (
    NodeFactory,
    extract_claims_node,
    fetch_paper_node,
    find_code_dataset_node,
    execute_baseline_node,
    human_approval_node,
    plan_baseline_node,
    write_report_node,
)


def route_after_approval(state: AgentState) -> str:
    """Conditional routing edge determining next node based on human decision."""
    if not state.approval or state.approval.decision == HumanDecision.ABORTED:
        return END
    if state.approval.decision == HumanDecision.REVISED:
        return "plan_baseline"
    return "execute_baseline"


def build_zero_gaze_graph(
    checkpointer: BaseCheckpointSaver | None = None,
    node_factory: NodeFactory | None = None,
) -> CompiledStateGraph:
    """Assemble and compile the Zero Gaze LangGraph workflow."""
    workflow = StateGraph(AgentState)

    if node_factory is not None:
        workflow.add_node("fetch_paper", node_factory.fetch_paper_node)
        workflow.add_node("extract_claims", node_factory.extract_claims_node)
        workflow.add_node("find_code_dataset", node_factory.find_code_dataset_node)
        workflow.add_node("plan_baseline", node_factory.plan_baseline_node)
        workflow.add_node("human_approval", node_factory.human_approval_node)
        workflow.add_node("execute_baseline", node_factory.execute_baseline_node)
        workflow.add_node("write_report", node_factory.write_report_node)
    else:
        workflow.add_node("fetch_paper", fetch_paper_node)
        workflow.add_node("extract_claims", extract_claims_node)
        workflow.add_node("find_code_dataset", find_code_dataset_node)
        workflow.add_node("plan_baseline", plan_baseline_node)
        workflow.add_node("human_approval", human_approval_node)
        workflow.add_node("execute_baseline", execute_baseline_node)
        workflow.add_node("write_report", write_report_node)

    # Entry point
    workflow.set_entry_point("fetch_paper")

    # Parallel Fan-Out: paper artifact flows concurrently to extraction and discovery
    workflow.add_edge("fetch_paper", "extract_claims")
    workflow.add_edge("fetch_paper", "find_code_dataset")
    # Fan-In Join: planner waits for both claims and code discovery to complete
    workflow.add_edge("extract_claims", "plan_baseline")
    workflow.add_edge("find_code_dataset", "plan_baseline")

    # Interrupt Gate: plan is held for human confirmation
    workflow.add_edge("plan_baseline", "human_approval")

    # Conditional branching based on human review verdict
    workflow.add_conditional_edges("human_approval", route_after_approval)

    # Execution edge
    workflow.add_edge("execute_baseline", "write_report")

    # Completion edge
    workflow.add_edge("write_report", END)

    if checkpointer is not None:
        saver = checkpointer
    else:
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
        allowed_modules = [
            ("zero_gaze.core.models.paper", "PaperExtractionSource"),
            ("zero_gaze.core.models.paper", "PaperArtifact"),
            ("zero_gaze.core.models.claims", "ClaimItem"),
            ("zero_gaze.core.models.claims", "ClaimsList"),
            ("zero_gaze.core.models.discovery", "RepoStatus"),
            ("zero_gaze.core.models.discovery", "CodeResource"),
            ("zero_gaze.core.models.plan", "ReplicationPlan"),
            ("zero_gaze.core.models.plan", "ReplicationReport"),
            ("zero_gaze.core.models.state", "HumanDecision"),
            ("zero_gaze.core.models.state", "HumanApproval"),
            ("zero_gaze.core.models.state", "AgentState"),
            ("zero_gaze.execution.sandbox", "ExecutionResult"),
        ]
        serde = JsonPlusSerializer(allowed_msgpack_modules=allowed_modules)
        saver = MemorySaver(serde=serde)

    return workflow.compile(checkpointer=saver)
