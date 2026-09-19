# Zero Gaze

> Autonomous machine learning research replication engine.
> Ingests arXiv papers, discovers reference codebases, extracts empirical claims, and synthesizes verifiable experiment baselines via LangGraph state machines.

<p align="center">
  <img src="assets/logo.png" alt="Zero Gaze Logo" width="220" />
</p>

<p align="center">
  <a href="https://zero-gaze-seven.vercel.app"><img src="https://img.shields.io/badge/Vercel-Deployment%20Live-000000.svg?logo=vercel&logoColor=white" alt="Vercel" /></a>
  <a href="https://zero-gaze-api.onrender.com/health"><img src="https://img.shields.io/badge/Render-API%20Online-46E3B7.svg?logo=render&logoColor=white" alt="Render" /></a>
  <a href="https://github.com/riri-05/zero-gaze/actions/workflows/eval.yml"><img src="https://github.com/riri-05/zero-gaze/actions/workflows/eval.yml/badge.svg" alt="CI/CD Pipeline" /></a>
  <a href="https://react.dev"><img src="https://img.shields.io/badge/React-19-61DAFB.svg?logo=react&logoColor=black" alt="React 19" /></a>
  <a href="https://github.com/riri-05/zero-gaze"><img src="https://img.shields.io/badge/LangGraph-StateGraph-blue.svg" alt="LangGraph" /></a>
  <a href="https://github.com/riri-05/zero-gaze"><img src="https://img.shields.io/badge/Protocol-AG--UI%202.0%20(SSE)-emerald.svg" alt="AG-UI" /></a>
  <a href="https://github.com/riri-05/zero-gaze"><img src="https://img.shields.io/badge/Python-3.11%2B-blue.svg" alt="Python" /></a>
  <a href="https://github.com/riri-05/zero-gaze"><img src="https://img.shields.io/badge/Tests-64%20Passed-success.svg" alt="Tests" /></a>
  <a href="https://github.com/riri-05/zero-gaze"><img src="https://img.shields.io/badge/License-MIT-neutral.svg" alt="License" /></a>
</p>

---

## Technical Overview

Zero Gaze is a scientific reproduction engine designed to verify machine learning literature at scale. It automates the transition from theoretical academic manuscripts into executable, resource-bounded experiment baselines.

The engine accepts an arXiv identifier or PDF stream. It parses the document hierarchy, extracts empirical claims with statistical metrics, discovers public codebases across open-source hubs, synthesizes executable replication code, gates execution through human operator checkpoints, and executes baselines inside ephemeral sandboxes.

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
    G --> J[Lego 06: Zero-Setup Runtime<br/>Kaggle & Local Sandbox Execution]
```

---

## Quickstart

### 1. Thirty-Second Terminal Quickstart

```bash
# Clone and install in development mode
git clone https://github.com/riri-05/zero-gaze.git
cd zero-gaze
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Configure OpenRouter API key
cp .env.example .env
# Supply your OPENROUTER_API_KEY in .env

# Replicate any arXiv paper in one command
zero-gaze replicate 2106.09685 --auto-approve
```

#### Expected Terminal Output

```
Initiating replication for paper target: 2106.09685
[1/4] Ingested: LoRA: Low-Rank Adaptation of Large Language Models (31,930 chars)
[2/4] Discovered code: https://github.com/microsoft/LoRA (13,800 stars)
[3/4] Extracted claims: GLUE MNLI Accuracy = 90.2%
[4/4] Plan synthesized: python baseline_experiment.py (Hardware: cpu, Est: 10 min)
============================================================
HUMAN-IN-THE-LOOP INTERRUPT GATE
============================================================
Paper: LoRA: Low-Rank Adaptation of Large Language Models
Target Hardware: cpu
Command: python baseline_experiment.py
Estimated Runtime: 10 min
Auto-approving execution per --auto-approve flag.
============================================================
REPLICATION SUMMARY
============================================================
# Replication Summary: LoRA: Low-Rank Adaptation of Large Language Models
- Review Verdict: APPROVED
- Implementation Target: https://github.com/microsoft/LoRA (13,800 stars)
- Planned Hardware: cpu
- Estimated Runtime: 10 minutes
```

---

### 2. Interactive Web Dashboard in One Command

```bash
zero-gaze serve --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` in your browser. The embedded React 19 + AG-UI 1.0 Server-Sent Events dashboard lets you submit arXiv IDs, inspect real-time streaming benchmark claims, edit and authorize baseline code in an interactive approval cockpit, and inspect live sandbox execution logs.

---

### 3. Four-Line Python API

```python
from zero_gaze.graph import ZeroGazeRunner

runner = ZeroGazeRunner()
state, thread_id, _ = runner.start_replication("2106.09685")
final_state = runner.resolve_approval(thread_id, decision="approved")
print(final_state["report"].summary_markdown)
```

---

### 4. Zero-Setup Kaggle Notebook (Free T4 GPU)

Run Zero Gaze in a browser without any local Python or GPU installation:
- Open [`notebooks/zero_gaze_kaggle_free.ipynb`](notebooks/zero_gaze_kaggle_free.ipynb).
- Features in-cell `ipywidgets` buttons for interactive human-in-the-loop experiment approvals.

---

## Architectural Invariants

1. **Statically Typed Boundaries.** Graph nodes exchange immutable Pydantic models (`AgentState`). Loose dictionaries are rejected across execution boundaries.
2. **Parallel Fan-Out.** Disjoint operations (`extract_claims` and `find_code_dataset`) execute concurrently once paper ingestion completes, reducing analysis latency.
3. **Boundary Resilience.** All external HTTP queries (arXiv, Hugging Face, GitHub, OpenRouter) route through gateway clients with exponential jitter backoff and circuit-breaking fallbacks.
4. **Mandatory Human-in-the-Loop Checkpoint.** Execution of generated code is gated by a LangGraph interrupt token. Compute resources cannot be allocated without explicit human authorization.
5. **Dual-Surface Delivery.** Every replication feature is executable locally via the `zero-gaze` CLI and FastAPI AG-UI web server, as well as remotely in standalone Kaggle GPU notebooks.
6. **Execution Containment.** Experiment code runs inside ephemeral subprocess sandboxes with strict runtime ceilings and metric extraction parsers.


## Subsystem Architecture Index

The architecture is divided into discrete technical modules documented in [`docs/`](docs/):

| Module | Architectural Specification | Provider / Framework | Primary Invariant |
| :--- | :--- | :--- | :--- |
| **Overview** | [`docs/00-architecture-overview/`](docs/00-architecture-overview/README.md) | System Blueprint | Global domain boundaries, event flows, and state machines. |
| **Lego 01** | [`docs/01-paper-ingestion-lego/`](docs/01-paper-ingestion-lego/README.md) | PyMuPDF4LLM / arXiv API | Three-tier recovery hierarchy (`PDF` -> `HTML` -> `Metadata`). |
| **Lego 02** | [`docs/02-artifact-discovery-lego/`](docs/02-artifact-discovery-lego/README.md) | GitHub / Hugging Face / PwC | Idempotent multi-source resolution and synthetic baseline generation. |
| **Lego 03** | [`docs/03-llm-engine-lego/`](docs/03-llm-engine-lego/README.md) | OpenRouter / `langchain-openai` | Automatic cascade failover (`nemotron` -> `qwen` -> `deepseek`). |
| **Lego 04** | [`docs/04-agent-graph-lego/`](docs/04-agent-graph-lego/README.md) | LangGraph StateGraph | Checkpoint persistence via `MemorySaver` and human interrupt gate. |
| **Lego 05** | [`docs/05-agent-ui-agui-lego/`](docs/05-agent-ui-agui-lego/README.md) | CopilotKit 2.0 / AG-UI 1.0 | Real-time Server-Sent Events (SSE) state synchronization. |
| **Lego 06** | [`docs/06-kaggle-runtime-lego/`](docs/06-kaggle-runtime-lego/README.md) | Subprocess Sandbox / Kaggle Kernel | Resource-bounded sandboxed execution and metric extraction grammar. |


## Verification & Test Suite

```bash
# Run the complete test suite across all 7 subsystems
pytest tests/
```
