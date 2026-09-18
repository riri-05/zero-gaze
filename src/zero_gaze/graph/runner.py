"""High-level runner and execution lifecycle manager for Zero Gaze."""

from __future__ import annotations

import logging
from typing import Any
import uuid
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from zero_gaze.core.models.state import AgentState, HumanDecision
from zero_gaze.graph.workflow import build_zero_gaze_graph

logger = logging.getLogger(__name__)


class ZeroGazeRunner:
    """Provides a high-level facade for executing, checkpointing, and resuming the replication agent."""

    def __init__(self, graph: CompiledStateGraph | None = None) -> None:
        self.graph = graph or build_zero_gaze_graph()

    def start_replication(
        self,
        paper_target: str,
        thread_id: str | None = None,
    ) -> tuple[dict[str, Any], str, bool]:
        """Start paper replication pipeline.

        Returns:
            tuple: (state_values, thread_id, is_interrupted)
        """
        tid = thread_id or f"zero-gaze-{uuid.uuid4().hex[:8]}"
        config = {"configurable": {"thread_id": tid}}

        logger.info("Starting replication for '%s' on thread '%s'", paper_target, tid)
        state_output = self.graph.invoke({"paper_target": paper_target}, config=config)

        snapshot = self.graph.get_state(config)
        is_interrupted = bool(snapshot.next and "human_approval" in snapshot.next)

        return snapshot.values, tid, is_interrupted

    def resolve_approval(
        self,
        thread_id: str,
        decision: HumanDecision | str = HumanDecision.APPROVED,
        comments: str | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Resume execution across the human interrupt gate with an operator verdict."""
        config = {"configurable": {"thread_id": thread_id}}

        decision_str = decision.value if isinstance(decision, HumanDecision) else str(decision)
        payload = {
            "decision": decision_str,
            "comments": comments,
            "overrides": overrides or {},
        }

        logger.info("Resuming execution on thread '%s' with verdict: %s", thread_id, decision_str)
        self.graph.invoke(Command(resume=payload), config=config)

        snapshot = self.graph.get_state(config)
        return snapshot.values

    def get_state(self, thread_id: str) -> dict[str, Any]:
        """Retrieve current checkpoint state for a thread."""
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = self.graph.get_state(config)
        return snapshot.values
