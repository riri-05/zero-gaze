"""Evaluation suite for CI/CD Pipeline. Tests end-to-end replication flow."""

import os
import sys
import logging
from zero_gaze.graph.runner import ZeroGazeRunner
from unittest.mock import patch, MagicMock
from zero_gaze.core.models.plan import ReplicationPlan
from zero_gaze.core.models.claims import ClaimsList
logger = logging.getLogger(__name__)

def evaluate_paper(paper_id: str) -> bool:
    """Run full replication workflow for a paper and verify execution success."""
    logger.info(f"Starting evaluation for paper: {paper_id}")
    
    mock_claims = ClaimsList(paper_title="LoRA", claims=[])
    mock_plan = ReplicationPlan(
        target_hardware="cpu",
        estimated_runtime_minutes=1,
        execution_command="python baseline_experiment.py",
        dependencies=["torch"],
        dataset_preparation_steps=[],
        baseline_script=""
    )
    mock_chat = MagicMock()
    mock_chat.invoke.return_value = MagicMock(content="```python\nprint('Mock execution')\n```")
    
    with patch("zero_gaze.llm.extractor.ClaimExtractor.extract_claims", return_value=mock_claims), \
         patch("zero_gaze.llm.extractor.ReplicationPlanner.plan_replication", return_value=mock_plan), \
         patch("zero_gaze.llm.coder.ModelGateway.get_chat_model", return_value=mock_chat):
         
        runner = ZeroGazeRunner()
        state, thread_id, is_interrupted = runner.start_replication(paper_id)
        
        if not is_interrupted:
            logger.error("Workflow did not interrupt for approval.")
            return False
            
        logger.info("Workflow paused for human approval. Auto-approving for eval.")
        final_state = runner.resolve_approval(thread_id, decision="approved", comments="CI/CD Auto-Approve")
        
        execution_result = final_state.get("execution_result")
        if not execution_result:
            logger.error("No execution result found in final state.")
            return False
            
        if not execution_result.success:
            logger.error(f"Execution failed. Exit code: {execution_result.exit_code}")
            logger.error(f"Stderr: {execution_result.stderr}")
            return False
            
        logger.info("Execution successful!")
        return True

if __name__ == "__main__":
    target = "2106.09685"
    if not evaluate_paper(target):
        logger.error("Evaluation failed.")
        import sys
        sys.exit(1)
        
    logger.info("Evaluation passed.")
