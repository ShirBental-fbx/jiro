"""
Orchestration layer. Composes JiraClient with engines to produce reports.
This is the single entry point that CLI and future integrations should use.
"""
from __future__ import annotations

from src.config import Settings
from src.jira_client import JiraClient
from src.models import (
    BreakdownReport,
    CommentDraft,
    CommentType,
    Issue,
    IssueComment,
    ParentSummaryReport,
    RiskReport,
    StandupReport,
    TriageReport,
)
from src.triage_engine import DEFAULT_JQL, build_triage_report
from src.risk_engine import assess_risks
from src.breakdown_engine import generate_breakdown
from src.comment_engine import draft_comment
from src.parent_summary_engine import generate_parent_summary
from src.standup_engine import generate_standup


class JiroAgent:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = JiraClient(settings)

    def triage(self, jql: str | None = None) -> TriageReport:
        """Run daily triage on open issues."""
        jql = jql or DEFAULT_JQL
        issues = self._client.search_issues(jql)

        comments_by_key: dict[str, list[IssueComment]] = {}
        for issue in issues:
            comments_by_key[issue.key] = self._client.get_issue_comments(issue.key)

        report = build_triage_report(issues, comments_by_key, self._settings)
        report.parent_summaries = self._build_parent_summaries(issues)
        return report

    def risk(self, issue_key: str) -> RiskReport:
        """Assess risks for a specific ticket."""
        issue = self._client.get_issue(issue_key)
        comments = self._client.get_issue_comments(issue_key)
        return assess_risks(issue, comments, self._settings)

    def breakdown(self, issue_key: str) -> BreakdownReport:
        """Generate implementation breakdown for a specific ticket."""
        issue = self._client.get_issue(issue_key)
        comments = self._client.get_issue_comments(issue_key)
        risk_report = assess_risks(issue, comments, self._settings)
        return generate_breakdown(issue, comments, risk_report)

    def draft(self, issue_key: str, comment_type: CommentType) -> CommentDraft:
        """Draft a Jira comment for a specific ticket."""
        issue = self._client.get_issue(issue_key)
        comments = self._client.get_issue_comments(issue_key)
        risk_report = assess_risks(issue, comments, self._settings)
        return draft_comment(issue, comments, comment_type, risk_report)

    def standup(self, jql: str | None = None) -> StandupReport:
        """Generate a standup report from current open issues."""
        jql = jql or DEFAULT_JQL
        issues = self._client.search_issues(jql)

        comments_by_key: dict[str, list[IssueComment]] = {}
        for issue in issues:
            comments_by_key[issue.key] = self._client.get_issue_comments(issue.key)

        return generate_standup(issues, comments_by_key, self._settings)

    def parent_summary(self, issue_key: str) -> ParentSummaryReport:
        """Generate goal/overview/progress summary for a parent ticket."""
        parent_issue = self._client.get_issue(issue_key)
        child_issues = self._fetch_child_issues(issue_key)
        return generate_parent_summary(parent_issue, child_issues)

    def _fetch_child_issues(self, issue_key: str) -> list[Issue]:
        """
        Fetch child issues for an Epic/parent ticket using common Jira JQL patterns.
        Uses conservative fallbacks because field availability differs across projects.
        """
        queries = [
            f'parent = "{issue_key}" ORDER BY priority DESC, updated DESC',
            f'"Epic Link" = "{issue_key}" ORDER BY priority DESC, updated DESC',
            f'parent = "{issue_key}" OR "Epic Link" = "{issue_key}" ORDER BY priority DESC, updated DESC',
        ]

        collected_by_key: dict[str, Issue] = {}
        for jql in queries:
            try:
                issues = self._client.search_issues(jql, max_results=self._settings.default_max_results)
            except Exception:
                continue
            for issue in issues:
                collected_by_key[issue.key] = issue
            if collected_by_key:
                break

        return list(collected_by_key.values())

    def _build_parent_summaries(self, assignee_issues: list[Issue]) -> list[ParentSummaryReport]:
        """
        Build parent summaries for all parent tickets where the user has child tasks
        as assignee (from triage issues) or as reporter.
        """
        reporter_issues = self._fetch_reporter_issues()
        focus_issues = _merge_unique_issues(assignee_issues, reporter_issues)

        parent_keys: set[str] = set()
        for issue in focus_issues:
            parent_key = issue.parent_key or issue.epic_key
            if parent_key:
                parent_keys.add(parent_key)

        summaries: list[ParentSummaryReport] = []
        for parent_key in sorted(parent_keys):
            try:
                parent_issue = self._client.get_issue(parent_key)
            except Exception:
                continue

            child_issues = self._fetch_child_issues(parent_key)
            if not child_issues:
                # Fallback to known issues if child queries are constrained by Jira config.
                child_issues = [
                    issue
                    for issue in focus_issues
                    if issue.parent_key == parent_key or issue.epic_key == parent_key
                ]

            summaries.append(generate_parent_summary(parent_issue, child_issues))

        return summaries

    def _fetch_reporter_issues(self) -> list[Issue]:
        """
        Fetch unresolved tickets reported by current user, to include reporter-owned
        subtask context in parent summaries.
        """
        jql = (
            'reporter = currentUser() AND resolution = Unresolved '
            "ORDER BY priority DESC, updated DESC"
        )
        try:
            return self._client.search_issues(jql, max_results=self._settings.default_max_results)
        except Exception:
            return []


def _merge_unique_issues(primary: list[Issue], secondary: list[Issue]) -> list[Issue]:
    merged: dict[str, Issue] = {issue.key: issue for issue in primary}
    for issue in secondary:
        merged[issue.key] = issue
    return list(merged.values())
