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
article and discusses the findings in chat. Setup enables a quiet daily job at
09:00 UTC. Ask “what changed since we last talked?” to catch up on saved articles.

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
decisions, collection limits, saved articles and project isolation. Verify installation
and scheduled updates in the target OpenClaw environment.

The previous HTML blog implementation is preserved at tag `v0.2.6-blog`.

## Release

Build releases from a clean checkout. CI validates the template and tests the
built archive on pushes and pull requests, using a pinned OpenClaw source revision.

For the first ClawHub release, sign in as `miguelbranco80` and publish the verified
archive with `clawhub package publish ./dist/project-briefing.tgz --family template --display-name "Project Briefing" --wait`.
After publication, configure ClawHub trusted publishing for this repository's
`release.yml`. For later releases,
bump `package.json`'s version and manually run **Verify and release** on `main`
with **Publish this version to ClawHub** enabled. Ordinary pushes never publish.

## License

[MIT](LICENSE).
