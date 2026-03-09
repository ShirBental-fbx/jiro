# Jiro

A local, CLI-first Jira workflow assistant for backend and infrastructure engineers.

Jiro helps you cut through Jira noise and answer the questions that matter every day:

- What should I work on today?
- Which tickets are blocked?
- Which tickets are stale or risky?
- What needs clarification before I start?
- What should I write as a Jira comment?
- What should I say in standup?

## Design Principles

- **Read-only** — Jiro never modifies Jira. It reads data and produces analysis.
- **CLI-first** — This is a terminal tool. No web UI, no database.
- **Heuristic-based** — v1 uses rules and text analysis, not LLMs. It works offline.
- **Modular** — Clean separation between API client, business logic engines, and presentation.
- **Extensible** — Designed so LLM integration can be added in v2 without rewriting.

## Installation

```bash
cd jiro
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Jira credentials
```

### Configuration

Create a `.env` file (or set environment variables):

| Variable | Required | Description |
|---|---|---|
| `JIRA_BASE_URL` | Yes | Your Jira Cloud URL (e.g. `https://yourco.atlassian.net`) |
| `JIRA_EMAIL` | Yes | Your Jira account email |
| `JIRA_API_TOKEN` | Yes | [Jira API token](https://id.atlassian.com/manage-profile/security/api-tokens) |
| `JIRO_STALE_DAYS` | No | Days before a ticket is considered stale (default: 5) |
| `JIRO_DEFAULT_MAX_RESULTS` | No | Max issues returned by JQL queries (default: 20) |

## Usage

### Daily Triage

```bash
# Triage your open issues
python cli.py triage

# Triage with custom JQL
python cli.py triage --jql "project = INFRA AND assignee = currentUser() AND resolution = Unresolved"
```

Shows: priority summary, blockers, stale tickets, suggested next actions.

### Risk Assessment

```bash
python cli.py risk PROJ-123
```

Flags: vague descriptions, missing acceptance criteria, unclear dependencies, stale tickets, missing owners, oversized scope.

### Ticket Breakdown

```bash
python cli.py breakdown PROJ-123
```

Generates: implementation plan, suggested subtasks, technical risks, missing information, clarification questions.

### Comment Drafting

```bash
# Status update
python cli.py draft-comment PROJ-123 --type status-update

# Blocker update
python cli.py draft-comment PROJ-123 --type blocker-update

# Clarification request
python cli.py draft-comment PROJ-123 --type clarification-request

# Ready for review
python cli.py draft-comment PROJ-123 --type ready-for-review
```

Produces copy-paste-ready Jira comments with placeholders for details you fill in.

### Standup Summary

```bash
python cli.py standup

# With custom JQL
python cli.py standup --jql "project = INFRA AND assignee = currentUser() AND resolution = Unresolved"
```

Generates: Yesterday / Today / Blockers from your recent Jira activity.

## Architecture

```
CLI (cli.py)
  └─ JiroAgent (orchestration)
       ├─ JiraClient (API communication, response normalization)
       └─ Engines (pure business logic)
            ├─ triage_engine    — daily prioritization
            ├─ risk_engine      — ticket quality/risk detection
            ├─ breakdown_engine — implementation planning
            ├─ comment_engine   — comment draft generation
            └─ standup_engine   — standup report generation
  └─ Presenters (Rich-based terminal output)
```

Key boundaries:
- Engines are stateless — models in, models out. No API calls.
- Client handles all Jira communication and normalizes responses into Pydantic models.
- Presenters handle formatting only. No data fetching or logic.
- Agent composes client + engines. It is the single entry point for all features.

## Running Tests

```bash
python -m pytest tests/ -v
```

Tests use synthetic Jira data — no live Jira connection required.

## v1 Limitations

- **Read-only** — Cannot create/update tickets or add comments (by design).
- **Heuristic-based** — Text analysis uses keyword matching, not semantic understanding. Works well for common patterns, may miss nuanced cases.
- **No caching** — Every command makes fresh API calls. Repeated triage runs fetch all data again.
- **No persistent state** — Cannot track changes between runs or show deltas.
- **Single user** — Designed for individual use, not team-wide analysis.
- **ADF parsing** — Jira's Atlassian Document Format is converted to plain text via a basic recursive extractor. Complex formatting may lose structure.

## Recommended v2 Improvements

1. **LLM integration** — Replace heuristic engines with LLM-backed analysis using the prompt templates in `prompts/`. The engine interface stays the same.
2. **Local caching** — Cache Jira responses (SQLite or flat files) to reduce API calls and enable delta tracking.
3. **Write support** — Add comment posting, status transitions (with explicit confirmation prompts).
4. **Team view** — Expand beyond single-user to team workload analysis.
5. **Watch mode** — Continuous monitoring with notifications for blocker changes or stale tickets.
6. **Custom heuristics** — User-configurable rules for what counts as "blocked", "stale", or "risky".

## Dependencies

- Python 3.9+
- requests
- pydantic
- python-dotenv
- rich
- pytest (dev)
