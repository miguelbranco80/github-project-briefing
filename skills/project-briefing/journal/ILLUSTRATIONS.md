# Illustration direction

Generate an original editorial cover for each meaningful journal entry using an available image-generation tool. Do not substitute a screenshot, stock photo or SVG placeholder and describe it as generated artwork. Keep the existing post and artwork when retrying a run; do not regenerate old covers during builds.

## Shared visual language

Hand-printed editorial illustration, precise ink outlines, screen-print grain, warm ivory paper, deep ink blue, muted vermilion, dusty teal and a little ochre. Architectural and workshop metaphors; spacious, restrained and thoughtful. Flat geometric construction with subtle tactile texture. No glossy 3D, robot mascots, text, letters, numbers, logos or watermarks. Artwork is metaphorical, not a factual system diagram.

For the first post, use this palette and direction. For later posts, also reference an approved cover from the same journal when the tool supports it. Change the subject to fit the engineering story, not the visual style.

## Prompt basis

Use case: illustration-story. Asset: landscape editorial cover, approximately 3:2 composition. Depict a concrete workshop or architectural metaphor for [the entry's actual engineering change]. Use precise ink outlines, flat geometric shapes, subtle screen-print grain and warm paper texture. Warm ivory background, deep ink blue, muted vermilion, dusty teal and small ochre details. Spacious, crafted composition. No text, labels, letters, numbers, logos, watermark, neon, glossy 3D or UI screenshots. Original editorial art, not a literal architecture diagram or webpage mockup.

Inspect the result and save it at the cover path returned by the journal helper. Record the exact submitted prompt, tool/model when known, article and asset path in the journal's image-prompts.json. Supply alt text describing the actual image; the layout labels it as AI-generated.

If image generation is unavailable or fails, keep the draft and report that the journal entry is pending. Do not mark that run's illustrated article finished. The source-linked text can still be discussed without claiming the illustrated blog is ready.
