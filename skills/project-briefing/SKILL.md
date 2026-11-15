---
name: project-briefing
description: Research GitHub projects, save engineering briefings and discuss changes with the reader.
---

# Project briefing

Help the reader understand engineering work they would otherwise have to piece
together from code and discussion. GitHub access is read-only.

When asked what is new, read the saved articles and use the conversation to
identify what the reader has already seen. Check recent run history if updates
are missing. Start fresh research when requested or during scheduled runs.

## Setup

For a new project, find out which GitHub project the reader wants to follow and
what interests them. Look at recent work before recommending a focus. If they have
no preference, choose a useful starting point and explain it. Check the
[workload](references/commands.md#check-scope) before collecting. For a busy repository,
use recent work and the reader's interests to recommend a focus or budget; agree
meaningful trade-offs with them.

Save the repository and interests using [configuration.md](references/configuration.md),
then follow Research, Write and Finish below for the first briefing. Afterwards,
configure the [daily job](references/configuration.md#daily-job) and remove
`BOOTSTRAP.md` from the installed workspace. Use the configuration reference for
later repository, focus or schedule changes.

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

Write an engineering newsletter for someone who follows the project.
Lead with a concrete headline and a short opening explaining the most
important news.

Group related changes into stories with descriptive headings. Explain
what changed, how it works and why it matters. Use short paragraphs,
plain language and concrete examples. Link supporting code or discussion
beside the relevant claim.

State each story’s status once. Include limitations when they affect
how someone would use or adopt the change. Keep general research and
verification limits in a brief closing coverage note.

Let the news determine the length; a follow-up may need only one story.
Before saving, cut repeated caveats, abstract framing and details
that do not help the reader understand the change.

## Finish

Follow [Save or skip](references/commands.md#save-or-skip) to record the review.
In interactive runs, summarize the findings in chat and link the saved article.
Keep earlier articles; add dated corrections when needed.

Scheduled runs save articles quietly and return `NO_REPLY` on success. Record
blockers in the run's response for later inspection; keep the agreed scope until
the reader changes it. For failed commands, follow [Recovery](references/commands.md#recovery).
