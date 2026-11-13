# Journal style

## Editorial contract

Write an engineering blog post for engineers who have not followed the repository. Explain a technical problem and the work addressing it; do not turn the collector's activity ledger into prose. Write as an independent observer, not an official spokesperson or a maintainer claiming work as their own.

Choose the strongest supported story and give it a specific technical headline. Open with the problem or changed behavior and why a reader should care. Keep scan counts, run IDs and collection status out of the lead; those belong in the sources footer or delivery message. Even a first scan should synthesize the important engineering work, not inventory every PR.

Develop the story in connected paragraphs: explain the previous behavior, how the change works, the design choice or trade-off, and its practical consequence. Name the relevant components, interfaces or failure sequence and explain unfamiliar project terms. Inspect the code or design needed to support that explanation; do not invent technical detail to make a thin source sound substantial. Use a small example or code excerpt when it genuinely clarifies the mechanism.

Group related work by the problem it addresses, not one section per PR. Choose descriptive headings from the material rather than repeating a fixed report outline. Use lists or tables only when they make a comparison or sequence clearer. A smaller-changes section or a closing next step is optional: include it only when there is something concrete to say. Keep the full inventory in the ledger. Publish a short article when the evidence warrants one; omit filler on quiet days.

Use plain technical English and an engaged, measured voice. Cut hype, vague importance claims, decorative metaphors and stock conclusions such as "a significant milestone" or "underscores the importance of". Explain what improves, for whom and under what conditions instead. Do not pad the post with repeated summaries or a boilerplate "what to watch" section.

Link primary sources naturally where they support the explanation, rather than opening every paragraph with a PR number and status. Keep proposed behavior, merged design, merged implementation and deployment evidence distinct. Attribute author-reported tests and place important uncertainty beside the affected claim, without repeating a generic qualification disclaimer after every paragraph. Do not infer implementation from an RFC on main or deployment from a merge. Use contributor names when authorship or a review explains a decision; an account name alone does not establish who wrote the text.

For example, a fictional report-style sentence is: "PR #123 adds a disconnect check. The author reports two tests." An engineering explanation is: "A client can disconnect while identity lookup is still running. A close listener installed afterward misses that event, so the handler may start a backend read nobody needs. Checking the connection before starting I/O closes that gap." Real posts must link inspected evidence for such a mechanism and state whether the fix is proposed or merged.

Before publishing, reread the actual draft: can a reader explain the problem, mechanism and consequence without opening every link? Check each technical claim against its source, remove inventory-like passages and unsupported conclusions, and cut any section that adds no understanding. This is an editorial review, not a word-count or keyword score; the builder cannot certify good prose or architectural truth. Never invent quotes, progress, metrics, employee identities, screenshots or test results.

End with a compact sources-and-limits footer naming the observation window and material coverage gaps. A rewrite of saved evidence is not a fresh check. Keep agent setup, tool failures, hosting status and notification receipts in the delivery message, not the article's narrative.

Keep the home page practical: latest article, earlier entries and archive navigation. Avoid slogans and repeated explanations of the journal's purpose; the About page owns that background.

## Visual contract

Preserve the shared templates and CSS. Warm paper background, ink-blue text, muted vermilion accents, thin rules, generous spacing. Georgia for editorial headlines and long-form reading, system sans-serif for summaries/navigation, monospace for dates and small labels. No remote font dependency. No client-side app or analytics.

Use the same page hierarchy for each post: issue/date → title → short description → topic line → article with a desktop contents rail → archive link. On mobile, stack the layout and keep the article readable without horizontal scrolling. Text-only is the normal format; do not fill image-free layouts with decorative placeholders.

Preserve any existing artwork. [ILLUSTRATIONS.md](ILLUSTRATIONS.md) covers optional one-off decoration, not a per-entry requirement.

### Architecture diagrams: optional, evidence-led

Add a diagram only when a concrete architectural relationship is important to the story and is clearer visually than in prose. It is not a required section or a decoration for every post. Do not add a generic boxes-and-arrows summary just to fill space.

Read the relevant code or PR at the observed revision before drawing. Use real component names and show only supported relationships, request paths or trust boundaries. Link the implementation or design source beside the diagram and label proposed behavior separately from implemented behavior. If the sources do not establish the architecture clearly, omit the diagram.

Use a labelled, code-native SVG or a statically rendered Mermaid diagram, separate from generated artwork. Save it with the post and check the actual rendering and labels at article and mobile widths; do not add a browser-side diagram framework merely in anticipation of needing one.

## Archive contract

Add new dated Markdown files. Keep earlier entries and images. New posts update the index and archive through the build. Do not silently rewrite older articles to reflect newer knowledge. Add a dated correction if necessary.
