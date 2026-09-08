# Generated image style — owner feedback, September 8, 2026

Status: approved style incorporated into Plan 0070; independent actual-code review and clean
release verification in progress. The owner subsequently authorized all five visual correctness
priorities and the established independent-review playbook. See PLAN-0070-VISUAL-CORRECTNESS.md.

The owner requested these changes:

- No NBN-added internal labels such as “illustrative data” or “not news” in graphics. Dates,
  sources and useful qualifications about the data remain appropriate.
- Highlight-card text should fill the available content area. Prefer enlarging the font;
  add surrounding copy only when it supplies useful context.
- Remove the duplicate bottom-left Next Block News name. Keep branding at bottom-right;
  preserve actual external source attribution and date details at left.
- Double the outer padding on both highlight-card formats and refit the passage within it.

Writer and editor visual guidance now reflect these preferences. The proof generator no longer
paints fixture labels into the images; its README retains their synthetic development status.
The renderer chooses the largest fitting excerpt font in each preset, preserving the selected
passage, paragraph breaks and highlights. It respects the outer padding, footer separation and
readability floor, and rejects content that cannot fit. Template version: nbn-visuals-4.

Combined prompt version: editorial-core-v2.29-visual-evidence. The main task explicitly agreed
to include its independently reviewed appendix-reference repair in this clean release.
Deployment status and exact verification are recorded in SPRINT-0070-FINDINGS.md.

Updated proofs are in the shared design workspace:
`/Users/brady/Documents/ChatGPT/Next Block News/reviews/post-visuals-2026-09-08/proofs-v4/`.
The original review proofs and four approved reference PNGs are preserved. The approved design
README records the owner clarifications. Source excerpts and fixture values were not expanded
to fill space. Highlight text insets are now 104px horizontally and 96px from the top, twice
the previous values. Footer side insets are 128px and logo bottom clearance is 72px, likewise
doubled. The excerpt refits within the remaining area. NBN source identity stays in metadata;
the visible footer omits its duplicate name while preserving any date and external source.

The layout measures the final line's actual glyph/highlight height, adjusts leading within a
readable range, and avoids stranding a final word when it can reflow the preceding line.
An excerpt too sparse to fill the content area within those limits asks for useful surrounding
source context; it does not invent copy or silently accept a largely empty card.

Earlier style validation: 32 focused visual/delivery tests passed, including image-pixel checks that short
excerpts fill both presets and remain clear of the footer, plus rejection of unfit text.
All ten proof dimensions were verified; both revised excerpt PNGs were visually inspected.
Runtime writer/editor prompt assembly includes the new guidance. No model or publisher calls.

Plan 0070 also verifies actual pixels for all six palette colors in both presets. New proof
outputs include all ten templates/formats and irregular-date charts. The excerpt line reflow
keeps paragraph boundaries intact. The source wording is unchanged.
