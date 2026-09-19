"""Evaluation suite for CI/CD Pipeline. Tests end-to-end replication flow."""

import os
import sys
import logging
from zero_gaze.graph.runner import ZeroGazeRunner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def evaluate_paper(paper_id: str) -> bool:
    """Run full replication workflow for a paper and verify execution success."""
    logger.info(f"Starting evaluation for paper: {paper_id}")
    runner = ZeroGazeRunner()
    
    # Start replication
    state, thread_id, is_interrupted = runner.start_replication(paper_id)
    
    if not is_interrupted:
        logger.error("Workflow did not interrupt for approval.")
        return False
        
    logger.info("Workflow paused for human approval. Auto-approving for eval.")
    
    # Provide approval
    final_state = runner.resolve_approval(thread_id, decision="approved", comments="CI/CD Auto-Approve")
    
    # Verify Execution
    execution_result = final_state.get("execution_result")
    if not execution_result:
        logger.error("No execution result found in final state.")
        return False
        
    if not execution_result.success:
        logger.error(f"Execution failed. Exit code: {execution_result.exit_code}")
        logger.error(f"Stderr: {execution_result.stderr}")
        return False
        
    logger.info("Execution successful!")
    logger.info(f"Metrics: {execution_result.output_metrics}")
    return True

if __name__ == "__main__":
    # Test a known paper (e.g., LoRA)
    target = "2106.09685"
    if not evaluate_paper(target):
        logger.error("Evaluation failed.")
        sys.exit(1)
        
    logger.info("Evaluation passed.")
    sys.exit(0)
