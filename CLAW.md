---
schemaVersion: 1
agent:
  id: project-briefing
  name: Project Briefing
categories: [research]
workspace:
  files:
    - source: skills/project-briefing/DATA.md
      path: skills/project-briefing/DATA.md
    - source: skills/project-briefing/SKILL.md
      path: skills/project-briefing/SKILL.md
    - source: skills/project-briefing/journal/ILLUSTRATIONS.md
      path: skills/project-briefing/journal/ILLUSTRATIONS.md
    - source: skills/project-briefing/journal/README.md
      path: skills/project-briefing/journal/README.md
    - source: skills/project-briefing/journal/STYLE.md
      path: skills/project-briefing/journal/STYLE.md
    - source: skills/project-briefing/journal/build.py
      path: skills/project-briefing/journal/build.py
    - source: skills/project-briefing/journal/eleventy.config.cjs
      path: skills/project-briefing/journal/eleventy.config.cjs
    - source: skills/project-briefing/journal/package-lock.json
      path: skills/project-briefing/journal/package-lock.json
    - source: skills/project-briefing/journal/package.json
      path: skills/project-briefing/journal/package.json
    - source: skills/project-briefing/journal/src/_includes/base.njk
      path: skills/project-briefing/journal/src/_includes/base.njk
    - source: skills/project-briefing/journal/src/_includes/post.njk
      path: skills/project-briefing/journal/src/_includes/post.njk
    - source: skills/project-briefing/journal/src/about.md
      path: skills/project-briefing/journal/src/about.md
    - source: skills/project-briefing/journal/src/archive.njk
      path: skills/project-briefing/journal/src/archive.njk
    - source: skills/project-briefing/journal/src/assets/favicon.svg
      path: skills/project-briefing/journal/src/assets/favicon.svg
    - source: skills/project-briefing/journal/src/assets/style.css
      path: skills/project-briefing/journal/src/assets/style.css
    - source: skills/project-briefing/journal/src/index.njk
      path: skills/project-briefing/journal/src/index.njk
    - source: skills/project-briefing/journal/src/posts/posts.json
      path: skills/project-briefing/journal/src/posts/posts.json
    - source: skills/project-briefing/journal/templates/post.md
      path: skills/project-briefing/journal/templates/post.md
    - source: skills/project-briefing/scripts/collect.py
      path: skills/project-briefing/scripts/collect.py
    - source: skills/project-briefing/scripts/journal.py
      path: skills/project-briefing/scripts/journal.py
    - source: skills/project-briefing/scripts/refresh.py
      path: skills/project-briefing/scripts/refresh.py
packages: []
mcpServers: {}
cronJobs:
  - id: daily-project-briefing
    name: Daily project briefing
    schedule: { cron: "0 9 * * *", timezone: UTC }
    session: isolated
    delivery: { mode: announce, channel: last }
    message: >-
      Follow skills/project-briefing/SKILL.md to refresh evidence, publish the journal and deliver its link.
      This is a scheduled run, not interactive onboarding.
---

# Project Briefing

Maintain an evidence-backed understanding of GitHub projects: meaningful changes,
open work, proposals, and decisions in a source-linked engineering journal.

For first-time interactive onboarding, follow BOOTSTRAP.md if present. Follow
skills/project-briefing/SKILL.md for configuration rules, collection,
interpretation, publication, delivery and recovery. Keep project records in this
agent's workspace, separate from the template source.

The template installs one daily refresh at 09:00 UTC. The user may change or pause
it. Do not create duplicate jobs. Verify installed scheduling and delivery before
claiming monitoring is active.

Requires Python 3.10+ on POSIX, Node.js/npm, authenticated gh and portal access
on the requesting agent. Preview uses a static-site portal, not a dashboard.
No shared plugins or MCP servers are installed.
