"""Command-line interface (CLI) for Zero Gaze."""

from __future__ import annotations

import argparse
import sys
import uvicorn
from zero_gaze.core.models.state import HumanDecision
from zero_gaze.graph.runner import ZeroGazeRunner


def serve_command(args: argparse.Namespace) -> None:
    """Start the Zero Gaze FastAPI agent API and dashboard."""
    print(f"Starting Zero Gaze AG-UI Server on http://{args.host}:{args.port}")
    uvicorn.run("zero_gaze.server.app:app", host=args.host, port=args.port, reload=args.reload)


def replicate_command(args: argparse.Namespace) -> None:
    """Run paper replication directly from the terminal with interactive approval."""
    runner = ZeroGazeRunner()
    print(f"Initiating replication for paper target: {args.target}")

    state, tid, interrupted = runner.start_replication(
        paper_target=args.target,
        thread_id=args.thread,
    )

    if interrupted:
        print("\n" + "=" * 60)
        print("HUMAN-IN-THE-LOOP INTERRUPT GATE")
        print("=" * 60)
        paper_title = state.get("paper").title if state.get("paper") else args.target
        print(f"Paper: {paper_title}")
        print(f"Target Hardware: {state.get('plan').target_hardware if state.get('plan') else 'cpu'}")
        print(f"Command: {state.get('plan').execution_command if state.get('plan') else 'None'}")
        print(f"Estimated Runtime: {state.get('plan').estimated_runtime_minutes if state.get('plan') else 0} min")

        if args.auto_approve:
            decision = HumanDecision.APPROVED
            print("Auto-approving execution per --auto-approve flag.")
        else:
            choice = input("\nAuthorize experiment execution? [y/N]: ").strip().lower()
            decision = HumanDecision.APPROVED if choice in ("y", "yes") else HumanDecision.ABORTED

        final_state = runner.resolve_approval(thread_id=tid, decision=decision)
        if final_state.get("report"):
            print("\n" + "=" * 60)
            print("REPLICATION SUMMARY")
            print("=" * 60)
            print(final_state["report"].summary_markdown)
        else:
            print("\nExecution was aborted.")
    else:
        print("Replication completed without interruption.")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="zero-gaze",
        description="Zero Gaze — ML Paper to Replication Plan Agent",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # serve subcommand
    serve_parser = subparsers.add_parser("serve", help="Start the FastAPI server and web dashboard")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Binding host IP (default: 127.0.0.1)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    serve_parser.add_argument("--reload", action="store_true", help="Enable live auto-reloading")
    serve_parser.set_defaults(func=serve_command)

    # replicate subcommand
    replicate_parser = subparsers.add_parser("replicate", help="Replicate an arXiv paper from terminal")
    replicate_parser.add_argument("target", help="arXiv paper ID or URL (e.g. 2106.09685)")
    replicate_parser.add_argument("--thread", default=None, help="Optional thread ID for persistence")
    replicate_parser.add_argument("--auto-approve", action="store_true", help="Automatically approve plan execution")
    replicate_parser.set_defaults(func=replicate_command)

    parsed = parser.parse_args()
    parsed.func(parsed)


if __name__ == "__main__":
    main()
