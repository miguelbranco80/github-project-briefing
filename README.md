# GitHub Project Briefing

Follow a GitHub project through source-linked engineering briefings. The agent
researches code changes, proposals and discussions, explains what matters to you,
and answers follow-up questions in chat. GitHub access is read-only.

## Start

Requires an OpenClaw source build with Templates enabled and a connected model.
The gateway host needs Python 3.10+ on POSIX and authenticated `gh` with access to
the repositories you want to follow.

```sh
openclaw templates add @miguelbranco80/github-project-briefing
```

Open the new agent's chat and name a repository. For example:

> Follow openclaw/openclaw. I'm interested in agent templates and automation.

The agent checks recent activity, agrees a useful scope with you and writes the
first briefing. Setup then enables daily research at 09:00 in the gateway host's
timezone. Keep the gateway running for scheduled research. New findings and a
link to the saved article appear in the setup chat; runs with no news stay quiet.

Ask follow-up questions there, such as “What changed since the last briefing?”
or “Explain the automation changes in more detail.”

## How it works

The agent collects PRs, commits and releases within the agreed scope, then reads
the relevant code and discussions to turn related changes into stories. Each
briefing links its sources and distinguishes shipped changes from proposals.

Each project keeps its evidence and review history in `activity.sqlite` and its
dated Markdown briefings in `articles/`, inside its own workspace folder.
Earlier articles remain available for follow-up questions. No database server
or website is required.

[Workflow](https://github.com/miguelbranco80/github-project-briefing/blob/main/skills/github-project-briefing/SKILL.md)
and [configuration](https://github.com/miguelbranco80/github-project-briefing/blob/main/skills/github-project-briefing/references/configuration.md).

## Development

From the [source repository](https://github.com/miguelbranco80/github-project-briefing):

```sh
gh repo clone miguelbranco80/github-project-briefing
cd github-project-briefing
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
openclaw templates validate .
openclaw templates dev .
mkdir -p dist
openclaw templates build . --out dist/github-project-briefing.tgz
python3 tests/check_archive.py dist/github-project-briefing.tgz
```

Tests use fake GitHub responses and exercise SQLite history, review
decisions, collection limits, saved articles and project isolation.

## License

[MIT](https://github.com/miguelbranco80/github-project-briefing/blob/main/LICENSE).
