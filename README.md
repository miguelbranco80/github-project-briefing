# Project Briefing — local prototype

Portable source; real monitoring state belongs outside this directory. Python 3 stdlib and an already authenticated GitHub CLI are required. The collector supports POSIX file locking.

## Try without installing an agent

```sh
python3 skills/project-briefing/scripts/collect.py --repo OWNER/REPOSITORY --state-dir /absolute/private/state
python3 -m unittest discover -s tests -v
```

Read the generated run-N.md and follow the skill to produce an interpretive briefing from SQLite evidence. Refresh with the same command. Use --reconcile to bypass the PR-detail cache. Multiple projects use separate state directories.

## Package

```sh
openclaw templates validate .
openclaw templates dev .
openclaw templates build . --out /tmp/project-briefing-0.1.0.tgz
```

Only the two explicitly selected skill files and manifest/package metadata enter the archive. No GitHub evidence, credentials, or personal settings belong in a published package. The local package scope is provisional, not a registry identity.

## Current boundaries

- Complete current open-PR inventory; seven-day initial updated-closed-PR window; default-branch commits and releases in the window.
- Paginated PR issue comments, reviews, inline comments and paths; GitHub's 3,000-file PR cap is a hard coverage failure.
- Atomic SQLite record/checkpoint commits, 24-hour overlap, per-state writer lock, read-only GitHub API calls and bounded transient HTTP retries.
- No automatic interpretation of acceptance, authority, implementation relationships or deployment.
- No ordinary-issue/GitHub-Discussion collection, CI collection, RFC document snapshots, role roster discovery, full historical reconciliation or delivery acknowledgements.
- Incremental PR caching relies on GitHub updated_at and head SHA. Reconcile re-fetches open/recent records; old closed discussions and deleted releases are not fully reconciled.
- Live collection is not a transactional snapshot; report its timestamps and limitations.
- No installed agent, scheduler, dashboard or publication. Template Add/onboarding remain to be tested separately.
