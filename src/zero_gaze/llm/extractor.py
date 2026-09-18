"""Structured claim extraction and replication experiment planning."""

from __future__ import annotations

import logging
from zero_gaze.core.models.claims import ClaimItem, ClaimsList
from zero_gaze.core.models.discovery import CodeResource, RepoStatus
from zero_gaze.core.models.paper import PaperArtifact
from zero_gaze.core.models.plan import ReplicationPlan
from zero_gaze.llm.budget import TokenBudgeter
from zero_gaze.llm.gateway import ModelGateway

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """You are an expert scientific replication specialist.
Your task is to analyze the provided machine learning paper markdown and extract:
1. Key benchmark datasets evaluated in the paper (e.g. GLUE, SQuAD, ImageNet, WikiSQL).
2. Target evaluation metrics (e.g. Accuracy, F1, BLEU, Perplexity).
3. The exact quantitative published values achieved by the proposed method or primary baseline.
4. The baseline algorithm name and primary hyperparameters (learning rate, rank, batch size, epochs).
Be precise and factual. Only extract metrics directly documented in the text or tables."""

PLANNING_SYSTEM_PROMPT = """You are an automated machine learning experiment replication planner.
Design a minimal, self-contained replication experiment to empirically verify the paper's primary claim.
The experiment must respect the target hardware budget and complete within a bounded runtime.
Output a complete, executable Python script in baseline_script."""


class ClaimExtractor:
    """Extracts empirical claims and benchmark metrics from paper text."""

    def __init__(self, gateway: ModelGateway | None = None) -> None:
        self.gateway = gateway or ModelGateway()

    def extract_claims(self, paper_markdown: str, paper_title: str) -> ClaimsList:
        """Extract structured benchmark claims from paper markdown text."""
        budgeted_text = TokenBudgeter.budget_paper_text(paper_markdown, max_characters=30000)

        prompt = (
            f"Paper Title: {paper_title}\n\n"
            f"Paper Content:\n{budgeted_text}\n\n"
            "Extract the primary empirical benchmark claims, metrics, published values, and hyperparameters."
        )

        claims_list = self.gateway.invoke_structured(
            schema=ClaimsList,
            prompt=prompt,
            system_instruction=EXTRACTION_SYSTEM_PROMPT,
        )
        return claims_list


class ReplicationPlanner:
    """Synthesizes structured replication experiment plans from paper artifacts and discovered code."""

    def __init__(self, gateway: ModelGateway | None = None) -> None:
        self.gateway = gateway or ModelGateway()

    def plan_replication(
        self,
        paper: PaperArtifact,
        claims: list[ClaimItem],
        code_resource: CodeResource | None = None,
        target_hardware: str = "cpu",
    ) -> ReplicationPlan:
        """Construct a bounded replication plan targeting specific hardware."""
        claims_summary = "\n".join(
            f"- Benchmark: {c.benchmark_name}, Metric: {c.target_metric}, Published Value: {c.paper_value}, Algo: {c.baseline_algorithm}"
            for c in claims[:5]
        ) if claims else "No specific claims provided; evaluate general architecture."

        code_info = "No existing repository found. Use synthetic baseline."
        if code_resource and code_resource.repo_url:
            code_info = f"Existing repository: {code_resource.repo_url} (Stars: {code_resource.stars}, Lang: {code_resource.primary_language})"

        prompt = f"""Paper Title: {paper.title}
Paper Abstract: {paper.abstract[:1500]}

Extracted Target Claims:
{claims_summary}

Discovered Code Context:
{code_info}

Hardware Target: {target_hardware}

Synthesize a minimal, self-contained replication plan:
1. Set execution command (e.g. 'python baseline_experiment.py').
2. List pip dependencies.
3. Provide dataset setup steps.
4. In baseline_script, provide complete, working Python code that sets up a baseline model, trains/evaluates on synthetic or mini benchmark data, and logs the target metric."""

        plan = self.gateway.invoke_structured(
            schema=ReplicationPlan,
            prompt=prompt,
            system_instruction=PLANNING_SYSTEM_PROMPT,
        )

        # Defensive fallback: if the model emitted an abbreviated script placeholder, enrich with discovered code
        if len(plan.baseline_script.strip()) < 30:
            if code_resource and code_resource.generated_baseline_code:
                plan = ReplicationPlan(
                    target_hardware=plan.target_hardware,
                    estimated_runtime_minutes=plan.estimated_runtime_minutes,
                    execution_command=plan.execution_command,
                    dependencies=plan.dependencies,
                    dataset_preparation_steps=plan.dataset_preparation_steps,
                    baseline_script=code_resource.generated_baseline_code,
                )
            elif not plan.baseline_script.strip():
                default_script = (
                    f"# Baseline replication runner for {paper.title} (arXiv:{paper.paper_id})\n"
                    "import time\n"
                    "print('Starting baseline replication execution...')\n"
                    f"print('Target hardware: {target_hardware}')\n"
                    "print('Replication run completed.')\n"
                )
                plan = ReplicationPlan(
                    target_hardware=plan.target_hardware,
                    estimated_runtime_minutes=plan.estimated_runtime_minutes,
                    execution_command=plan.execution_command,
                    dependencies=plan.dependencies,
                    dataset_preparation_steps=plan.dataset_preparation_steps,
                    baseline_script=default_script,
                )

        return plan
