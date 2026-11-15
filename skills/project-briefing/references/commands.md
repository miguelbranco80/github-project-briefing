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

## Publish or skip

```sh
python3 scripts/journal.py prepare --workspace WORKSPACE --repo OWNER/REPO --run RUN
```

Edit the returned `article`: fill its title and description and write the Markdown
body. Keep the other metadata, which identifies the collected evidence. Diagrams
and requested artwork go under the journal's `src/assets/`; link diagram sources
and supply alt text. Optional covers use `cover`, `coverAlt` and `coverCaption`.

```sh
python3 scripts/journal.py publish --workspace WORKSPACE --repo OWNER/REPO --run RUN
```

Publication builds the project's static site, saves the article path in SQLite
and returns the article’s `html` path, the journal’s `output_dir` and its
self-contained `reader` path. When nothing merits an article, instead run:

```sh
python3 scripts/journal.py skip --workspace WORKSPACE --repo OWNER/REPO --run RUN --reason 'Only routine dependency updates; no relevant behavior change.'
```

This stores the reason in SQLite without creating a Markdown file. Either decision
removes the run from `pending_runs`; retrying returns the saved decision.

## Present the journal

Pass the complete contents of the returned `reader` file unchanged to
`show_widget` as `widget_code`, with `pin: true`, `size: "full"`, the repository
as `title`, and a lowercase `journal-OWNER--REPO` name (at most 64 characters).
Use the same name and session for later updates. Forward file contents through
Code Mode when available instead of copying the HTML through the model.

The reader includes the existing pages, styles and artwork; archive navigation
stays inside the widget. Create it only after an article exists. The static blog
in `OUTPUT_DIR/index.html` remains available for ordinary browsers.

## Recovery

Fix the reported cause and repeat the failed command. Collection keeps the previous
checkpoint on failure; publication keeps the previous site. Existing drafts and
review decisions are reused. To read the queue without GitHub access:

```sh
python3 scripts/collect.py --repo OWNER/REPO --state-dir STATE --pending
```

For a dated correction or requested layout change, edit the existing journal and
rebuild with `python3 assets/journal/build.py STATE/journal`. This preserves article
URLs. Present the rebuilt reader to update the dashboard. Inspect the scheduler's
history for failed runs before retrying.
