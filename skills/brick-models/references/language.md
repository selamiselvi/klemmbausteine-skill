# Conversation and artifact languages

Speak with the user in their language. The canonical community bundle is English regardless of chat language: model title/description, all step titles/notes, PDF, browser guide and catalog labels. Proper place names and creator names may retain their original spelling. State once while beginning work that the standard instructions will be English and that an additional translated PDF is available on request; do not add a language questionnaire in automatic mode.

Author all canonical model prose in English before building. Check the prose and sample early/middle/late PDF pages for language consistency; do not mix translated step titles with English interface headings. The validator checks structure, not natural-language correctness. Do not claim automated language detection. Do not edit the skill's English templates into the user's language.

For an existing mixed-language bundle, translate only the model's title, description and step titles/notes in a separate working copy of `model.json`, then run:

```sh
python scripts/brick.py refresh-guide ORIGINAL_BUNDLE --text-model ENGLISH_MODEL_JSON --out NEW_ENGLISH_BUNDLE
```

The command rejects changes to geometry, step membership/order, cameras, IDs, attribution or license. It reuses the rendered images and regenerates the canonical model, PDF, HTML, step text, LDraw comments and manifest. No Blender rerender is needed for a text change.

## Additional translated PDF on request

Keep the English bundle as the community version. If the user explicitly requests another language, also generate a separate PDF outside that bundle:

```sh
python scripts/brick.py translation-template ENGLISH_BUNDLE > WORKING_TRANSLATION_JSON
python scripts/brick.py localize-guide ENGLISH_BUNDLE --translation WORKING_TRANSLATION_JSON --out TRANSLATED_PDF
```

Between those commands, translate the complete template: language tag, title, description, every step title/note, all fixed labels, part names and color names. Keep the same keys and step order; preserve `{parts}` and `{steps}` placeholders, part/color IDs and dimensions. The agent performs the translation; this tool is a deterministic formatter, not a translation service. No translation source or model-specific prose belongs in the skill repository.

Missing fields are rejected instead of falling back to English. The PDF uses the exact existing images; geometry and all canonical files remain untouched. The current optional translation export is PDF-only and is not automatically added to the sharing ZIP. The browser guide, CSV and model in the community bundle stay English.

For characters missing from the built-in PDF font, provide compatible regular and bold TTFs using `--font FONT_TTF --bold-font BOLD_TTF`. The exporter rejects missing glyphs. Fonts requiring shaping or right-to-left layout still need explicit layout support; do not promise all languages work from translation alone. Inspect the translated PDF for glyphs, wrapping, overflow and language consistency before delivering it. Translation changes page composition only; it never triggers Blender.
