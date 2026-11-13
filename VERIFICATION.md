# Verification

## Version 0.2.2: counted first-scan scope choices

The collector now checks GitHub Search PR counts before the first successful
baseline. If over budget or incomplete, it returns scope options without
reading conversations or creating a run/checkpoint. Shorter windows are counted
individually, not extrapolated from an average. The skill asks one combined
days/limit question and preserves user approval; it does not guess progressively
higher limits. Daily scans after a complete baseline keep the checkpoint path.

37 tests pass, including six first-scan regressions: counted choices, approved
limits, incomplete/malformed counts, real CLI stop/resume with either a raised
limit or a shorter window, read-only estimation, blocker deduplication, and
live-discovery protection against search undercounts. The archive check runs
the complete suite against the extracted runtime code, not just journal tests.

A read-only live estimate at 2026-11-13T00:24:45Z returned 925/649/189 PRs for
7/3/1 days and suggested limits of 1,200/800/300. No evidence scan was run.
Search counts are indexed estimates, not a transactional inventory or a runtime
forecast; conversation, commit and release volume can vary independently.

The targeted installed-agent update changes only SKILL.md and collect.py after
comparison with the previous template revision and a backup. Saved project
scope, evidence, articles, checkpoint and existing automation remain unchanged.
This does not resolve the scheduled portal/delivery blockers recorded below.

## Version 0.2.1: text-first journal and one workflow owner

31 tests pass against disposable generic project records. Coverage includes:
- Collector-derived observation windows and non-overwriting drafts.
- Text-only publication without cover metadata, artwork or image-prompts.json.
- An optional SVG diagram copied into the site with its article/source link.
- An older illustrated entry retained alongside a new text-only entry.
- Missing diagrams/optional covers, absent cover alt text, placeholders, broken
  links/anchors and changed evidence metadata refusing publication without
  replacing the good site or consuming reporting backlog.
- Pending drafts not entering the site or blocking completed articles.
- Retry preserving the article, site and delivery status while returning the
  output directory and post URL needed to present an already-built entry.
- All 21 runtime resources selected without development paths or project data.

Template validation and dev preview pass; the preview reports zero blocked
actions. The 0.2.1 archive contains exactly 24 files: the 21 runtime resources
plus CLAW.md, BOOTSTRAP.md and package.json. It contains no configured project,
evidence, articles, generated output, credentials or node_modules.

tests/check_archive.py extracts that archive into a fresh temporary directory,
installs locked dependencies and reruns all eight journal/package tests against
the extracted code. All pass. Diagram/artwork fixtures test rendering mechanics,
not architectural accuracy or a successful image-generation call.

## Runtime correction

The previous live test wrote and built an article, but delegated publication to
a helper that lacked portal/screen access. Its required cover generation ended
the initial child run before a later image-completion turn built the site. The
parent returned a pending draft response and did not present the later result.
That test did not establish reliable completion or delivery.

The skill now keeps publication/presentation with the requesting session;
optional helpers return evidence reviews only. The normal publication path
does not call image generation. Technical diagram rules remain in STYLE.md;
ILLUSTRATIONS.md applies only to requested one-off decoration.

The idle installed test agent and its initialized site engine received the
22 changed runtime files after comparison with the old template baseline.
Configuration, evidence, articles and assets were left unchanged; replaced
files were backed up. Its existing daily job's prompt now points at the single
updated skill. The job ID, schedule and destination were preserved.

A manual run of that existing job completed in 59 seconds. It collected four PR
changes and one commit, wrote a new text-only article and built five pages with
76 local link/asset checks. Its final blocker report is visible in the parent
session history. The existing artwork remained optional rather than blocking it.

End-to-end presentation and notification failed with concrete runtime blockers:
- The scheduled turn's portal call was denied because it lacked owner authority,
  despite the interactive agent having portal access.
- Delivery recorded lastDelivered=false, lastDeliveryStatus=not-delivered and
  "Channel is required when delivery.channel=last has no previous channel."

The run request itself timed out and the runs endpoint returned a visibility
limit; get and parent history supplied the results above. No run was retried,
no job was replaced and no broader tool permissions were granted. These runtime
blockers are not fixed by the prompt/build changes.

## Boundaries

The manifest declares one daily job. The journal reuses the collector and
reporting database; article Markdown is the briefing, not a second narrative
copy. Build validation is executable, while editorial truth and diagram
usefulness require source-based review. No new orchestration subsystem,
collector, dashboard or scheduler was added.

A normal template Add is not an upgrade of an existing agent. The targeted
test-agent file update above is not proof of a fresh installation. The recorded
Add defect in the installed 2026.11.5-beta.1 CLI is not fixed by this package.

Fresh-agent Add/recovery, live notification routing/receipts, interactive setup
racing a scheduled run, portal recovery after restart and requester-side
desktop/mobile rendering still require end-to-end qualification. No claim of
fully qualified unattended operation is made.
