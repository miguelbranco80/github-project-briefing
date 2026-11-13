# Verification

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

A manual run of that existing job was requested. The request timed out; a
subsequent get showed runningAtMs, but run-history access returned a visibility
limit. No retry or replacement job was created. Live scheduled completion and
requester-side presentation are not verified by the source/package checks.

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
