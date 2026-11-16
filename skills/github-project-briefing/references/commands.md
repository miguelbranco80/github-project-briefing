# Run a briefing

Commands run from the skill directory. `WORKSPACE` is the installed workspace;
`STATE` is the returned project directory; `RUN` is an unreviewed completed run.

## Check scope

```sh
python3 scripts/collect.py --repo OWNER/REPO --state-dir STATE --estimate
```

This returns `estimated`, `limit`, `limited` and `since` without collecting evidence.
For a new project, use `WORKSPACE/data/OWNER--REPO` as `STATE`. Pass `--days`,
`--max-prs` and `--pr-filter` to check a proposed scope. GitHub search counts are
estimates; collection also checks the actual result against the budget.

## Collect and review

```sh
python3 scripts/refresh.py --workspace WORKSPACE
```

Each project result contains `state_dir`, collection counts and `pending_runs`.
`needs_scope` means PR or commit collection was incomplete: review the returned
`coverage`, adjust the agreed settings and retry. The checkpoint stays unchanged.
Read each unreviewed run, including any backlog:

```sh
python3 scripts/collect.py --repo OWNER/REPO --state-dir STATE --run RUN
```

This reads the collection window, sampling limits, changed candidates and review
decision from SQLite. Broad collection reads PRs and commits in the scan window,
plus a sample of up to 100 releases. Filtered collection reads matching PRs only.
Full snapshots remain in the database.
Inspect discussions and code for selected stories:

```sh
gh pr view NUMBER --repo OWNER/REPO --comments
gh pr diff NUMBER --repo OWNER/REPO
```

## Save or skip

Write the article as plain Markdown to `STATE/articles/YYYY-MM-DD-run-RUN.md`.
Use a headline, the article date and the prose described in the skill. Include the
observation window from the saved run in the closing coverage note. Create the
articles directory if needed; reuse an existing article for the same run.

Read the completed file, then record it:

```sh
python3 scripts/collect.py --repo OWNER/REPO --state-dir STATE --run RUN --article ARTICLE_PATH
```

When nothing merits an article, instead run:

```sh
python3 scripts/collect.py --repo OWNER/REPO --state-dir STATE --run RUN --reason 'Only routine dependency updates; no relevant behavior change.'
```

Either decision removes the run from `pending_runs`. Repeating the same decision
is safe; a conflicting decision is rejected.

## Recovery

Fix the reported cause and repeat the failed command. Collection keeps the previous
checkpoint on failure. An unrecorded article remains available to finish and save.
To read the queue without GitHub access:

```sh
python3 scripts/collect.py --repo OWNER/REPO --state-dir STATE --pending
```

For a correction, edit the article and date the correction. Inspect the scheduler's
history for failed runs before retrying.
