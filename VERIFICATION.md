# Verification

## Version 0.2.0: illustrated journal template

29 tests pass against disposable generic project records, including the existing
collector/refresh tests and the journal CLI. Journal coverage includes:
- Collector-derived observation windows and repeatable, non-overwriting drafts.
- Two articles, latest-entry selection and archive preservation.
- Missing artwork/provenance, placeholders, broken links/anchors and changed
  evidence metadata refusing publication without consuming reporting backlog.
- Pending drafts not entering the site or blocking other completed articles.
- Publication retry preserving the existing article and delivery status.
- All 21 runtime resources selected, without absolute development paths or OCE
  repository names.

Template validation and dev preview pass; the preview reports zero blocked
actions. The built 0.2.0 archive contains exactly 24 files: those 21 runtime
resources plus CLAW.md, BOOTSTRAP.md and package.json. It contains no configured
project, collected evidence, articles, generated output, credentials or node_modules.

tests/check_archive.py extracts that archive into a fresh temporary directory,
installs locked dependencies there and reruns the six journal/package tests
against the extracted code. This verifies the artifact rather than relying
only on the development checkout. Test artwork is an explicit disposable
fixture, not a claimed successful image-generation call.

## Source review

The installed skill owns one operational workflow. The manifest declares one
daily job; the blog reuses the collector and reporting database. Article
Markdown is the briefing, not a second narrative copy. Editorial/diagram rules,
art direction and schema each have their own referenced guide.

Source review found and fixed draft/build interference before packaging. Drafts
remain outside the rendered source; failed builds restore the draft and retain
the previous site. Metadata parsing uses line-delimited frontmatter, including
literal --- punctuation inside descriptions.

The earlier independent review of 0.1 found two P2 defects (ledger regeneration
overwriting registered briefings, and changing query parameters defeating
blocker suppression). Those fixes and regression tests remain. The 0.2 source
review was performed directly; no new independent clean-review verdict is claimed.

## Runtime limits

This release updates portable template source. It does not upgrade the existing
installed agent, alter its jobs or depend on its old workspace.

Fresh-agent Add/recovery, scheduler routing/receipts, interactive setup racing
a scheduled run, real cover generation and requester-side portal rendering
remain end-to-end verification work. The recorded Add problem in the installed
2026.11.5-beta.1 CLI is not fixed by this package. No claim of fully qualified
unattended operation or live visual rendering is made.

Semantic briefing quality still requires source-based evaluation; passing
collection/build tests does not establish accurate engineering interpretation.
