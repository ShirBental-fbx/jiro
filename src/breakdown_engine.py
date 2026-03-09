from __future__ import annotations

import re

from src.models import (
    BreakdownReport,
    Issue,
    IssueComment,
    RiskReport,
    Subtask,
)


ENGINEERING_CATEGORIES = [
    "api_changes",
    "data_model",
    "migration",
    "backfill",
    "validation",
    "testing",
    "monitoring",
    "rollout",
    "documentation",
]

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "api_changes": ["api", "endpoint", "rest", "graphql", "grpc", "route", "handler", "controller"],
    "data_model": ["schema", "model", "table", "column", "field", "entity", "database", "db"],
    "migration": ["migration", "migrate", "alter table", "add column", "drop", "rename"],
    "backfill": ["backfill", "back-fill", "populate", "seed", "historic data", "retroactive"],
    "validation": ["validation", "validate", "constraint", "check", "sanitize", "input"],
    "testing": ["test", "spec", "coverage", "integration test", "unit test", "e2e"],
    "monitoring": ["monitoring", "observability", "alert", "metric", "logging", "dashboard", "datadog", "grafana"],
    "rollout": ["rollout", "deploy", "feature flag", "canary", "gradual", "release", "dark launch"],
    "documentation": ["runbook", "readme", "docs", "documentation", "playbook", "wiki"],
}


def generate_breakdown(
    issue: Issue,
    comments: list[IssueComment],
    risk_report: RiskReport | None = None,
) -> BreakdownReport:
    all_text = _gather_text(issue, comments)

    plan = _build_implementation_plan(issue, all_text)
    subtasks = _suggest_subtasks(issue, all_text)
    tech_risks = _identify_technical_risks(issue, all_text, risk_report)
    missing = _identify_missing_info(issue, all_text)
    questions = _generate_clarification_questions(issue, all_text, missing)

    return BreakdownReport(
        issue_key=issue.key,
        summary=issue.summary,
        implementation_plan=plan,
        suggested_subtasks=subtasks,
        technical_risks=tech_risks,
        missing_information=missing,
        clarification_questions=questions,
    )


def _gather_text(issue: Issue, comments: list[IssueComment]) -> str:
    parts = [issue.summary, issue.description or ""]
    for c in comments[:10]:
        parts.append(c.body)
    return "\n".join(parts).lower()


def _build_implementation_plan(issue: Issue, all_text: str) -> list[str]:
    plan: list[str] = []

    plan.append(f"Understand the full scope of: {issue.summary}")

    detected = _detect_categories(all_text)

    if "data_model" in detected:
        plan.append("Review and update data model / schema changes")
    if "migration" in detected:
        plan.append("Write and test database migration")
    if "backfill" in detected:
        plan.append("Plan and implement data backfill strategy")
    if "api_changes" in detected:
        plan.append("Implement API changes (request/response contracts, validation)")
    if "validation" in detected:
        plan.append("Add input validation and error handling")

    plan.append("Implement core business logic")

    if "testing" in detected or not detected:
        plan.append("Write unit and integration tests")
    if "monitoring" in detected:
        plan.append("Add monitoring, metrics, and alerting")
    if "rollout" in detected:
        plan.append("Plan rollout strategy (feature flags, canary, gradual)")
    if "documentation" in detected:
        plan.append("Update documentation and runbooks")

    if not any(cat in detected for cat in ("testing",)):
        plan.append("Write tests covering happy path and edge cases")

    plan.append("Code review and QA")

    return plan


def _suggest_subtasks(issue: Issue, all_text: str) -> list[Subtask]:
    subtasks: list[Subtask] = []
    detected = _detect_categories(all_text)

    if "data_model" in detected:
        subtasks.append(Subtask(
            title=f"[{issue.key}] Schema / data model changes",
            description="Define and implement required schema changes.",
            category="data_model",
        ))

    if "migration" in detected:
        subtasks.append(Subtask(
            title=f"[{issue.key}] Database migration",
            description="Write migration script, test rollback, validate on staging.",
            category="migration",
        ))

    if "backfill" in detected:
        subtasks.append(Subtask(
            title=f"[{issue.key}] Data backfill",
            description="Backfill existing data to match new schema/logic.",
            category="backfill",
        ))

    if "api_changes" in detected:
        subtasks.append(Subtask(
            title=f"[{issue.key}] API implementation",
            description="Implement endpoint changes, request validation, response formatting.",
            category="api_changes",
        ))

    subtasks.append(Subtask(
        title=f"[{issue.key}] Core implementation",
        description="Implement the primary business logic for this ticket.",
        category="implementation",
    ))

    subtasks.append(Subtask(
        title=f"[{issue.key}] Testing",
        description="Unit tests, integration tests, edge case coverage.",
        category="testing",
    ))

    if "monitoring" in detected:
        subtasks.append(Subtask(
            title=f"[{issue.key}] Monitoring and observability",
            description="Add metrics, alerts, and dashboards.",
            category="monitoring",
        ))

    if "rollout" in detected:
        subtasks.append(Subtask(
            title=f"[{issue.key}] Rollout plan",
            description="Feature flag setup, canary strategy, rollback plan.",
            category="rollout",
        ))

    return subtasks


def _identify_technical_risks(
    issue: Issue,
    all_text: str,
    risk_report: RiskReport | None,
) -> list[str]:
    risks: list[str] = []

    if risk_report:
        for finding in risk_report.findings:
            risks.append(f"{finding.risk_type.value}: {finding.explanation}")

    if "migration" in _detect_categories(all_text):
        risks.append("Database migration requires careful rollback planning and staging validation.")

    if "backfill" in _detect_categories(all_text):
        risks.append("Backfill may be long-running — consider batching and idempotency.")

    if re.search(r"third.party|external.api|vendor|saas", all_text):
        risks.append("External dependency — verify SLA, rate limits, and failure modes.")

    if re.search(r"concurren|race.condition|deadlock|lock", all_text):
        risks.append("Concurrency concerns — review locking strategy and test under contention.")

    return risks


def _identify_missing_info(issue: Issue, all_text: str) -> list[str]:
    missing: list[str] = []

    if not issue.has_description:
        missing.append("No description provided.")
    elif issue.description_length < 100:
        missing.append("Description is very short — likely missing important context.")

    ac_signals = ["acceptance criteria", "ac:", "definition of done", "expected behavior"]
    if not any(s in all_text for s in ac_signals):
        missing.append("No acceptance criteria found.")

    if not issue.story_points:
        missing.append("No story points / effort estimate.")

    if re.search(r"tbd|to be determined|tbc|to be confirmed", all_text):
        missing.append("Text contains TBD/TBC markers — information is explicitly incomplete.")

    return missing


def _generate_clarification_questions(
    issue: Issue,
    all_text: str,
    missing: list[str],
) -> list[str]:
    questions: list[str] = []

    if "No acceptance criteria found." in missing:
        questions.append("What are the acceptance criteria for this ticket?")

    if "No description provided." in missing or "Description is very short" in missing[0:1]:
        questions.append("Can you provide more context on the expected scope and behavior?")

    if re.search(r"depends on|blocked by|dependent on", all_text):
        questions.append("What is the current status of the dependency? Who owns it?")

    if re.search(r"rollback|roll back", all_text):
        questions.append("What is the rollback strategy if this change causes issues?")

    if re.search(r"existing data|existing users|backward.compat", all_text):
        questions.append("How should existing data / users be handled during the transition?")

    if not questions:
        questions.append("Are there any constraints or edge cases not captured in the ticket?")

    return questions


def _detect_categories(text: str) -> set[str]:
    detected: set[str] = set()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            detected.add(category)
    return detected
