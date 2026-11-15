# Project Briefing

An OpenClaw agent that researches GitHub projects and publishes source-linked
engineering articles. Each project keeps its evidence and journal in its own folder.

## Start

Requires Python 3.10+ on POSIX, Node.js 20.19+, authenticated `gh`.

```sh
gh repo clone miguelbranco80/project-briefing-template
cd project-briefing-template
openclaw templates add .
```

Name a repository and what interests you. The agent researches the project,
produces the first briefing and confirms the daily follow-up. The template includes
one job at 09:00 UTC; notification delivery is handled by OpenClaw.

## How it works

1. Check workload, agree scope and collect evidence into the project's `activity.sqlite`.
2. Review unreviewed collections and research the changes that matter.
3. Write an article in `journal/src/posts/`, or record why none is needed in SQLite.
4. Build the project's static HTML journal in `journal/_site/`; open `index.html` to browse it.

Collection and review bookkeeping stays in SQLite. Existing `run-N.md` and
`quiet-N.md` notes are imported before removal; articles and evidence are preserved.

[SKILL.md](skills/project-briefing/SKILL.md) owns the workflow;
[BOOTSTRAP.md](BOOTSTRAP.md) points to its setup section. See
[configuration](skills/project-briefing/references/configuration.md) for project
settings and storage, and [commands](skills/project-briefing/references/commands.md)
for operation. Source changes take effect when installed in an agent.

## Verify

```sh
npm ci --prefix skills/project-briefing/assets/journal --ignore-scripts --no-audit --no-fund
python3 -m unittest discover -s tests -v
openclaw templates validate .
openclaw templates dev .
openclaw templates build . --out dist/project-briefing-0.2.5.tgz
python3 tests/check_archive.py dist/project-briefing-0.2.5.tgz
```

Tests use fake GitHub responses and exercise SQLite history, migration, review
decisions, collection limits, article builds and project isolation. Verify installation,
file preview and scheduled delivery in the target OpenClaw environment.
