# Portable journal engine

This directory is installed with the Project Briefing skill. The skill owns the
single daily workflow; STYLE.md owns editorial and diagram choices,
ILLUSTRATIONS.md covers optional one-off artwork, and templates/post.md is the
article starter. No external learned skill or development workspace is required.

scripts/journal.py (beside this directory, under the skill's scripts/) prepares
a separate site under each configured STATE/journal/. It fills repository
branding and derives the post date and observation window from the completed
collector run. Draft paths are stable per run and live outside src/. Preparing again does not
overwrite the draft, archive or art; unfinished drafts cannot block other posts.
The starter is writing guidance, not publishable prose. Publication rejects its
explicit draft marker even after metadata is filled; replace the scaffold and
remove the marker after editorial review. This check cannot judge writing quality.

The publish command builds and validates that site, then records the article
as the run's briefing in the existing SQLite reporting table. A retry returns
the existing output and its serving paths without rewriting it or resetting
delivery. Here "publish" means updating local static output, not public hosting.
Neither a cover nor image-generation provenance is required. Existing optional
covers still render; their paths and alt text are checked when supplied.

The builder uses pinned Eleventy and Python 3.10+. It stages output and checks
metadata, local links, images and heading anchors before replacing _site/.
Failed builds do not mark the run written and retain the previous site.
npm ci --ignore-scripts installs locked dependencies on the first build;
subsequent builds reuse them. Rendering does not poll GitHub or generate art.

Only STATE/journal/_site/ may be served. Evidence databases, source caches,
configuration and article drafts are not the preview root. Portals are temporary;
a built site is not proof of requester-side rendering or permanent hosting.

Package updates do not overwrite initialized journals automatically. Keep their
sources, URLs and artwork; apply intentional layout updates separately rather
than reinitializing or deleting the site.
