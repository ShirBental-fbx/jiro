#!/usr/bin/env python3
"""Jiro CLI — local Jira workflow assistant."""
from __future__ import annotations

import argparse
import sys

from src.config import load_settings
from src.jiro_agent import JiroAgent
from src.models import CommentType
from src.presenters import (
    console,
    render_breakdown,
    render_comment,
    render_risk,
    render_standup,
    render_triage,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="jiro",
        description="Jiro — local Jira workflow assistant for engineers",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # triage
    triage_parser = subparsers.add_parser("triage", help="Daily triage of open issues")
    triage_parser.add_argument("--jql", type=str, default=None, help="Custom JQL query")

    # risk
    risk_parser = subparsers.add_parser("risk", help="Risk assessment for a ticket")
    risk_parser.add_argument("issue_key", type=str, help="Jira issue key (e.g. PROJ-123)")

    # breakdown
    breakdown_parser = subparsers.add_parser("breakdown", help="Implementation breakdown for a ticket")
    breakdown_parser.add_argument("issue_key", type=str, help="Jira issue key (e.g. PROJ-123)")

    # draft-comment
    draft_parser = subparsers.add_parser("draft-comment", help="Draft a Jira comment")
    draft_parser.add_argument("issue_key", type=str, help="Jira issue key (e.g. PROJ-123)")
    draft_parser.add_argument(
        "--type",
        type=str,
        choices=["status-update", "blocker-update", "clarification-request", "ready-for-review"],
        default="status-update",
        help="Comment type (default: status-update)",
    )

    # standup
    standup_parser = subparsers.add_parser("standup", help="Generate standup summary")
    standup_parser.add_argument("--jql", type=str, default=None, help="Custom JQL query")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        settings = load_settings()
    except EnvironmentError as exc:
        console.print(f"[red]Configuration error:[/red] {exc}")
        sys.exit(1)

    agent = JiroAgent(settings)

    try:
        _dispatch(agent, args)
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")
        sys.exit(130)
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)


def _dispatch(agent: JiroAgent, args: argparse.Namespace) -> None:
    cmd = args.command

    if cmd == "triage":
        report = agent.triage(jql=args.jql)
        render_triage(report)

    elif cmd == "risk":
        report = agent.risk(args.issue_key)
        render_risk(report)

    elif cmd == "breakdown":
        report = agent.breakdown(args.issue_key)
        render_breakdown(report)

    elif cmd == "draft-comment":
        comment_type = CommentType(args.type)
        draft = agent.draft(args.issue_key, comment_type)
        render_comment(draft)

    elif cmd == "standup":
        report = agent.standup(jql=args.jql)
        render_standup(report)

    else:
        console.print(f"[red]Unknown command: {cmd}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
