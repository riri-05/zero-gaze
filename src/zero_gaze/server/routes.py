"""FastAPI route handlers for replication execution, approval, and SSE streaming."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncGenerator
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from zero_gaze.core.models.state import HumanDecision
from zero_gaze.graph.runner import ZeroGazeRunner
from zero_gaze.server.sse import (
    format_agent_error,
    format_agent_finish,
    format_agent_start,
    format_execution_stdout,
    format_interrupt_requested,
    format_interrupt_resolved,
    format_node_transition,
    format_state_delta,
    format_state_snapshot,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Replication"])

# Global shared runner instance
runner = ZeroGazeRunner()


class StartReplicationRequest(BaseModel):
    paper_target: str = Field(..., description="arXiv URL or paper ID")
    thread_id: str | None = Field(default=None, description="Optional persistent thread ID")


class ApproveReplicationRequest(BaseModel):
    thread_id: str = Field(..., description="Target thread identifier")
    decision: HumanDecision = Field(default=HumanDecision.APPROVED, description="Approval decision")
    comments: str | None = Field(default=None, description="Reviewer feedback or notes")
    overrides: dict[str, Any] = Field(default_factory=dict, description="Configuration overrides")


class ReplicationStatusResponse(BaseModel):
    thread_id: str
    status: str
    is_interrupted: bool
    state: dict[str, Any]


@router.get("/health", summary="Service Health Check")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "zero-gaze-agent", "version": "0.1.0"}


@router.post(
    "/api/replication/start",
    response_model=ReplicationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Start paper replication pipeline",
)
def start_replication(request: StartReplicationRequest) -> ReplicationStatusResponse:
    """Initiate replication pipeline up to the human approval gate or completion."""
    try:
        state_values, tid, is_interrupted = runner.start_replication(
            paper_target=request.paper_target,
            thread_id=request.thread_id,
        )
        current_status = "interrupted_awaiting_approval" if is_interrupted else "completed"
        return ReplicationStatusResponse(
            thread_id=tid,
            status=current_status,
            is_interrupted=is_interrupted,
            state=state_values,
        )
    except Exception as err:
        logger.error("Failed to start replication: %s", err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Replication execution failed: {err}",
        ) from err


@router.post(
    "/api/replication/approve",
    response_model=ReplicationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve human approval interrupt gate",
)
def approve_replication(request: ApproveReplicationRequest) -> ReplicationStatusResponse:
    """Resume an interrupted replication run with the operator verdict."""
    try:
        final_state = runner.resolve_approval(
            thread_id=request.thread_id,
            decision=request.decision,
            comments=request.comments,
            overrides=request.overrides,
        )
        return ReplicationStatusResponse(
            thread_id=request.thread_id,
            status="completed" if request.decision != HumanDecision.ABORTED else "aborted",
            is_interrupted=False,
            state=final_state,
        )
    except Exception as err:
        logger.error("Failed to resolve approval for %s: %s", request.thread_id, err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve approval: {err}",
        ) from err


@router.get(
    "/api/replication/state/{thread_id}",
    response_model=ReplicationStatusResponse,
    summary="Get current replication state snapshot",
)
def get_replication_state(thread_id: str) -> ReplicationStatusResponse:
    """Retrieve checkpoint snapshot for a specific thread."""
    try:
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = runner.graph.get_state(config)
        state_values = snapshot.values
        if not state_values:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Thread '{thread_id}' not found.",
            )
        is_interrupted = bool(snapshot.next and "human_approval" in snapshot.next)
        return ReplicationStatusResponse(
            thread_id=thread_id,
            status="interrupted_awaiting_approval" if is_interrupted else "completed",
            is_interrupted=is_interrupted,
            state=state_values,
        )
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(err),
        ) from err


@router.get(
    "/api/replication/stream/{thread_id}",
    summary="AG-UI Server-Sent Events stream for real-time state synchronization",
)
async def stream_replication(
    thread_id: str,
    paper_target: str = Query(default="", description="Optional paper target to start if idle"),
) -> StreamingResponse:
    """Stream AG-UI Server-Sent Events for thread state transitions and approval prompts."""

    async def event_generator() -> AsyncGenerator[str, None]:
        yield format_agent_start(thread_id, paper_target)

        try:
            config = {"configurable": {"thread_id": thread_id}}
            snapshot = runner.graph.get_state(config)
            current_state = snapshot.values

            if not current_state and paper_target:
                queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
                loop = asyncio.get_running_loop()

                def run_stream() -> None:
                    try:
                        for chunk in runner.graph.stream(
                            {"paper_target": paper_target},
                            config=config,
                            stream_mode="updates",
                        ):
                            loop.call_soon_threadsafe(queue.put_nowait, ("update", chunk))
                        loop.call_soon_threadsafe(queue.put_nowait, ("done", None))
                    except Exception as exc:
                        loop.call_soon_threadsafe(queue.put_nowait, ("error", exc))

                loop.run_in_executor(None, run_stream)

                while True:
                    msg_type, payload = await queue.get()
                    if msg_type == "done":
                        break
                    elif msg_type == "error":
                        raise payload
                    elif msg_type == "update":
                        for node_name, node_update in payload.items():
                            if node_name == "__interrupt__":
                                continue
                            yield format_node_transition(thread_id, node_name, "completed")
                            yield format_state_delta(thread_id, node_update)

                snapshot = runner.graph.get_state(config)
                current_state = snapshot.values

            is_interrupted = bool(snapshot.next and "human_approval" in snapshot.next)
            yield format_state_snapshot(thread_id, current_state)

            if is_interrupted:
                plan_data = current_state.get("plan")
                plan_dict = plan_data.model_dump() if hasattr(plan_data, "model_dump") else (plan_data or {})
                code_data = current_state.get("code_resource")
                code_dict = code_data.model_dump() if hasattr(code_data, "model_dump") else (code_data or {})

                yield format_interrupt_requested(
                    thread_id=thread_id,
                    prompt="Please review the replication plan and approve execution.",
                    plan=plan_dict,
                    code_resource=code_dict,
                )
            else:
                report_data = current_state.get("report")
                report_dict = report_data.model_dump() if hasattr(report_data, "model_dump") else (report_data or {})
                yield format_agent_finish(thread_id, report=report_dict)
        except Exception as err:
            logger.error("Stream generation failed: %s", err)
            yield format_agent_error(thread_id, str(err))
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/api/copilotkit",
    summary="CopilotKit 2.0 / AG-UI compatible protocol endpoint",
)
def copilotkit_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
    """CopilotKit remote agent handshake and message forwarding endpoint."""
    return {
        "status": "ok",
        "agent": "zero_gaze_agent",
        "protocol": "AG-UI/1.0",
        "received_keys": list(payload.keys()),
    }
