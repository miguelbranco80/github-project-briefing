# Project Briefing

An OpenClaw agent that researches GitHub projects and saves source-linked
engineering articles. Each project keeps its evidence and articles in its own folder.

## Start

Requires an OpenClaw source build with `templates`, Python 3.10+ on POSIX,
and authenticated `gh`.

```sh
gh repo clone miguelbranco80/project-briefing-template
cd project-briefing-template
openclaw templates add .
```

Name a repository and what interests you. The agent researches it, saves the first
article and discusses the findings in chat. Setup enables daily research at 09:00
in the gateway host's timezone. New briefings appear in the same chat; ask follow-up
questions there. Runs with no news stay quiet.

## How it works

1. Check workload, agree scope and collect evidence into the project's `activity.sqlite`.
2. Review unreviewed collections and research the changes that matter.
3. Save a Markdown article in `articles/`, or record why none is needed in SQLite.
4. Read and discuss saved articles in chat.

Collection and review bookkeeping stays in SQLite; articles stay in Markdown.

[SKILL.md](skills/project-briefing/SKILL.md) owns the workflow;
[BOOTSTRAP.md](BOOTSTRAP.md) points to its setup section. See
[configuration](skills/project-briefing/references/configuration.md) for project
settings and storage, and [commands](skills/project-briefing/references/commands.md)
for operation. Source changes take effect when installed in an agent.

## Verify

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
openclaw templates validate .
openclaw templates dev .
mkdir -p dist
openclaw templates build . --out dist/project-briefing.tgz
python3 tests/check_archive.py dist/project-briefing.tgz
```

Tests use fake GitHub responses and exercise SQLite history, review
decisions, collection limits, saved articles and project isolation.

## License

[MIT](LICENSE).
