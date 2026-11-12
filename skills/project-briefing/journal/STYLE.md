# Journal style

## Editorial contract

Write an independent engineering journal, not official release notes and not a marketing blog. Follow work across polls: explain the engineering problem, the choice being made, what changed, why it matters, and what still needs to happen.

Use plain technical English. Lead with the consequence rather than a PR number. Group connected work into stories, with a short section for smaller changes. Use contributor names when authorship or a review explains a decision; an account name alone is not evidence a human wrote the text.

Link primary sources in the prose. Keep proposal, design merged, implementation merged and deployment evidence distinct. Attribute author-reported tests. Date every observation window. Mark interpretations as interpretations, not a maintainer roadmap. Do not infer implementation from the presence of an RFC on main.

Aim for a readable article rather than an exhaustive inventory. Quiet polls can produce short entries. The collector ledger retains the detailed record. Never invent quotes, progress, metrics, employee identities, screenshots or test results.

Keep the home page practical: latest article, earlier entries and archive navigation. Avoid slogans and repeated explanations of the journal's purpose; the About page owns that background.

## Visual contract

Preserve the shared templates and CSS. Warm paper background, ink-blue text, muted vermilion accents, thin rules, generous spacing. Georgia for editorial headlines and long-form reading, system sans-serif for summaries/navigation, monospace for dates and small labels. No remote font dependency. No client-side app or analytics.

Use the exact same page hierarchy for each post: issue/date → title → short description → topic line → generated editorial cover → article with a desktop contents rail → archive link. On mobile, stack the layout and keep the article readable without horizontal scrolling.

Keep the generated editorial covers and their established style; [ILLUSTRATIONS.md](ILLUSTRATIONS.md) owns the art direction. Covers are metaphors, not technical evidence.

### Architecture diagrams: optional, evidence-led

Add a diagram only when a concrete architectural relationship is important to the story and is clearer visually than in prose. It is not a required section or a decoration for every post. Do not add a generic boxes-and-arrows summary just to fill space.

Read the relevant code or PR at the observed revision before drawing. Use real component names and show only supported relationships, request paths or trust boundaries. Link the implementation or design source beside the diagram and label proposed behavior separately from implemented behavior. If the sources do not establish the architecture clearly, omit the diagram.

Use a labelled, code-native SVG or a statically rendered Mermaid diagram, separate from generated artwork. Save it with the post and check the actual rendering and labels at article and mobile widths; do not add a browser-side diagram framework merely in anticipation of needing one.

## Archive contract

Add new dated Markdown files. Keep earlier entries and images. New posts update the index and archive through the build. Do not silently rewrite older articles to reflect newer knowledge. Add a dated correction if necessary.
