# Optional one-off artwork

Use this guide only when the user requests decorative site artwork. Generate it
once, save the original and reuse it; do not generate a new cover for each post.
It must not block an article or a daily update. STYLE.md owns technical diagrams.

## Art direction

Hand-printed editorial illustration, precise ink outlines, screen-print grain,
warm ivory paper, deep ink blue, muted vermilion, dusty teal and a little ochre.
Spacious workshop or architectural metaphors; no glossy 3D, robot mascots, text,
letters, numbers, logos or watermarks. This is decoration, not system evidence.

Inspect the result and save it under src/assets/illustrations/. Record its asset,
exact prompt and tool/model when known in image-prompts.json. Describe the actual
image in alt text and identify generated artwork in its caption. Optional legacy
post artwork uses cover, coverAlt and coverCaption; leave these fields out of
ordinary articles.

Follow the image tool's continuation instructions in the requesting session.
If generation finishes in a later turn, resume that one-off request there.
A failed or pending branding image does not make a text article unfinished.
