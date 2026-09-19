"""Server-Sent Events (SSE) serializer conforming to AG-UI 1.0 specification."""

from __future__ import annotations

import json
from typing import Any
from pydantic import BaseModel


class AGUIEvent:
    """Representation of an AG-UI Server-Sent Event."""

    def __init__(self, event_type: str, data: dict[str, Any] | BaseModel | str) -> None:
        self.event_type = event_type
        if isinstance(data, BaseModel):
            self.data = data.model_dump()
        elif isinstance(data, dict):
            self.data = data
        else:
            self.data = {"message": str(data)}

    def format(self) -> str:
        """Format event as text/event-stream message."""
        payload = json.dumps(self.data, default=str)
        return f"event: {self.event_type}\ndata: {payload}\n\n"


def format_agent_start(thread_id: str, paper_target: str) -> str:
    """Format agent start lifecycle event."""
    return AGUIEvent("agent:start", {
        "thread_id": thread_id,
        "paper_target": paper_target,
        "protocol": "AG-UI/1.0",
    }).format()


def format_state_delta(thread_id: str, delta: dict[str, Any]) -> str:
    """Format state delta synchronization event."""
    return AGUIEvent("state:delta", {
        "thread_id": thread_id,
        "delta": delta,
    }).format()


def format_state_snapshot(thread_id: str, state_values: dict[str, Any]) -> str:
    """Format full state snapshot event."""
    return AGUIEvent("state:snapshot", {
        "thread_id": thread_id,
        "state": state_values,
    }).format()


def format_interrupt_requested(
    thread_id: str,
    prompt: str,
    plan: dict[str, Any] | None = None,
    code_resource: dict[str, Any] | None = None,
) -> str:
    """Format human operator interrupt request event."""
    return AGUIEvent("interrupt:requested", {
        "thread_id": thread_id,
        "prompt": prompt,
        "plan": plan or {},
        "code_resource": code_resource or {},
    }).format()


def format_interrupt_resolved(thread_id: str, decision: str) -> str:
    """Format human operator approval resolution event."""
    return AGUIEvent("interrupt:resolved", {
        "thread_id": thread_id,
        "decision": decision,
    }).format()


def format_agent_finish(thread_id: str, report: dict[str, Any] | None = None) -> str:
    """Format agent finish lifecycle event."""
    return AGUIEvent("agent:finish", {
        "thread_id": thread_id,
        "status": "completed",
        "report": report or {},
    }).format()


def format_agent_error(thread_id: str, error: str) -> str:
    """Format agent error event."""
    return AGUIEvent("agent:error", {
        "thread_id": thread_id,
        "error": error,
    }).format()


def format_node_transition(thread_id: str, node: str, status: str = "completed") -> str:
    """Format pipeline node lifecycle event."""
    return AGUIEvent("node:transition", {
        "thread_id": thread_id,
        "node": node,
        "status": status,
    }).format()


def format_execution_stdout(thread_id: str, chunk: str) -> str:
    """Format real-time execution stdout stream chunk."""
    return AGUIEvent("execution:stdout", {
        "thread_id": thread_id,
        "chunk": chunk,
    }).format()
