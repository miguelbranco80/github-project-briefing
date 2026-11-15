---
name: project-briefing
description: Research GitHub projects and publish engineering briefings explaining meaningful changes, decisions and open work.
---

# Project briefing

Help the reader understand engineering work they would otherwise have to piece
together from code and discussion. GitHub access is read-only.

## Setup

For a new journal, find out which GitHub project the reader wants to follow and
what interests them. Look at recent work before recommending a focus. If they have
no preference, choose a useful starting point and explain it. Check the
[workload](references/commands.md#check-scope) before collecting. For a busy repository,
use recent work and the reader's interests to recommend a focus or budget; agree
meaningful trade-offs with them.

Save the repository and interests using [configuration.md](references/configuration.md),
then follow Research, Write and Finish below for the first briefing. Use the same
reference for later repository, focus or schedule changes.

## Research

Read the interests in `projects.json` and the project's previous articles. Follow
[Collect and review](references/commands.md#collect-and-review) to collect candidates
and read unreviewed runs from SQLite. Continue within the saved agreement.
If collection returns `needs_scope`, explain the limit and recommend an adjustment;
resume after agreement. The collector retains the unfinished window.

Choose the changes that matter to this reader. Read their discussions and the
relevant code or design. Follow related work back to the underlying problem;
check dates and earlier coverage before treating something as news.

## Write

Explain the problem, mechanism, trade-off and practical consequence in connected
prose. Use a specific headline and concrete examples. Link inspected evidence next
to the claims it supports. Distinguish proposed work, accepted designs, merged
implementations and verified deployments; attribute opinions and reported tests.

Before publishing, check that the reader can understand what changed and why it
matters. Remove unsupported claims and activity inventories. State the observation
window and material gaps, including limited sampling. Diagrams are useful when
inspected code or designs support a relationship that is easier to show.

## Finish

Follow [Publish or skip](references/commands.md#publish-or-skip). Return a short
introduction with the article link, or save the reason nothing merits publication
in SQLite. Keep previous articles and artwork; add dated corrections when needed.
Scheduled runs return new work or a new blocker; otherwise `NO_REPLY`.
The scheduler owns notification delivery.

For first-time setup, explain if no article was needed and confirm the installed daily job's
schedule and destination with the reader. Explain any missing access. Once the
first briefing and follow-up are arranged, remove `BOOTSTRAP.md` from the installed
workspace; retain the template copy.

For failed runs, follow [Recovery](references/commands.md#recovery).
