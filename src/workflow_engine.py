from __future__ import annotations

from collections import Counter

from src.models import (
    Issue,
    OrphanTaskItem,
    WorkOrigin,
    WorkOriginBreakdownItem,
    WorkflowHealthReport,
)


PRODUCT_TERMS = [
    "product",
    "prd",
    "roadmap",
    "planning",
]

BUG_PROD_TERMS = [
    "bug",
    "production",
    "prod",
    "incident",
    "hotfix",
    "outage",
    "sev",
]

ADHOC_TERMS = [
    "refactor",
    "tech debt",
    "techdebt",
    "chore",
    "infra",
    "engineering",
    "internal",
    "spike",
]


def analyze_workflow_health(issues: list[Issue]) -> WorkflowHealthReport:
    if not issues:
        return WorkflowHealthReport(
            product_coverage_pct=0.0,
            orphan_tasks=[],
            work_origin_breakdown=[],
        )

    linked_to_product = [issue for issue in issues if _has_product_planning_link(issue)]
    orphan_tasks = _find_orphan_tasks(issues)
    origin_breakdown = _build_origin_breakdown(issues)

    coverage_pct = round((len(linked_to_product) / len(issues)) * 100, 1)
    return WorkflowHealthReport(
        product_coverage_pct=coverage_pct,
        orphan_tasks=orphan_tasks,
        work_origin_breakdown=origin_breakdown,
    )


def classify_work_origin(issue: Issue) -> WorkOrigin:
    text = f"{issue.summary} {issue.description}".lower()
    issue_type = issue.issue_type.lower()
    labels = [label.lower() for label in issue.labels]
    components = [component.lower() for component in issue.components]
    meta_text = " ".join(labels + components)

    if _has_product_planning_link(issue):
        return WorkOrigin.PRODUCT_EPIC

    if issue_type == "bug" or _contains_any(text, BUG_PROD_TERMS) or _contains_any(meta_text, BUG_PROD_TERMS):
        return WorkOrigin.BUG_PRODUCTION

    if issue_type in ("task", "chore", "spike") or _contains_any(text, ADHOC_TERMS) or _contains_any(meta_text, ADHOC_TERMS):
        return WorkOrigin.ADHOC_ENGINEERING

    return WorkOrigin.UNKNOWN


def _has_product_planning_link(issue: Issue) -> bool:
    if issue.parent_key or issue.epic_key:
        return True

    issue_type = issue.issue_type.lower()
    if issue_type in ("epic", "story"):
        return True

    meta_text = " ".join([*(label.lower() for label in issue.labels), *(component.lower() for component in issue.components)])
    return _contains_any(meta_text, PRODUCT_TERMS)


def _find_orphan_tasks(issues: list[Issue]) -> list[OrphanTaskItem]:
    orphans: list[OrphanTaskItem] = []
    for issue in issues:
        issue_type = issue.issue_type.lower()
        if issue_type in ("epic", "story"):
            continue
        if issue.parent_key or issue.epic_key:
            continue
        orphans.append(
            OrphanTaskItem(
                issue_key=issue.key,
                summary=issue.summary,
                issue_type=issue.issue_type,
            )
        )
    return orphans


def _build_origin_breakdown(issues: list[Issue]) -> list[WorkOriginBreakdownItem]:
    counts = Counter(classify_work_origin(issue) for issue in issues)
    ordered = [
        WorkOrigin.PRODUCT_EPIC,
        WorkOrigin.BUG_PRODUCTION,
        WorkOrigin.ADHOC_ENGINEERING,
        WorkOrigin.UNKNOWN,
    ]
    return [
        WorkOriginBreakdownItem(origin=origin, count=counts.get(origin, 0))
        for origin in ordered
        if counts.get(origin, 0) > 0
    ]


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)
