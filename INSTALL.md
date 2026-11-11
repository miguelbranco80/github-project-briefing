# Install Project Briefing locally

This is a local experimental template. Nothing needs publishing to ClawHub.

## Add once

On the Gateway host, run:

```sh
gh repo clone miguelbranco80/project-briefing-template
cd project-briefing-template
openclaw templates add .
```

Keep the agent ID printed by Add. Adding again creates another agent and another daily job; it does not upgrade the first one. The archive in `dist/` is an alternative portable source.

The Control UI Add flow opens the new agent chat and sends its first message. CLI Add does not promise to open a browser or start a conversation: select the new **Project Briefing** agent in OpenClaw and send `Get started` if needed. BOOTSTRAP.md directs its first reply to ask which repository to follow. Reply with `owner/repo`; priorities and people to watch are optional. No data from this development conversation is included.

The agent saves projects.json, collects a baseline and writes briefings in its own workspace. The bundled automation defaults to daily at 09:00 UTC. Before calling setup complete, ask it to verify the installed job's enabled state and destination. Last-channel notification delivery needs checking in your installed agent; a declared schedule alone does not prove delivery. If Add reports a partial result, inspect that agent and automation rather than repeating Add.

Requires Python 3 and an authenticated GitHub CLI accessible to the new agent's execution host. Access in the developer workspace does not prove a sandboxed agent has the same access. Collection follows recent activity rather than the entire open backlog. Above 100 recently updated PRs it stops during discovery, before conversations. A smaller initial window can be chosen with --days; the agent must not raise budgets automatically. Large repositories may still exceed the recent-activity budget. Each paginated evidence stream is also capped at 1,000 records.

## Before setup and on failures

The daily job exists immediately after Add. With no configured repositories it must stay quiet and skip collection and onboarding. Interactive setup activates monitoring by saving projects.json; no second job is needed. Invalid configuration or missing GitHub access produces one actionable warning, with unchanged blockers suppressed through automation scratch and retried on the next daily run. These lifecycle behaviours are agent instructions, not deterministic collector guards; scheduled execution and deduplication still require end-to-end verification.

## Check it

Ask: `Refresh now, show collection coverage and the daily job's enabled state and delivery destination.` Then ask `Refresh again; report only meaningful changes since the previous briefing.`

The initial repo question is an agent instruction, not a mandatory UI wizard. It can be corrected conversationally. The collector has focused tests and a live smoke test; fresh-agent onboarding and scheduled notification delivery have not been verified end to end.

## Remove it

Use the new agent's delete action, or on the Gateway host:

```sh
openclaw agents delete ACTUAL_AGENT_ID
```

Use the ID printed at Add, not a session/chat ID. Deleting only a chat is not uninstalling the agent. Ordinary agent deletion removes its dedicated workspace (including projects.json, SQLite evidence, briefings and local skills) and its assigned automations, including files added there later. Export anything you want to keep first.

This package installs no shared plugins or MCP servers and does not alter GitHub authentication. Those shared settings remain. The development source, built archive, separate smoke-test data and any reports already delivered elsewhere remain; deleting the agent is not an erase-every-copy operation.
