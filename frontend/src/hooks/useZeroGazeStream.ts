import { useState, useEffect, useCallback, useRef } from "react";
import {
  PipelineStage,
  PaperArtifact,
  ClaimItem,
  CodeResource,
  ReplicationPlan,
  ExecutionResult,
  ReplicationReport,
  InterruptPayload,
} from "../types/protocol";

export interface StreamState {
  stage: PipelineStage;
  threadId: string | null;
  paper: PaperArtifact | null;
  claims: ClaimItem[];
  codeResource: CodeResource | null;
  plan: ReplicationPlan | null;
  approvalPayload: InterruptPayload | null;
  executionResult: ExecutionResult | null;
  report: ReplicationReport | null;
  terminalLogs: string[];
  activeNode: string | null;
  completedNodes: string[];
  isStreaming: boolean;
  error: string | null;
}

export function useZeroGazeStream() {
  const [state, setState] = useState<StreamState>({
    stage: "idle",
    threadId: null,
    paper: null,
    claims: [],
    codeResource: null,
    plan: null,
    approvalPayload: null,
    executionResult: null,
    report: null,
    terminalLogs: [],
    activeNode: null,
    completedNodes: [],
    isStreaming: false,
    error: null,
  });

  const eventSourceRef = useRef<EventSource | null>(null);

  const startReplication = useCallback((paperTarget: string, autoApprove: boolean = false) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const threadId = "zg-" + Math.random().toString(36).substring(2, 10);

    setState({
      stage: "fetch_paper",
      threadId,
      paper: null,
      claims: [],
      codeResource: null,
      plan: null,
      approvalPayload: null,
      executionResult: null,
      report: null,
      terminalLogs: [`[INIT] Bound thread ${threadId} for target ${paperTarget}`],
      activeNode: "fetch_paper",
      completedNodes: [],
      isStreaming: true,
      error: null,
    });

    const sseUrl = `/api/replication/stream/${threadId}?paper_target=${encodeURIComponent(paperTarget)}`;
    const es = new EventSource(sseUrl);
    eventSourceRef.current = es;

    es.addEventListener("agent:start", (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        setState((prev) => ({
          ...prev,
          terminalLogs: [...prev.terminalLogs, `[AGENT] Started workflow on target ${data.paper_target}`],
        }));
      } catch (e) {
        console.error(e);
      }
    });

    es.addEventListener("node:transition", (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        const node = data.node;
        const status = data.status;
        setState((prev) => {
          const completed = status === "completed" && !prev.completedNodes.includes(node)
            ? [...prev.completedNodes, node]
            : prev.completedNodes;
          return {
            ...prev,
            activeNode: node,
            completedNodes: completed,
            terminalLogs: [...prev.terminalLogs, `[STAGE] Node '${node}' -> ${status}`],
          };
        });
      } catch (e) {
        console.error(e);
      }
    });

    es.addEventListener("state:delta", (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        const delta = data.delta || {};
        setState((prev) => {
          const updated = { ...prev };
          if (delta.paper) {
            updated.paper = delta.paper;
            updated.terminalLogs = [
              ...updated.terminalLogs,
              `[INGEST] Ingested: "${delta.paper.title}" (${delta.paper.authors?.slice(0, 2).join(", ") || "Unknown"})`,
            ];
          }
          if (delta.claims) {
            updated.claims = delta.claims;
            updated.terminalLogs = [
              ...updated.terminalLogs,
              `[EXTRACT] Extracted ${delta.claims.length} benchmark claims`,
            ];
          }
          if (delta.code_resource) {
            updated.codeResource = delta.code_resource;
            updated.terminalLogs = [
              ...updated.terminalLogs,
              `[DISCOVER] Discovered: ${delta.code_resource.repo_url || "Synthetic baseline"} (${delta.code_resource.status})`,
            ];
          }
          if (delta.plan) {
            updated.plan = delta.plan;
            updated.terminalLogs = [
              ...updated.terminalLogs,
              `[PLAN] Plan synthesized: ${delta.plan.execution_command} (Target: ${delta.plan.target_hardware})`,
            ];
          }
          if (delta.execution_result) {
            updated.executionResult = delta.execution_result;
            const logMsg = delta.execution_result.success
              ? `[EXEC] Completed with exit code 0 in ${delta.execution_result.runtime_seconds}s`
              : `[EXEC] Failed with exit code ${delta.execution_result.exit_code}: ${delta.execution_result.error_message}`;
            updated.terminalLogs = [
              ...updated.terminalLogs,
              logMsg,
              ...(delta.execution_result.stdout ? delta.execution_result.stdout.split("\n").filter(Boolean) : []),
            ];
          }
          return updated;
        });
      } catch (e) {
        console.error(e);
      }
    });

    es.addEventListener("interrupt:requested", (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        setState((prev) => ({
          ...prev,
          stage: "human_approval",
          activeNode: "human_approval",
          approvalPayload: {
            thread_id: data.thread_id,
            prompt: data.prompt,
            plan: data.plan,
            code_resource: data.code_resource,
          },
          plan: data.plan || prev.plan,
          codeResource: data.code_resource || prev.codeResource,
          terminalLogs: [
            ...prev.terminalLogs,
            `[GATE] Human approval required for execution plan: ${data.plan?.execution_command || "python baseline.py"}`,
          ],
        }));

        if (autoApprove) {
          sendApproval("approved");
        }
      } catch (e) {
        console.error(e);
      }
    });

    es.addEventListener("execution:stdout", (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        setState((prev) => ({
          ...prev,
          terminalLogs: [...prev.terminalLogs, data.chunk],
        }));
      } catch (e) {
        console.error(e);
      }
    });

    es.addEventListener("agent:finish", (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        setState((prev) => ({
          ...prev,
          stage: "completed",
          isStreaming: false,
          activeNode: null,
          report: data.report,
          terminalLogs: [...prev.terminalLogs, `[FINISH] Workflow complete. Final verdict: ${data.report?.verdict || "done"}`],
        }));
        es.close();
      } catch (e) {
        console.error(e);
      }
    });

    es.addEventListener("agent:error", (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        setState((prev) => ({
          ...prev,
          stage: "failed",
          isStreaming: false,
          error: data.error,
          terminalLogs: [...prev.terminalLogs, `[ERROR] ${data.error}`],
        }));
        es.close();
      } catch (e) {
        console.error(e);
      }
    });

    es.onerror = () => {
      setState((prev) => ({
        ...prev,
        isStreaming: false,
        terminalLogs: [...prev.terminalLogs, "[STREAM] Disconnected from server"],
      }));
      es.close();
    };
  }, []);

  const sendApproval = useCallback(
    async (
      decision: "approved" | "aborted" | "revised",
      overrides?: { script?: string; timeout_seconds?: number },
      comments?: string
    ) => {
      if (!state.threadId) return;

      setState((prev) => ({
        ...prev,
        stage: decision === "approved" ? "execute_baseline" : decision === "aborted" ? "aborted" : "plan_baseline",
        approvalPayload: null,
        terminalLogs: [
          ...prev.terminalLogs,
          `[ACTION] Operator submitted verdict: ${decision.toUpperCase()}${comments ? ` ("${comments}")` : ""}`,
        ],
      }));

      try {
        const res = await fetch("/api/replication/approve", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            thread_id: state.threadId,
            decision,
            comments,
            overrides: overrides || {},
          }),
        });

        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Approval request failed");
        }

        const data = await res.json();
        if (data.state?.report) {
          setState((prev) => ({
            ...prev,
            stage: "completed",
            report: data.state.report,
            executionResult: data.state.execution_result || prev.executionResult,
          }));
        }
      } catch (err: unknown) {
        const errorMsg = err instanceof Error ? err.message : String(err);
        setState((prev) => ({
          ...prev,
          error: errorMsg,
          terminalLogs: [...prev.terminalLogs, `[ERROR] Failed to send approval: ${errorMsg}`],
        }));
      }
    },
    [state.threadId]
  );

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  return { state, startReplication, sendApproval };
}
