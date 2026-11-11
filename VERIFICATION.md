# Verification

## Current local checks

- 14 collector tests pass, covering bounded discovery, dormant PR exclusion, explicit reconciliation, pagination limits, checkpoint rollback, deduplication, release edits/drafts, and pending-output recovery.
- New discovery/reconciliation regressions fail against the saved pre-change collector. The evidence-limit test checks bounded runtime behaviour without a new test-only API.
- Template validation and dev preview pass; preview reports zero blocked actions. Preview is not installation.
- git diff --check passes.
- Rebuilt archive: dist/project-briefing-0.1.0-simplified.tgz.

## What changed

Discovery now reads PRs in updated order and stops at the time boundary or the 100-PR budget. It no longer inventories all open PRs. Each other paginated evidence stream is limited to 1,000 records. Overflow fails the scan; no partial checkpoint or silently selected subset is recorded. Reconciliation explicitly revisits previously tracked open PRs.

Bootstrap introduces the agent. The skill owns one ordered workflow. The manifest owns the role and schedule. Combined instruction length fell from 1,746 to 1,015 words.

## Limits of this evidence

Earlier live raw-labs/snapi baseline/delta checks passed before this discovery change. The revised collector has not been live-retested; current discovery evidence uses deterministic GitHub fixtures.

Still unverified: fresh-agent onboarding, execution-host access, scheduled/no-setup runs, malformed configuration handling, blocker deduplication, setup/job races, delivery receipts and routing, and deletion cleanup. Those behaviours are partly instructions, not deterministic collector guarantees. Briefing usefulness also needs an installed-agent trial.

No agent or automation was installed during this revision. No dashboard or publication.
