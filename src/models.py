from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Jira domain models
# ---------------------------------------------------------------------------

class Issue(BaseModel):
    key: str
    summary: str
    status: str
    priority: str = "Medium"
    assignee: str | None = None
    reporter: str | None = None
    issue_type: str = "Task"
    description: str = ""
    labels: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    created: datetime | None = None
    updated: datetime | None = None
    resolution: str | None = None
    parent_key: str | None = None
    epic_key: str | None = None
    subtask_keys: list[str] = Field(default_factory=list)
    linked_issue_keys: list[str] = Field(default_factory=list)
    story_points: float | None = None
    sprint_name: str | None = None

    @property
    def has_description(self) -> bool:
        return bool(self.description and self.description.strip())

    @property
    def description_length(self) -> int:
        return len(self.description.strip()) if self.description else 0


class IssueComment(BaseModel):
    id: str
    author: str
    body: str
    created: datetime


# ---------------------------------------------------------------------------
# Triage models
# ---------------------------------------------------------------------------

class PrioritySummaryItem(BaseModel):
    issue_key: str
    summary: str
    priority: str
    status: str
    days_since_update: int
    has_blockers: bool


class BlockerItem(BaseModel):
    issue_key: str
    summary: str
    signal: str
    source: Literal["status", "description", "comment"]


class StaleTicketItem(BaseModel):
    issue_key: str
    summary: str
    days_since_update: int
    status: str


class SuggestedAction(BaseModel):
    issue_key: str
    action: str
    reason: str
    urgency: Literal["high", "medium", "low"] = "medium"


class TriageReport(BaseModel):
    generated_at: datetime = Field(default_factory=datetime.now)
    total_issues: int
    priority_summary: list[PrioritySummaryItem] = Field(default_factory=list)
    blockers: list[BlockerItem] = Field(default_factory=list)
    stale_tickets: list[StaleTicketItem] = Field(default_factory=list)
    suggested_actions: list[SuggestedAction] = Field(default_factory=list)
    workflow_health: WorkflowHealthReport | None = None
    parent_summaries: list[ParentSummaryReport] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Workflow health models
# ---------------------------------------------------------------------------

class WorkOrigin(str, Enum):
    PRODUCT_EPIC = "product_epic"
    BUG_PRODUCTION = "bug_production"
    ADHOC_ENGINEERING = "adhoc_engineering"
    UNKNOWN = "unknown"


class OrphanTaskItem(BaseModel):
    issue_key: str
    summary: str
    issue_type: str


class WorkOriginBreakdownItem(BaseModel):
    origin: WorkOrigin
    count: int


class WorkflowHealthReport(BaseModel):
    product_coverage_pct: float
    orphan_tasks: list[OrphanTaskItem] = Field(default_factory=list)
    work_origin_breakdown: list[WorkOriginBreakdownItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Risk models
# ---------------------------------------------------------------------------

class RiskType(str, Enum):
    VAGUE_DESCRIPTION = "vague_description"
    MISSING_ACCEPTANCE_CRITERIA = "missing_acceptance_criteria"
    UNCLEAR_DEPENDENCY = "unclear_dependency"
    STALE_TICKET = "stale_ticket"
    MISSING_OWNER = "missing_owner"
    OVERSIZED_SCOPE = "oversized_scope"


class RiskSeverity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskFinding(BaseModel):
    risk_type: RiskType
    severity: RiskSeverity
    explanation: str
    recommended_action: str


class RiskReport(BaseModel):
    issue_key: str
    summary: str
    findings: list[RiskFinding] = Field(default_factory=list)

    @property
    def has_risks(self) -> bool:
        return len(self.findings) > 0

    @property
    def highest_severity(self) -> RiskSeverity | None:
        if not self.findings:
            return None
        order = {RiskSeverity.HIGH: 0, RiskSeverity.MEDIUM: 1, RiskSeverity.LOW: 2}
        return min(self.findings, key=lambda f: order[f.severity]).severity


# ---------------------------------------------------------------------------
# Breakdown models
# ---------------------------------------------------------------------------

class Subtask(BaseModel):
    title: str
    description: str = ""
    category: str = ""


class BreakdownReport(BaseModel):
    issue_key: str
    summary: str
    implementation_plan: list[str] = Field(default_factory=list)
    suggested_subtasks: list[Subtask] = Field(default_factory=list)
    technical_risks: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Comment draft models
# ---------------------------------------------------------------------------

class CommentType(str, Enum):
    STATUS_UPDATE = "status-update"
    BLOCKER_UPDATE = "blocker-update"
    CLARIFICATION_REQUEST = "clarification-request"
    READY_FOR_REVIEW = "ready-for-review"


class CommentDraft(BaseModel):
    issue_key: str
    comment_type: CommentType
    body: str


# ---------------------------------------------------------------------------
# Standup models
# ---------------------------------------------------------------------------

class StandupItem(BaseModel):
    issue_key: str
    summary: str
    detail: str = ""


class StandupReport(BaseModel):
    generated_at: datetime = Field(default_factory=datetime.now)
    yesterday: list[StandupItem] = Field(default_factory=list)
    today: list[StandupItem] = Field(default_factory=list)
    blockers: list[StandupItem] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Parent summary models
# ---------------------------------------------------------------------------

class ParentSummaryReport(BaseModel):
    parent_key: str
    parent_summary: str
    goal: str
    overview: str
    health: str
    progress: list[str] = Field(default_factory=list)
