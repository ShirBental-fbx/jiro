from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from src.models import (
    BreakdownReport,
    CommentDraft,
    ParentSummaryReport,
    RiskReport,
    RiskSeverity,
    StandupReport,
    TriageReport,
)
from src.utils import truncate


console = Console()

SEVERITY_COLORS = {
    RiskSeverity.HIGH: "red",
    RiskSeverity.MEDIUM: "yellow",
    RiskSeverity.LOW: "dim",
}

URGENCY_COLORS = {
    "high": "red",
    "medium": "yellow",
    "low": "dim",
}

PRIORITY_COLORS = {
    "Highest": "bold red",
    "High": "red",
    "Medium": "yellow",
    "Low": "dim green",
    "Lowest": "dim",
}


def render_triage(report: TriageReport) -> None:
    console.print()
    console.rule("[bold]Jiro — Daily Triage[/bold]")
    console.print(f"[dim]{report.total_issues} open issues • {report.generated_at:%Y-%m-%d %H:%M}[/dim]")
    console.print()

    # Priority summary
    if report.priority_summary:
        table = Table(title="Priority Summary", show_lines=False, padding=(0, 1))
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Priority", no_wrap=True)
        table.add_column("Status", no_wrap=True)
        table.add_column("Days Stale", justify="right")
        table.add_column("Blocked", justify="center")
        table.add_column("Summary")

        for item in report.priority_summary:
            p_style = PRIORITY_COLORS.get(item.priority, "")
            blocked_marker = "[red]●[/red]" if item.has_blockers else "[dim]–[/dim]"
            table.add_row(
                item.issue_key,
                Text(item.priority, style=p_style),
                item.status,
                str(item.days_since_update),
                blocked_marker,
                truncate(item.summary, 60),
            )
        console.print(table)
        console.print()

    # Blockers
    if report.blockers:
        console.print(Panel.fit(
            _format_blockers(report),
            title="[red]Blockers[/red]",
            border_style="red",
        ))
        console.print()

    # Stale tickets
    if report.stale_tickets:
        console.print(Panel.fit(
            _format_stale(report),
            title="[yellow]Stale Tickets[/yellow]",
            border_style="yellow",
        ))
        console.print()

    # Workflow health
    if report.workflow_health:
        console.print(Panel.fit(
            _format_workflow_health(report),
            title="[magenta]Workflow Health[/magenta]",
            border_style="magenta",
        ))
        console.print()

    # Parent task summaries
    if report.parent_summaries:
        console.print("[bold]Parent Task Summaries[/bold]")
        for summary in report.parent_summaries:
            console.print(Panel.fit(
                _format_parent_summary_inline(summary),
                title=f"[cyan]{summary.parent_key}[/cyan] — {truncate(summary.parent_summary, 64)}",
                border_style="cyan",
            ))
        console.print()

    # Suggested actions
    if report.suggested_actions:
        console.print("[bold]Suggested Actions[/bold]")
        for action in report.suggested_actions[:10]:
            color = URGENCY_COLORS.get(action.urgency, "")
            console.print(f"  [{color}]▸[/{color}] [cyan]{action.issue_key}[/cyan]: {action.action}")
            console.print(f"    [dim]{action.reason}[/dim]")
        console.print()


def render_risk(report: RiskReport) -> None:
    console.print()
    console.rule(f"[bold]Jiro — Risk Assessment: {report.issue_key}[/bold]")
    console.print(f"[dim]{report.summary}[/dim]")
    console.print()

    if not report.has_risks:
        console.print("[green]No significant risks detected.[/green]")
        return

    table = Table(show_lines=True, padding=(0, 1))
    table.add_column("Severity", no_wrap=True)
    table.add_column("Risk Type", no_wrap=True)
    table.add_column("Finding")
    table.add_column("Action")

    for finding in report.findings:
        color = SEVERITY_COLORS.get(finding.severity, "")
        table.add_row(
            Text(finding.severity.value.upper(), style=color),
            finding.risk_type.value,
            finding.explanation,
            finding.recommended_action,
        )

    console.print(table)
    console.print()


def render_breakdown(report: BreakdownReport) -> None:
    console.print()
    console.rule(f"[bold]Jiro — Breakdown: {report.issue_key}[/bold]")
    console.print(f"[dim]{report.summary}[/dim]")
    console.print()

    if report.implementation_plan:
        console.print("[bold]Implementation Plan[/bold]")
        for i, step in enumerate(report.implementation_plan, 1):
            console.print(f"  {i}. {step}")
        console.print()

    if report.suggested_subtasks:
        table = Table(title="Suggested Subtasks", show_lines=False, padding=(0, 1))
        table.add_column("#", justify="right", style="dim")
        table.add_column("Category", style="cyan", no_wrap=True)
        table.add_column("Title")
        table.add_column("Description")

        for i, sub in enumerate(report.suggested_subtasks, 1):
            table.add_row(str(i), sub.category, sub.title, sub.description)
        console.print(table)
        console.print()

    if report.technical_risks:
        console.print("[bold yellow]Technical Risks[/bold yellow]")
        for risk in report.technical_risks:
            console.print(f"  [yellow]▸[/yellow] {risk}")
        console.print()

    if report.missing_information:
        console.print("[bold red]Missing Information[/bold red]")
        for item in report.missing_information:
            console.print(f"  [red]▸[/red] {item}")
        console.print()

    if report.clarification_questions:
        console.print("[bold]Clarification Questions[/bold]")
        for i, q in enumerate(report.clarification_questions, 1):
            console.print(f"  {i}. {q}")
        console.print()


def render_comment(draft: CommentDraft) -> None:
    console.print()
    console.rule(f"[bold]Jiro — Comment Draft: {draft.issue_key}[/bold]")
    console.print(f"[dim]Type: {draft.comment_type.value}[/dim]")
    console.print()

    console.print(Panel(
        draft.body,
        title="[green]Copy-paste ready[/green]",
        border_style="green",
        padding=(1, 2),
    ))
    console.print()


def render_standup(report: StandupReport) -> None:
    console.print()
    console.rule("[bold]Jiro — Standup[/bold]")
    console.print(f"[dim]{report.generated_at:%Y-%m-%d %H:%M}[/dim]")
    console.print()

    _render_standup_section("Yesterday", report.yesterday, "blue")
    _render_standup_section("Today", report.today, "green")
    _render_standup_section("Blockers", report.blockers, "red")

    if report.notes:
        console.print("[bold dim]Notes[/bold dim]")
        for note in report.notes:
            console.print(f"  [dim]• {note}[/dim]")
        console.print()


def render_parent_summary(report: ParentSummaryReport) -> None:
    console.print()
    console.rule(f"[bold]Jiro — Parent Task Summary: {report.parent_key}[/bold]")
    console.print(f"[dim]{report.parent_summary}[/dim]")
    console.print()

    console.print(Panel.fit(
        report.goal,
        title="[cyan]Goal[/cyan]",
        border_style="cyan",
    ))
    console.print()

    console.print(Panel.fit(
        report.overview,
        title="[magenta]Overview[/magenta]",
        border_style="magenta",
    ))
    console.print()

    console.print(Panel.fit(
        report.health,
        title="[yellow]Health[/yellow]",
        border_style="yellow",
    ))
    console.print()

    console.print("[bold]Progress[/bold]")
    for item in report.progress:
        console.print(f"  [green]•[/green] {item}")
    console.print()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_blockers(report: TriageReport) -> str:
    lines: list[str] = []
    for b in report.blockers:
        lines.append(f"[cyan]{b.issue_key}[/cyan]: {truncate(b.summary, 50)}")
        lines.append(f"  Signal: \"{b.signal}\" (from {b.source})")
    return "\n".join(lines)


def _format_stale(report: TriageReport) -> str:
    lines: list[str] = []
    for s in report.stale_tickets:
        lines.append(f"[cyan]{s.issue_key}[/cyan]: {truncate(s.summary, 50)} — {s.days_since_update}d stale ({s.status})")
    return "\n".join(lines)


def _format_workflow_health(report: TriageReport) -> str:
    workflow = report.workflow_health
    if not workflow:
        return "No workflow data."

    lines: list[str] = []
    lines.append(f"Product Coverage: [bold]{workflow.product_coverage_pct:.1f}%[/bold]")
    lines.append(f"Orphan Tasks: [bold]{len(workflow.orphan_tasks)}[/bold]")

    if workflow.work_origin_breakdown:
        lines.append("Work Origin:")
        for item in workflow.work_origin_breakdown:
            label = item.origin.value.replace("_", " ").title()
            lines.append(f"  - {label}: {item.count}")
    return "\n".join(lines)


def _format_parent_summary_inline(summary: ParentSummaryReport) -> str:
    lines: list[str] = []
    lines.append(f"[bold]Goal:[/bold] {summary.goal}")
    lines.append(f"[bold]Overview:[/bold] {summary.overview}")
    lines.append(f"[bold]Health:[/bold] {summary.health}")
    lines.append("[bold]Progress:[/bold]")
    for item in summary.progress[:3]:
        lines.append(f"  - {item}")
    return "\n".join(lines)


def _render_standup_section(title: str, items: list, color: str) -> None:
    console.print(f"[bold {color}]{title}[/bold {color}]")
    if not items:
        console.print(f"  [dim]Nothing to report.[/dim]")
    else:
        for item in items:
            console.print(f"  [cyan]{item.issue_key}[/cyan]: {item.summary}")
            if item.detail:
                console.print(f"    [dim]{item.detail}[/dim]")
    console.print()
