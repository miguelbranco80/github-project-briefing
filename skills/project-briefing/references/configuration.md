# Configure the journal

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
  journal/
    drafts/            Markdown articles being written
    src/posts/         published Markdown articles
    src/assets/        styles and artwork
    _site/             generated static HTML
```

SQLite is a local file; it needs no database server. Its `runs` table records each
collection's window, status and sampling limits. A reviewed run has either an
`article_path` or a `review_reason`; a completed run with neither still needs review.
`objects` holds the latest candidate snapshots and `changes` preserves their
history. The renderer is shared; project data and journals are separate.

## Updating project settings

Merge requested changes into `projects.json` atomically, preserving other projects. Agree changes to
focus or budgets with the reader. A changed filter begins a new baseline;
otherwise collection continues from the previous checkpoint with a 24-hour overlap.
Keep background knowledge in the journal; do not copy these settings into research notes.

## Schedule and delivery

Reuse the installed daily job. Confirm its schedule and configure notification
delivery to the destination agreed with the reader; OpenClaw installs template
jobs without channel delivery. Check the scheduler's history for delivery results.

## Runtime requirements

The execution environment needs Python 3.10+ on POSIX, Node.js 20.19+, authenticated
`gh`. Report a missing capability specifically.
