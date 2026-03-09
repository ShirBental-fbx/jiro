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
    IssueComment,
    RiskReport,
    StandupReport,
    TriageReport,
)
from src.triage_engine import DEFAULT_JQL, build_triage_report
from src.risk_engine import assess_risks
from src.breakdown_engine import generate_breakdown
from src.comment_engine import draft_comment
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

        return build_triage_report(issues, comments_by_key, self._settings)

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
