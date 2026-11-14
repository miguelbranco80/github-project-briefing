# Project Briefing

An agent template that follows GitHub repositories and maintains an engineering
blog: source-linked articles, a consistent layout and a dated archive. One daily
job handles collection, interpretation and journal updates. New installations
contain no repository configuration or research data.

## Install

Requires Python 3.10+ on POSIX, Node.js/npm, authenticated `gh`, and a working
OpenClaw template Add flow. The agent needs portal access to present the blog;
`screen` is optional for panel display. Image generation is not required.

~~~sh
gh repo clone miguelbranco80/project-briefing-template
cd project-briefing-template
openclaw templates add .
~~~

Add creates an independent agent and one daily job at 09:00 UTC; adding again is
not an upgrade. Open the new agent's chat and send **Get started** if onboarding
does not start automatically. The agent asks which repository to follow and
checks tools, collection scope and daily delivery. Before expensive collection,
it scouts project activity and tries a small sample. For busy repositories it
helps you choose a useful focus and remembers the working research approach.

For a first-run check, ask: **Refresh now, build the journal without decorative
artwork, show the article and report collection, presentation and daily-delivery
readiness.** A second refresh should preserve the archive and only publish when
there are meaningful new developments. Verify the daily job's actual destination
and delivery, not just its existence.

To remove the agent, export any wanted data, then delete it through the UI or run
`openclaw agents delete ACTUAL_AGENT_ID`. This removes its workspace and assigned
automations. Deleting a chat does not uninstall the agent. Source checkouts,
archives, shared credentials and already-delivered reports remain.

## Develop and check

Run from the source checkout with the OpenClaw CLI available:

~~~sh
npm ci --prefix skills/project-briefing/journal --ignore-scripts --no-audit --no-fund
python3 -m unittest discover -s tests -v
openclaw templates validate .
openclaw templates dev .
openclaw templates build . --out dist/project-briefing-0.2.5.tgz
python3 tests/check_archive.py dist/project-briefing-0.2.5.tgz
~~~

The tests use disposable workspaces and fake GitHub responses. They exercise
collection, recovery, journal preparation/building, archive preservation, failed
builds, idempotent publication and package resource coverage. No live research
or credentials enter the package.

## Verification and known limits

Version 0.2.5 passed 47 tests in the source checkout and against the extracted
release archive, including a cold locked dependency install. Template validation
and install preview passed. These checks cover filtered/broad collection, scope changes, old-database
compatibility, limits and recovery, text-only publication, optional assets, draft rejection, archive preservation,
local links and package resources; they do not certify editorial quality.

A live scheduled run collected evidence and built a text-only article, but
presentation and notification failed: the scheduled turn lacked portal authority
and its `channel: last` delivery had no destination. Those runtime blockers remain
unresolved. Fresh-agent installation, notification routing, setup/scheduler races,
portal recovery after restart and requester-side desktop/mobile rendering still
need end-to-end verification.

The tested 2026.11.5-beta.1 CLI also had an Add defect: it required a stopped
Gateway, then contacted that Gateway to create the job. This template does not
fix that runtime issue. If Add partially succeeds, inspect the agent and job
before retrying; do not stop the Gateway just to repeat the same failing command.

## Ownership

- CLAW.md declares installed files and the single daily job.
- BOOTSTRAP.md owns the first conversation: introduction, repository selection,
  readiness explanation and handoff. skills/project-briefing/SKILL.md owns shared
  configuration rules, ongoing operation and targeted recovery; it does not
  repeat onboarding on ordinary or scheduled runs.
- scripts/collect.py owns workload estimates, optional PR search filtering,
  bounded collection and reporting records; refresh.py owns configuration checks,
  independent refreshes and blocker deduplication.
- scripts/journal.py binds articles to completed runs, initializes each project's
  blog, builds it and records outputs. The journal directory supplies the portable
  site engine, post template, editorial rules and optional one-off artwork guide.
- [DATA.md](skills/project-briefing/DATA.md) owns the evidence schema and scope.

All runtime resources are inside this template. No separate workshop skill,
OCE-specific tracker or development-workspace path is required. Article Markdown
is also the saved briefing: there is no duplicate narrative file to maintain.
Generated outputs live under each project's data directory, not in template source.

## Boundaries

The requesting agent owns research, writing, publication and presentation;
optional helpers return bounded evidence reviews. The builder does not write
articles or generate art. Code validates the mechanics, not the truth or
usefulness of prose. The editorial guide calls for engineering stories explaining
problems, mechanisms, trade-offs and consequences, not PR inventories. The starter
is deliberately unpublished until its draft marker is removed after writing.
Quiet polls do not create filler posts. Diagrams are optional and must be grounded
in inspected code or design sources. Portals serve previews; public hosting is
not configured.

Broad collection covers recent PR metadata/discussions, commits and releases
within explicit budgets. An optional saved pr_filter restricts collection to
matching PRs and their discussions, excluding repository-wide commits/releases.
It is not a full source archive, CI monitor, issue tracker or
deployment qualification. See [DATA.md](skills/project-briefing/DATA.md) for details.

Portable-source updates do not automatically upgrade an already installed agent
or rewrite its existing data. Source/package tests are not proof of successful
installation, scheduler execution or requester-side rendering.
