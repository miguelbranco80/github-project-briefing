# Configure project briefings

## Project settings (`projects.json`)

Save `projects.json` in the installed workspace. Each project requires only `repo`;
the other fields are optional and shown below with their defaults. Use strict JSON
without comments.

```json
{
  "projects": [
    {
      "repo": "owner/repo",
      "priorities": [],
      "watchlist": [],
      "state_dir": "data/owner--repo",
      "days": 7,
      "max_prs": 100,
      "max_commits": 100,
      "pr_filter": ""
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `priorities` | Reader interests, such as `["query performance", "API changes"]`. Guides story selection. |
| `watchlist` | People whose work the reader wants to follow. Guides story selection. |
| `state_dir` | Storage beneath workspace `data/`. When omitted, derived from `repo` by replacing `/` with `--`. |
| `days` | Days to look back for the first scan or after changing the filter. Must be a positive integer. |
| `max_prs` | Maximum PR candidates per scan. Must be a positive integer; filtered searches are capped at 1,000. |
| `max_commits` | Maximum commits per broad scan. Must be a positive integer. |
| `pr_filter` | Empty: collect PRs, commits and releases. Nonempty: collect only PRs matching GitHub labels, authors or keywords, e.g. `"label:security"`. |

Interests and people guide the agent; only `pr_filter` restricts GitHub collection.
Test a filter's relevance before saving it. Release discovery samples up to 100 releases.

## Project storage

Each project has its own directory:

```text
data/owner--repo/
  activity.sqlite      collection evidence and review decisions
  articles/            dated Markdown briefings
```

SQLite is a local file; it needs no database server. Its `runs` table records each
collection's window, status and sampling limits. A reviewed run has either an
`article_path` or a `review_reason`; a completed run with neither still needs review.
`objects` holds the latest candidate snapshots and `changes` preserves their
history. Each article path belongs to that project.

## Updating project settings

Merge requested changes into `projects.json` atomically, preserving other projects.
A changed filter begins a new baseline;
otherwise collection continues from the previous checkpoint with a 24-hour overlap.
Keep background knowledge in the articles; do not copy these settings into research notes.

## Daily job

After the first briefing, create a daily automation from this conversation:
09:00 in the gateway host's timezone, isolated execution, announce delivery,
and “Run the scheduled project briefing using skills/github-project-briefing/SKILL.md.”
Use the working model, runtime and account and allow the research tools. Leave external
delivery coordinates unset so results return here. Reuse this conversation's
briefing job if setup is repeated. Tell the reader the schedule and timezone.
Check run history for execution and delivery failures before claiming scheduled
updates work.

## Runtime requirements

The execution environment needs Python 3.10+ on POSIX and authenticated `gh`,
in addition to OpenClaw. Report a missing capability specifically.
