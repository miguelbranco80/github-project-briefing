# Local records

Each project's state directory contains activity.sqlite and Markdown reports.
Workspace refresh.sqlite stores blocker signatures only. projects.json owns
project preferences and approved collection budgets. No credentials belong here.

## Schema

| Table | Purpose |
|---|---|
| runs | Repository, start/end, coverage start, complete/failed state and error |
| objects | Latest source payload by repository, kind and GitHub ID |
| changes | Immutable per-run before/after payloads |
| run_outputs | Saved briefing path and delivery status, independently of collection |

Use parameterized queries; restrict by repository and run. For example:

```sql
SELECT kind,key,before_json,after_json FROM changes WHERE run_id=?;
SELECT kind,key,payload FROM objects WHERE repo=? AND kind='pr' AND key=?;
SELECT id,since,started,finished,status,error FROM runs WHERE repo=? ORDER BY id DESC;
```

PR payloads contain pr (API metadata and description), comments (issue comments)
and reviews (review summaries). review_comments is empty for compatibility.
No /files or inline-diff endpoint is fetched. Commits come from the commit-list
endpoint, not commit-detail patches. Release payloads include release notes.
Old databases may still contain files/patches from earlier versions; updating the
collector does not erase historical evidence.

Source discussions can themselves quote code. Lightweight collection is not a
guarantee that no user-written code appears in a payload.

The collector does not inventory dormant open PRs, ordinary issues, GitHub
Discussions, CI, RFC contents, deployment proof or verified maintainer rosters.
A merged PR is not proof of acceptance or deployment. Interpretations and role
evidence belong in linked briefings; no inferred authority is stored as fact.

Complete scans commit sources and checkpoint atomically. Failed scans preserve
the previous checkpoint. Ledgers regenerate from immutable deltas; a saved
briefing removes a run from the writing queue. Pending/uncertain delivery remains
separate and must not automatically resend already-written reports.
