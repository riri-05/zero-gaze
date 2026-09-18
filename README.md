# Zero Gaze

> ML paper to replication plan agent.
> LangGraph agent that reads an arXiv paper and drafts the replication experiment.

<p align="center">
  <img src="assets/logo.png" alt="Zero Gaze Logo" width="220" />
</p>

## Overview

Zero Gaze is an autonomous research replication agent built with LangGraph. It converts theoretical machine learning papers into verified, executable experiment plans.

Given an arXiv identifier or PDF link, Zero Gaze extracts empirical benchmark claims and mathematical formulations. It discovers official codebases and datasets across PapersWithCode, Hugging Face, and GitHub. It synthesizes a hardware-aware replication script. An interactive human-in-the-loop checkpoint gates execution. The agent then generates a structured replication report comparing baseline results against original published metrics.

```mermaid
flowchart TD
    A[arXiv URL or PDF Target] --> B[Lego 01: Paper Ingestion & Markdown Engine<br/>PyMuPDF4LLM & arXiv API]
    B -->|PaperArtifact| C[Lego 02: Artifact Discovery Engine<br/>PapersWithCode / Hugging Face / GitHub]
    B -->|PaperArtifact| D[Lego 03: LLM Engine & Model Gateway<br/>OpenRouter Structured Claims]
    C -->|CodeResource| E[Replication Planning Node<br/>Hardware Budget & Baseline Script]
    D -->|ClaimsList| E
    E -->|ReplicationPlan| F{Lego 04: Human Approval Gate<br/>LangGraph interrupt}
    F -->|Approved| G[Replication Report & Code Generation]
    F -->|Aborted| H[Workflow Terminated]
    G --> I[Lego 05: Agent UI & Wire Protocol<br/>CopilotKit 2.0 & AG-UI 1.0 SSE]
    G -.->|Deferred Phase 7| J[Lego 06: Zero-Setup Runtime<br/>Kaggle Sandbox Execution]
```

---

## Lego Modules

The architecture is divided into modular Lego pieces. Each module has isolated responsibilities and documented contracts.

| Module | Location | Primary Tech | Responsibility |
| :--- | :--- | :--- | :--- |
| **Lego 01** | [`docs/01-paper-ingestion-lego/`](docs/01-paper-ingestion-lego/README.md) | PyMuPDF4LLM / arXiv API | Ingests arXiv papers and extracts structured markdown with tables and LaTeX. |
| **Lego 02** | [`docs/02-artifact-discovery-lego/`](docs/02-artifact-discovery-lego/README.md) | PapersWithCode / Hugging Face / GitHub | Finds existing code and benchmarks, or generates synthetic baselines. |
| **Lego 03** | [`docs/03-llm-engine-lego/`](docs/03-llm-engine-lego/README.md) | OpenRouter / `langchain-openai` | Routes prompts over free-tier models with Pydantic structured output. |
| **Lego 04** | [`docs/04-agent-graph-lego/`](docs/04-agent-graph-lego/README.md) | LangGraph Python | Orchestrates the state machine, fan-out edges, and human approval gates. |
| **Lego 05** | [`docs/05-agent-ui-agui-lego/`](docs/05-agent-ui-agui-lego/README.md) | CopilotKit 2.0 / AG-UI 1.0 | Streams agent thoughts and exposes interactive approvals to Next.js. |
| **Lego 06** | [`docs/06-kaggle-runtime-lego/`](docs/06-kaggle-runtime-lego/README.md) | Kaggle Python Kernel | (Deferred) Free-tier T4 GPU single-notebook execution target. |

---

## Architectural Invariants

1. **Statically Typed Boundaries.** Graph nodes exchange immutable Pydantic models. Loose dictionaries are prohibited in `AgentState`.
2. **Parallel Fan-Out.** Claim extraction and artifact discovery execute concurrently once paper ingestion completes.
3. **Boundary Resilience.** All external HTTP calls use dedicated gateway clients with timeout limits and exponential backoff retries.
4. **Mandatory Human-in-the-Loop Checkpoint.** The agent pauses execution before code execution. Human operators review and approve compute budgets and execution commands.
5. **Clean Separation of Concerns.** The core agent logic lives in a framework-agnostic Python package. The web interface and execution sandboxes consume this core as a dependency.

---

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Node.js 20 or higher (for the frontend dashboard)
- OpenRouter API key

### Environment Configuration

Create a `.env` file in the project root:

```bash
OPENROUTER_API_KEY="your_openrouter_api_key"
OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"
PRIMARY_MODEL="deepseek/deepseek-v4-flash-0731:free"
REASONING_MODEL="qwen/qwen3.8-27b:free"
FAST_MODEL="nvidia/nemotron-3.5-lightning:free"
```

---

## Project Structure

```
zero-gaze/
├── assets/                          # Static branding assets
│   └── logo.png
├── docs/                            # Modular Lego architecture blueprints
│   ├── 00-architecture-overview/
│   ├── 01-paper-ingestion-lego/
│   ├── 02-artifact-discovery-lego/
│   ├── 03-llm-engine-lego/
│   ├── 04-agent-graph-lego/
│   ├── 05-agent-ui-agui-lego/
│   └── 06-kaggle-runtime-lego/
├── .gitignore                       # Git ignore rules protecting secrets and caches
└── README.md                        # Project documentation and roadmap
```

---

## Roadmap

Development proceeds across seven verified phases. Each phase requires smoke testing and automated unit test verification before committing.

- [x] **Phase 0: Architectural Blueprint & Documentation.** Specifications for Lego 01 through Lego 05.
- [ ] **Phase 1: Core Foundation & Domain Models.** Pydantic schemas, error definitions, and package configuration.
- [ ] **Phase 2: Paper Ingestion Engine.** arXiv API client, PDF stream downloader, and PyMuPDF4LLM parser.
- [ ] **Phase 3: Artifact Discovery Engine.** PapersWithCode, Hugging Face, and GitHub search clients with synthetic stub generator.
- [ ] **Phase 4: LLM Engine & Routing Gateway.** OpenRouter fallback cascade, model routing matrix, and structured extraction.
- [ ] **Phase 5: LangGraph State Machine & Gate.** StateGraph with parallel fan-out, MemorySaver checkpointing, and interrupt handlers.
- [ ] **Phase 6: Agent UI & Wire Protocol.** FastAPI backend, AG-UI 1.0 SSE stream endpoint, and Next.js CopilotKit dashboard.
- [ ] **Phase 7: Execution Sandbox & Kaggle Runtime.** Isolated execution environment and Kaggle notebook release.
