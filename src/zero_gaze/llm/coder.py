"""Iterative coding loop with LLM and sandbox feedback."""

import logging
from typing import Any
from langchain_core.messages import SystemMessage, HumanMessage
from zero_gaze.execution.sandbox import SandboxRunner, ExecutionResult
from zero_gaze.llm.gateway import ModelGateway
from zero_gaze.core.models.claims import ClaimsList

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an automated machine learning experiment replication agent.
Your task is to write a self-contained PyTorch script to replicate the paper's primary claims.
The script MUST execute without manual intervention.
Output ONLY valid Python code inside a ```python block. No explanations."""

REPAIR_PROMPT = """The code you generated failed with the following execution trace.
Analyze the stack trace, fix the bugs, and output the fully corrected Python script.
Output ONLY valid Python code inside a ```python block.

Trace:
{trace}"""

class IterativeCoder:
    """Generates and refines code by executing it and feeding back stack traces."""

    def __init__(self, gateway: ModelGateway | None = None, sandbox: SandboxRunner | None = None, max_retries: int = 3):
        self.gateway = gateway or ModelGateway()
        self.sandbox = sandbox or SandboxRunner(timeout_seconds=60.0)
        self.max_retries = max_retries

    def _extract_code(self, llm_response: str) -> str:
        if "```python" in llm_response:
            return llm_response.split("```python")[1].split("```")[0].strip()
        elif "```" in llm_response:
            return llm_response.split("```")[1].split("```")[0].strip()
        return llm_response.strip()

    def generate_and_refine(self, claims: ClaimsList | None, paper_context: str) -> tuple[str, ExecutionResult]:
        """Generate code, run it, and iteratively repair it if it fails."""
        claims_json = claims.model_dump_json() if claims else "{}"
        prompt = f"Paper Context:\n{paper_context}\n\nClaims to verify:\n{claims_json}"
        
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ]
        
        # Use primary model directly
        model = self.gateway.get_chat_model(self.gateway.models_cascade[0], temperature=0.2)
        
        best_code = ""
        last_result = None

        for attempt in range(self.max_retries + 1):
            logger.info(f"IterativeCoder: Generation attempt {attempt + 1}/{self.max_retries + 1}")
            
            try:
                response = model.invoke(messages)
                current_code = self._extract_code(response.content)
                best_code = current_code
                
                result = self.sandbox.execute_script(current_code)
                last_result = result
                
                if result.success:
                    logger.info("IterativeCoder: Execution successful.")
                    return best_code, result
                
                logger.warning(f"IterativeCoder: Execution failed. Exit code: {result.exit_code}")
                # Append failure trace to messages for next attempt
                messages.append(HumanMessage(content=REPAIR_PROMPT.format(trace=result.stderr.strip() or result.stdout.strip())))
                
            except Exception as e:
                logger.error(f"IterativeCoder: LLM or Sandbox invocation failed: {e}")
                if not last_result:
                    last_result = ExecutionResult(
                        success=False, exit_code=-1, stdout="", stderr=str(e), runtime_seconds=0.0, error_message=str(e)
                    )
                return best_code, last_result
                
        logger.error("IterativeCoder: Max retries exhausted.")
        return best_code, last_result
