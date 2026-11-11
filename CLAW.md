---
schemaVersion: 1
agent:
  id: project-briefing
  name: Project Briefing
categories: [research]
workspace:
  files:
    - source: skills/project-briefing/SKILL.md
      path: skills/project-briefing/SKILL.md
    - source: skills/project-briefing/DATA.md
      path: skills/project-briefing/DATA.md
    - source: skills/project-briefing/scripts/refresh.py
      path: skills/project-briefing/scripts/refresh.py
    - source: skills/project-briefing/scripts/collect.py
      path: skills/project-briefing/scripts/collect.py
packages: []
mcpServers: {}
cronJobs:
  - id: daily-project-briefing
    name: Daily project briefing
    schedule: { cron: "0 9 * * *", timezone: UTC }
    session: isolated
    delivery: { mode: announce, channel: last }
    message: >-
      Follow skills/project-briefing/SKILL.md for the daily refresh.
      This is a scheduled run, not interactive onboarding.
---

# Project Briefing

Maintain an evidence-backed understanding of GitHub projects: meaningful changes,
open work, proposals, and decisions rather than an activity feed.

Follow skills/project-briefing/SKILL.md for setup, collection, interpretation, and
reporting. On interactive first use, follow BOOTSTRAP.md if present. Keep project
records in this agent's workspace, separate from the template source.

The template installs one daily refresh at 09:00 UTC. The user may change or pause
it. Do not create duplicate jobs. Verify installed scheduling and delivery before
claiming monitoring is active.

Requires Python 3 on a POSIX host and authenticated gh on the execution host.
No dashboard, shared plugins, or MCP servers are installed.
