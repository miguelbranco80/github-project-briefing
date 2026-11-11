# Verification

## Current revision

23 tests pass, including the real refresh/collector CLI against fake gh, baseline
and delta, no configuration, malformed configuration, path/budget validation,
independent repository failures, blocker deduplication/recovery, concurrent
refresh exclusion, lightweight collection, checkpoint rollback and reporting
recovery. No network or credentials are needed for these tests.

Template validation and dev preview pass (zero blocked actions). The archive
is dist/project-briefing-0.1.0-lifecycle.tgz. A preview is not installation.

## Source review

Independent Codex review used the complete current source, instructions, docs
and tests, not recollection. It found two P2 defects:
- Registered briefings could be overwritten by ledger regeneration.
- Changing API window parameters defeated blocker suppression.

Both are fixed with regression tests. Ledger filenames are reserved for new
outputs; legacy registered briefings are preserved. Error signatures strip
changing query parameters. No second clean-review verdict is claimed.

## Boundaries

This revision changes portable source only. It does not upgrade the existing
installed agent, alter its job or remove historical patches from its database.
Earlier installed-agent use exposed the onboarding, collection and reporting
problems addressed here.

Still unverified: real scheduler routing/receipts, installation recovery on the
affected Gateway, interactive setup racing a scheduled refresh, and deletion
cleanup. Template instructions now separate collection readiness from delivery
readiness. No claim of fully tested unattended operation.

The skill now requires source checks, attribution and omission checks for
briefings. Briefing usefulness and RFC-to-implementation interpretation still
need evaluation against a real project's sources; deterministic collection tests
do not establish semantic quality.
