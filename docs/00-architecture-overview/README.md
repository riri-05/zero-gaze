# Zero Gaze — Architecture & Modular Lego System

> **Zero Gaze** — ML paper → replication plan agent  
> *LangGraph agent that reads an arXiv paper and drafts the experiment.*

```
                 ┌────────────────────────────────────────────────────────┐
                 │                 ZERO GAZE SYSTEM MAP                   │
                 └────────────────────────────────────────────────────────┘

[arXiv Link / PDF] 
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ LEGO 01: Paper Ingestion & Markdown Engine (PyMuPDF / arXiv API)        │
│ • Extracts raw PDF streams to structured markdown with LaTeX & tables   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ PaperArtifact
                                     ├────────────────────────────────────┐
                                     ▼                                    ▼
┌──────────────────────────────────────────────────┐ ┌──────────────────────────────────────────────────┐
│ LEGO 02: Artifact Discovery Engine               │ │ LEGO 03: LLM Engine & Model Gateway              │
│ (PapersWithCode / HuggingFace / GitHub)          │ │ (OpenRouter Free Tier Router)                    │
│ • Locates official repositories & datasets       │ │ • Parallel structured claim & metric extraction  │
└────────────────────────┬─────────────────────────┘ └────────────────────────┬─────────────────────────┘
                         │ CodeResource                                       │ ClaimsList
                         └─────────────────────────┬──────────────────────────┘
                                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ LEGO 04: StateGraph Orchestration Engine (LangGraph Python)             │
│ • Coordinates fan-out execution and human-in-the-loop interrupt gate    │
│   [fetch] ──► [extract & discover in parallel] ──► [plan]               │
│                    ──► [APPROVE?] ──► [report]                          │
└──────────────────────────────────────────┬──────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ LEGO 05: Agent UI & Wire Protocol                                       │
│ • CopilotKit 2.0 + AG-UI 1.0 (SSE)                                      │
│ • Next.js React Interactive UI                                          │
│ • Generative state cards & approval modals                              │
└─────────────────────────────────────────────────────────────────────────┘

[Deferred to Phase 7]
LEGO 06: Zero-Setup Runtime & Kaggle Sandbox
• Self-contained headless notebook execution environment on free Kaggle GPU.
```

---

## The Lego Modules Index

| Lego Piece | Module Directory | Upstream Provider | Primary Responsibility |
| :--- | :--- | :--- | :--- |
| **Lego 01** | [`../01-paper-ingestion-lego/`](../01-paper-ingestion-lego/README.md) | arXiv API / PyMuPDF | Ingest arXiv papers and parse PDFs into structured markdown with math and tables. |
| **Lego 02** | [`../02-artifact-discovery-lego/`](../02-artifact-discovery-lego/README.md) | PapersWithCode / Hugging Face / GitHub | Discover existing code implementations, benchmark datasets, or generate synthetic stubs. |
| **Lego 03** | [`../03-llm-engine-lego/`](../03-llm-engine-lego/README.md) | OpenRouter / `langchain-openai` | Route prompts across free-tier models with structured JSON schema outputs. |
| **Lego 04** | [`../04-agent-graph-lego/`](../04-agent-graph-lego/README.md) | LangGraph | Orchestrate nodes, typed state machine, checkpoint persistence, and human interrupt gates. |
| **Lego 05** | [`../05-agent-ui-agui-lego/`](../05-agent-ui-agui-lego/README.md) | CopilotKit 2.0 / AG-UI 1.0 | Connect agent state to Next.js frontend over AG-UI Server-Sent Events protocol. |
| **Lego 06** | [`../06-kaggle-runtime-lego/`](../06-kaggle-runtime-lego/README.md) | Kaggle Notebook Runtime | (Deferred) Single-click zero-install replication execution on free Kaggle GPU/CPU. |

---

## Architectural Invariants

1. **Statically Typed Boundaries.** Graph nodes exchange immutable Pydantic models (`AgentState`), never loose dictionary payloads.
2. **Parallel Fan-Out.** Disjoint nodes (`extract_claims` and `find_code_dataset`) execute concurrently from the ingested paper artifact.
3. **Defensive Fallbacks.** If upstream services fail (such as arXiv HTML missing or PapersWithCode empty), the system falls back gracefully to secondary channels or synthetic baselines.
4. **Mandatory Human-in-the-Loop Checkpoint.** The agent never attempts to execute generated code without explicit human operator confirmation.
5. **Phased Delivery.** The primary delivery phase targets the core Python package, CLI, and AG-UI web interface. The Kaggle notebook runtime is deferred to subsequent release packaging.
