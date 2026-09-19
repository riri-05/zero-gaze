# Zero Gaze — Architecture & Modular Lego System

> Global System Specification & Domain Boundaries  
> An autonomous verification engine converting arXiv preprints into empirical experiments via LangGraph.

---

## 1. System Topology

```mermaid
flowchart TD
    A[arXiv Preprint Target] --> B[Lego 01: Paper Ingestion & Markdown Engine<br/>PyMuPDF4LLM & arXiv Export Gateway]
    B -->|PaperArtifact| C[Lego 02: Artifact Discovery Engine<br/>GitHub / Hugging Face / PapersWithCode]
    B -->|PaperArtifact| D[Lego 03: LLM Engine & Model Gateway<br/>OpenRouter Cascade Matrix]
    C -->|CodeResource| E[Replication Planner Node<br/>Hardware Budget & Baseline Script]
    D -->|ClaimsList| E
    E -->|ReplicationPlan| F{Lego 04: Human Approval Gate<br/>LangGraph interrupt}
    F -->|Approved| G[Replication Report & Baseline Execution]
    F -->|Aborted| H[Workflow Terminated]
    G --> I[Lego 05: Agent UI & Wire Protocol<br/>CopilotKit 2.0 & AG-UI 1.0 SSE]
    G --> J[Lego 06: Zero-Setup Runtime<br/>Kaggle GPU & Local Sandbox]
```

---

## 2. Domain-Driven Design Bounded Contexts

Zero Gaze is partitioned into five distinct bounded contexts. Each context maintains complete ownership over its internal models and communicates strictly via immutable value objects.

| Bounded Context | Lego Module | Domain Aggregates | External Boundaries |
| :--- | :--- | :--- | :--- |
| **Ingestion Context** | Lego 01 | `PaperArtifact`, `PaperExtractionSource` | arXiv Atom XML API, PDF Binary Streams, ar5iv HTML DOM |
| **Discovery Context** | Lego 02 | `CodeResource`, `RepoStatus` | GitHub Search REST API, Hugging Face Papers API, PapersWithCode |
| **Inference Context** | Lego 03 | `ClaimItem`, `ClaimsList` | OpenRouter OpenAI-Compatible Chat Completions API |
| **Orchestration Context** | Lego 04 | `AgentState`, `HumanApproval`, `ReplicationPlan` | LangGraph StateGraph, Checkpoint Storage (`MemorySaver`) |
| **Presentation Context** | Lego 05 | `AGUIEvent`, `ReplicationStatusResponse` | AG-UI 2.0 SSE Wire Stream, FastAPI Web Server, React 19 Cockpit |
| **Execution Context** | Lego 06 | `ExecutionResult`, `SandboxRunner` | Ephemeral Subprocess Cgroups, PyTorch Runtime, Kaggle T4 Kernel |
| **Operations Context** | Lego 07 | `render.yaml`, `vercel.json`, GitHub Actions | Multi-Cloud Deployment, Vercel Edge CDN, Render Web Service |

---

## 3. Global System Invariants

1. **Statically Typed Boundaries.** Graph nodes exchange immutable models conforming to `AgentState`. Untyped dictionaries or mutable global variables are prohibited across graph edges.
2. **Parallel Fan-Out.** Operations that depend solely on the ingested manuscript (`extract_claims` and `find_code_dataset`) execute concurrently. They join at `plan_baseline`, avoiding serialization latency.
3. **Idempotent Caching.** Upstream repository queries and document extractions are cached by normalized paper identifier. Re-running the pipeline returns identical cached records without consuming external quotas.
4. **Mandatory Human-in-the-Loop Checkpoint.** The engine cannot trigger code execution without an explicit human operator authorization token delivered through `Command(resume=...)`.
5. **Execution Containment.** Generated baseline scripts execute in ephemeral subprocess environments with strict execution timeouts, stdout capture, and metric parsing.

---

## 4. Subsystem Interaction Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Operator as Human Operator
    participant UI as AG-UI Presentation Layer (Lego 05)
    participant Graph as LangGraph Orchestration Engine (Lego 04)
    participant Ingestion as Ingestion Engine (Lego 01)
    participant Discovery as Artifact Discovery (Lego 02)
    participant LLM as Model Gateway (Lego 03)
    participant Sandbox as Execution Sandbox (Lego 06)

    Operator->>UI: Submit arXiv Paper Identifier (e.g. 2106.09685)
    UI->>Graph: Invoke StateGraph(paper_target)
    Graph->>Ingestion: Ingest Manuscript & Parse Markdown
    Ingestion-->>Graph: Return PaperArtifact
    par Concurrent Extraction & Discovery
        Graph->>Discovery: Discover Repositories & Datasets
        Discovery-->>Graph: Return CodeResource
    and
        Graph->>LLM: Extract Benchmark Claims & Metrics
        LLM-->>Graph: Return ClaimsList
    end
    Graph->>LLM: Synthesize Replication Plan
    LLM-->>Graph: Return ReplicationPlan
    Graph->>UI: Emit interrupt:requested (Pause at Human Gate)
    UI-->>Operator: Display Plan, Code, and Hardware Budget
    Operator->>UI: Click "Approve Execution"
    UI->>Graph: Dispatch Command(resume=Approved)
    Graph->>Sandbox: Execute Baseline Script (timeout=60s)
    Sandbox-->>Graph: Return ExecutionResult (stdout, metrics, exit_code)
    Graph->>UI: Emit agent:finish with ReplicationReport
    UI-->>Operator: Render Final Replication Summary
```

---

## 5. Global Failure Domain Matrix

| Subsystem | Failure Trigger | Detection Mechanism | Mitigation Policy | Degraded State |
| :--- | :--- | :--- | :--- | :--- |
| **Ingestion** | arXiv PDF stream unavailable or corrupted | HTTP status != 200 or missing `%PDF` magic bytes | Failover to ar5iv HTML DOM; if unavailable, fallback to title/abstract metadata | `METADATA_FALLBACK` extraction source |
| **Discovery** | GitHub secondary rate limit (HTTP 403/429) | JSON error payload or status code | Query PapersWithCode mirror; if missing, invoke `SyntheticStubGenerator` | `SYNTHETIC_STUB` code baseline |
| **Inference** | OpenRouter free endpoint rate limit (HTTP 429) | HTTP 429 status code | Exponential backoff with jitter; automatic cascade to secondary or tertiary model | Cascade model failover |
| **Orchestration** | State mutation validation error | Pydantic `ValidationError` at node boundary | Catch error, append message to `AgentState.errors`, and halt execution | Unchecked state halt |
| **Execution** | Script infinite loop or excessive memory | Subprocess timeout expiration | Terminate subprocess tree via `SIGKILL` after timeout threshold | `ExecutionResult.success = False` |
