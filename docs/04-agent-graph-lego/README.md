# Lego 04: StateGraph Orchestration Engine

## 1. Overview & Responsibility
The **StateGraph Orchestration Engine** is the central nervous system of Zero Gaze. Built on LangGraph, it implements an explicit, typed state machine that chains data gathering, claim extraction, resource discovery, experiment planning, and report writing.

Crucially, it incorporates a **Human-in-the-Loop Interrupt Gate** prior to code generation or execution, ensuring the user reviews and confirms the replication scope.

```
             [fetch_paper]
                   │
           ┌───────┴───────┐
           ▼               ▼
   [extract_claims]  [find_code_dataset]
           │               │
           └───────┬───────┘
                   ▼
            [plan_baseline]
                   │
                   ▼
            [human_approval] ◄─── (LangGraph interrupt gate: approve / revise / abort)
                   │
           ┌───────┴───────┐
       [Approved]      [Aborted]
           │               │
           ▼               ▼
     [write_report]      [END]
           │
           ▼
         [END]
```

---

## 2. Official Provider Documentation Links
- **LangGraph Documentation:** [`https://langchain-ai.github.io/langgraph/`](https://langchain-ai.github.io/langgraph/)
- **LangGraph Human-in-the-Loop Guide:** [`https://langchain-ai.github.io/langgraph/how-tos/human-in-the-loop/`](https://langchain-ai.github.io/langgraph/how-tos/human-in-the-loop/)
- **LangGraph Persistence & Checkpointing:** [`https://langchain-ai.github.io/langgraph/how-tos/persistence/`](https://langchain-ai.github.io/langgraph/how-tos/persistence/)
- **LangGraph StateGraph API Reference:** [`https://langchain-ai.github.io/langgraph/reference/graphs/`](https://langchain-ai.github.io/langgraph/reference/graphs/)

---

## 3. State Schema Contract

```python
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional
import operator
from pydantic import BaseModel, Field
from zero_gaze.core.models.paper import PaperArtifact
from zero_gaze.core.models.discovery import CodeResource


class ClaimItem(BaseModel):
    benchmark_name: str
    target_metric: str
    paper_value: float
    baseline_algorithm: str
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)


class ReplicationPlan(BaseModel):
    target_hardware: str = "cpu"
    estimated_runtime_minutes: int = 10
    execution_command: str
    dependencies: List[str] = Field(default_factory=list)
    dataset_preparation_steps: List[str] = Field(default_factory=list)
    baseline_script: str


class ReplicationReport(BaseModel):
    verdict: str
    summary_markdown: str
    metric_deltas: Dict[str, Any] = Field(default_factory=dict)


class HumanDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REVISED = "revised"
    ABORTED = "aborted"


class HumanApproval(BaseModel):
    decision: HumanDecision = HumanDecision.PENDING
    reviewer_comments: Optional[str] = None
    config_overrides: Dict[str, Any] = Field(default_factory=dict)


class AgentState(BaseModel):
    paper_target: str
    paper: Optional[PaperArtifact] = None
    claims: List[ClaimItem] = Field(default_factory=list)
    code_resource: Optional[CodeResource] = None
    plan: Optional[ReplicationPlan] = None
    approval: HumanApproval = Field(default_factory=HumanApproval)
    report: Optional[ReplicationReport] = None
    errors: Annotated[List[str], operator.add] = Field(default_factory=list)
```

---

## 4. StateGraph Implementation

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt


# 1. Node Implementations
def fetch_paper_node(state: AgentState) -> dict:
    # calls Ingestion Lego
    return {"paper": state.paper}


def extract_claims_node(state: AgentState) -> dict:
    # calls LLM Lego in parallel
    return {"claims": []}


def find_code_dataset_node(state: AgentState) -> dict:
    # calls Discovery Lego in parallel
    return {"code_resource": None}


def plan_baseline_node(state: AgentState) -> dict:
    # joins claims and code_resource to construct replication plan
    return {"plan": None}


def human_approval_node(state: AgentState) -> dict:
    # Interrupt execution and wait for human operator approval payload
    user_payload = interrupt({
        "prompt": "Please review the replication plan and approve execution.",
        "plan": state.plan.model_dump() if state.plan else {},
        "code_resource": state.code_resource.model_dump() if state.code_resource else {},
    })

    return {
        "approval": HumanApproval(
            decision=user_payload.get("decision", HumanDecision.APPROVED),
            reviewer_comments=user_payload.get("comments"),
            config_overrides=user_payload.get("overrides", {}),
        )
    }


def write_report_node(state: AgentState) -> dict:
    return {"report": ReplicationReport(verdict="replicated", summary_markdown="# Summary")}


# 2. Conditional Routing Edge
def route_after_approval(state: AgentState) -> str:
    if state.approval.decision == HumanDecision.ABORTED:
        return END
    return "write_report"


# 3. Graph Assembly with Parallel Fan-Out
def build_zero_gaze_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("fetch_paper", fetch_paper_node)
    workflow.add_node("extract_claims", extract_claims_node)
    workflow.add_node("find_code_dataset", find_code_dataset_node)
    workflow.add_node("plan_baseline", plan_baseline_node)
    workflow.add_node("human_approval", human_approval_node)
    workflow.add_node("write_report", write_report_node)

    workflow.set_entry_point("fetch_paper")

    # Parallel Fan-Out
    workflow.add_edge("fetch_paper", "extract_claims")
    workflow.add_edge("fetch_paper", "find_code_dataset")

    # Fan-In Join at Planning
    workflow.add_edge("extract_claims", "plan_baseline")
    workflow.add_edge("find_code_dataset", "plan_baseline")

    # Human Gate and Routing
    workflow.add_edge("plan_baseline", "human_approval")
    workflow.add_conditional_edges("human_approval", route_after_approval)
    workflow.add_edge("write_report", END)

    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)
```
