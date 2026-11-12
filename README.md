# Project Briefing

An agent template that follows GitHub repositories and maintains an illustrated
engineering blog: source-linked articles, generated covers, a consistent layout
and a dated archive. One daily job handles collection, interpretation and journal
updates. New installations contain no repository configuration or research data.

## Develop and check

Requires Python 3.10+ on POSIX, Node.js/npm, and the OpenClaw CLI. Live collection
uses existing authenticated gh; live covers require an image-generation tool.

~~~sh
npm ci --prefix skills/project-briefing/journal --ignore-scripts --no-audit --no-fund
python3 -m unittest discover -s tests -v
openclaw templates validate .
openclaw templates dev .
openclaw templates build . --out dist/project-briefing-0.2.0.tgz
python3 tests/check_archive.py dist/project-briefing-0.2.0.tgz
~~~

The tests use disposable workspaces and fake GitHub responses. They exercise
collection, recovery, journal preparation/building, archive preservation, failed
builds, idempotent publication and package resource coverage. No live research
or credentials enter the package.

## Ownership

- CLAW.md declares installed files and the single daily job.
- BOOTSTRAP.md starts onboarding; skills/project-briefing/SKILL.md owns the workflow.
- scripts/collect.py owns bounded collection and reporting records; refresh.py
  owns configuration checks, independent refreshes and blocker deduplication.
- scripts/journal.py binds articles to completed runs, initializes each project's
  blog, builds it and records outputs. The journal directory supplies the portable
  site engine, post template, editorial rules and illustration brief.
- [DATA.md](skills/project-briefing/DATA.md) owns the evidence schema and scope.
- [INSTALL.md](INSTALL.md) owns installation/removal; [VERIFICATION.md](VERIFICATION.md)
  records what has actually been tested.

All runtime resources are inside this template. No separate workshop skill,
OCE-specific tracker or development-workspace path is required. Article Markdown
is also the saved briefing: there is no duplicate narrative file to maintain.
Generated outputs live under each project's data directory, not in template source.

## Boundaries

The agent writes and generates art during the scheduled turn; the builder alone
does neither. Code validates the mechanics, not the truth or usefulness of prose.
Quiet polls do not create filler posts. Diagrams are optional and must be grounded
in inspected code or design sources. Portals serve previews; public hosting is
not configured.

Collection covers recent PR metadata/discussions, commits and releases within
explicit budgets. It is not a full source archive, CI monitor, issue tracker or
deployment qualification. See DATA.md for details.

Portable-source updates do not automatically upgrade an already installed agent
or rewrite its existing data. Source/package tests are not proof of successful
installation, scheduler execution, image generation or requester-side rendering.
