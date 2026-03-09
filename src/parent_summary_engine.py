from __future__ import annotations

import re

from src.models import Issue, ParentSummaryReport
from src.utils import days_ago
from src.utils import truncate


ACTIVE_STATUS_TERMS = [
    "to do",
    "todo",
    "in progress",
    "in review",
    "cr",
    "code review",
    "in development",
    "doing",
    "active",
]

IN_PROGRESS_STATUS_TERMS = [
    "in progress",
    "in development",
    "doing",
]

DONE_STATUS_TERMS = [
    "done",
    "closed",
    "resolved",
    "released",
    "completed",
]

STALE_CHILD_DAYS = 5

SECTION_NAMES = ("goal", "overview", "context")
PRIORITY_ORDER = {"Highest": 0, "High": 1, "Medium": 2, "Low": 3, "Lowest": 4}


def generate_parent_summary(parent_issue: Issue, child_issues: list[Issue]) -> ParentSummaryReport:
    goal = extract_goal_from_parent(parent_issue)
    active_tasks = _pick_active_tasks(child_issues, limit=3)
    overview = _build_overview(active_tasks)
    progress = _build_progress(active_tasks)
    health = _compute_initiative_health(child_issues)

    return ParentSummaryReport(
        parent_key=parent_issue.key,
        parent_summary=parent_issue.summary,
        goal=goal,
        overview=overview,
        health=health,
        progress=progress,
    )


def extract_goal_from_parent(parent_issue: Issue) -> str:
    goal = extract_goal_from_description(parent_issue.description or "")
    if goal != "No clear goal found in parent description.":
        return goal
    return _derive_goal_from_parent_summary(parent_issue.summary)


def extract_goal_from_description(description: str) -> str:
    """
    Extract a short goal from parent description.
    Priority:
      1) Goal/Overview/Context sections
      2) First meaningful sentence
    """
    if not description or not description.strip():
        return "No clear goal found in parent description."

    section_text = _extract_section_text(description, SECTION_NAMES)
    if section_text:
        sentence = _first_meaningful_sentence(section_text)
        if sentence:
            return truncate(sentence, 180)

    sentence = _first_meaningful_sentence(description)
    if sentence:
        return truncate(sentence, 180)

    return "No clear goal found in parent description."


def _extract_section_text(description: str, section_names: tuple[str, ...]) -> str | None:
    lines = [line.rstrip() for line in description.splitlines()]
    for idx, line in enumerate(lines):
        normalized = line.strip().lower()
        for section in section_names:
            if _is_section_heading(normalized, section):
                collected: list[str] = []
                # Inline style: "Goal: ...".
                inline_match = re.match(rf"^#*\s*{re.escape(section)}\s*:\s*(.+)$", normalized, re.IGNORECASE)
                if inline_match and inline_match.group(1).strip():
                    return inline_match.group(1).strip()

                # Block style:
                # Goal
                # <text>
                for next_line in lines[idx + 1:]:
                    stripped = next_line.strip()
                    if not stripped:
                        if collected:
                            break
                        continue
                    if _looks_like_new_heading(stripped):
                        break
                    collected.append(stripped)
                if collected:
                    return " ".join(collected)
    return None


def _is_section_heading(line: str, section: str) -> bool:
    if line == section:
        return True
    if line == f"{section}:":
        return True
    if line.startswith(f"## {section}") or line.startswith(f"### {section}") or line.startswith(f"# {section}"):
        return True
    return False


def _looks_like_new_heading(line: str) -> bool:
    if re.match(r"^#{1,6}\s+\w+", line):
        return True
    if re.match(r"^[A-Za-z][A-Za-z0-9 /\-]{0,40}:\s*$", line):
        return True
    return False


def _first_meaningful_sentence(text: str) -> str | None:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return None

    parts = re.split(r"(?<=[.!?])\s+", compact)
    for part in parts:
        sentence = part.strip(" -\t")
        if _is_meaningful_sentence(sentence):
            return sentence

    # If there are no clear sentence delimiters, use first meaningful chunk.
    chunks = [chunk.strip(" -\t") for chunk in compact.split(".")]
    for chunk in chunks:
        if _is_meaningful_sentence(chunk):
            return chunk
    return None


def _is_meaningful_sentence(sentence: str) -> bool:
    if len(sentence) < 20:
        return False
    if not re.search(r"[A-Za-z]{4,}", sentence):
        return False
    return True


def _pick_active_tasks(child_issues: list[Issue], limit: int = 3) -> list[Issue]:
    active = [issue for issue in child_issues if _is_active(issue.status)]
    active.sort(
        key=lambda issue: (
            PRIORITY_ORDER.get(issue.priority, 99),
            issue.summary.lower(),
        )
    )
    return active[:limit]


def _is_active(status: str) -> bool:
    normalized = (status or "").lower()
    return any(term in normalized for term in ACTIVE_STATUS_TERMS)


def _build_overview(active_tasks: list[Issue]) -> str:
    if not active_tasks:
        return "No active child tasks right now; current work may be queued, blocked, or not yet started."

    descriptors = [issue.summary.strip() for issue in active_tasks if issue.summary.strip()]
    if not descriptors:
        return "Current work is focused on active child tasks."
    if len(descriptors) == 1:
        return f"Current work is focused on {descriptors[0]}."
    if len(descriptors) == 2:
        return f"Current work is focused on {descriptors[0]} and {descriptors[1]}."
    return f"Current work is focused on {descriptors[0]}, {descriptors[1]}, and {descriptors[2]}."


def _build_progress(active_tasks: list[Issue]) -> list[str]:
    if not active_tasks:
        return ["No active child tasks to report progress on."]

    return [
        f"{issue.key} — {truncate(issue.summary, 90)} ({issue.status})"
        for issue in active_tasks
    ]


def _derive_goal_from_parent_summary(summary: str) -> str:
    text = (summary or "").strip()
    if not text:
        return "Define and deliver this parent initiative."

    lower = text.lower()
    if "tech debt" in lower:
        return "Address technical debt in the system."
    if "bug" in lower or "incident" in lower:
        return "Stabilize the system and resolve high-impact defects."
    if "onboard" in lower:
        return "Complete onboarding work required for this initiative."

    return f"Deliver the outcomes described in '{truncate(text, 100)}'."


def _compute_initiative_health(child_issues: list[Issue]) -> str:
    if _has_stale_tasks(child_issues):
        return "Stalled"
    if _has_in_progress_tasks(child_issues):
        return "Active"
    return "Queued"


def _has_stale_tasks(child_issues: list[Issue]) -> bool:
    for issue in child_issues:
        status = (issue.status or "").lower()
        if any(term in status for term in DONE_STATUS_TERMS):
            continue
        if days_ago(issue.updated) >= STALE_CHILD_DAYS:
            return True
    return False


def _has_in_progress_tasks(child_issues: list[Issue]) -> bool:
    for issue in child_issues:
        status = (issue.status or "").lower()
        if any(term in status for term in IN_PROGRESS_STATUS_TERMS):
            return True
    return False
