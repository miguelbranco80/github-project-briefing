# Project Briefing — local prototype

See [INSTALL.md](INSTALL.md) for the exact local installation, first-run checks, and removal procedure.

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

The selected skill files, BOOTSTRAP.md, and manifest/package metadata enter the archive. No GitHub evidence, credentials, or personal settings belong in a published package. The local package scope is provisional, not a registry identity.

## Current boundaries

- Seven-day initial window of updated PRs and default-branch commits; subsequent scans overlap the last successful start by 24 hours. Dormant open PRs are excluded until updated.
- PR discovery stops above 100 recent PRs before conversation fetching. --days narrows only the initial window; --max-prs explicitly changes the PR ceiling. No silent truncation or automatic escalation.
- Each paginated evidence stream is capped at 1,000 records, including releases, commits, PR comments, reviews, and paths. Overflow fails the scan without advancing a checkpoint. This is a bounded briefing collector, not a complete archive.
- Current releases are compared each run, including edits to old releases and unpublished drafts.
- Atomic SQLite record/checkpoint commits, 24-hour overlap, per-state writer lock, read-only GitHub API calls and bounded transient HTTP retries.
- No automatic interpretation of acceptance, authority, implementation relationships or deployment.
- No ordinary-issue/GitHub-Discussion collection, CI collection, RFC document snapshots, role roster discovery, full historical reconciliation or automatic notification receipt verification. Per-run output records separate unbriefed work from pending/uncertain delivery; saved briefings are never automatically regenerated or resent.
- Incremental PR caching relies on GitHub updated_at and head SHA. Reconcile re-fetches recent and previously tracked open records within the same budget; old closed discussions and deleted releases are not fully reconciled.
- Live collection is not a transactional snapshot; report its timestamps and limitations.
- An earlier version was trial-installed; this source revision has not been applied to that agent. No dashboard is included.

## First-run and daily workflow

Template Add creates a dedicated agent and workspace, opens its chat, and sends the initial message. BOOTSTRAP.md delegates to the skill: introduce the service, then ask for a repository. Priorities and watchlists are optional; cadence defaults to daily at 09:00 UTC. Configuration is saved in workspace projects.json, so isolated daily runs do not depend on chat history. The manifest declares one daily job with last-channel delivery. Verify the installed job state and delivery before claiming monitoring is active.

No repository is configured in the package. Before onboarding, scheduled runs stay quiet. Installation/onboarding, last-channel delivery, and scheduler execution still need end-to-end testing.

## Data and daily execution

[DATA.md](skills/project-briefing/DATA.md) documents collection and storage. No patch or source-file endpoint is fetched by default. Old stored evidence is preserved, not silently erased.

The daily skill invokes scripts/refresh.py with --workspace WORKSPACE. This validates configuration before collection, skips absent/empty setup, suppresses unchanged blockers and reports recovery. It does not configure the scheduler or prove notification delivery.
