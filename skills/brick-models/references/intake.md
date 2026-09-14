# Short intake before model design

The three required choices are size, detail and building experience, in that order. `scripts/intake.py` is the single source of question wording, option IDs and numeric design targets. It uses only Python's standard library and writes JSON to stdout; no installation, network call or output folder is needed to ask these questions.

## Conversation

1. Establish the subject from the user's text or image. If no subject is given, ask what they want to build. Do not infer a subject from the intake defaults.
2. Reuse explicit choices already given in the conversation. A request for a small lighthouse answers size, but says nothing about the user's experience. An image alone does not establish physical size, detail preference or experience.
3. Run the helper with known choices, for example `python scripts/intake.py --language de --size small`. Present its remaining questions together in the returned order, using the returned labels and descriptions. Use the host's question UI when available, otherwise a short numbered list. For languages other than English or German, translate the English wording without changing the choices or their meanings. Do not expose internal IDs or ask the user for stud counts, render settings, file formats or exact part counts.
4. Wait for the missing answers. Partial answers remove only the corresponding questions. Ambiguous answers need clarification only for the affected choice. A preselected UI option, silence or elapsed time is not an answer.
5. Run the helper again with all resolved choices. Briefly state the intended model in everyday language and proceed; this is not another confirmation gate. Use the returned targets during design and instruction planning.

If the user explicitly says to choose for them, `--defaults` fills only unanswered choices with small / balanced / beginner. State those assumptions briefly. It must not replace preferences they already supplied. Revisions retain previous choices unless the user changes them; do not restart onboarding for a color or layout adjustment.

Free-text preferences and explicit limits override presets. For example, a precise height or a maximum number of pieces remains a constraint even if it differs from the nearest profile. Retain these overrides with the working brief outside the skill repository and outside the exported bundle. Do not add unrecognized fields to `model.json`. If preferences conflict, ask about that tradeoff only; do not silently lower detail or increase size.

## Design targets

The helper's size ranges describe the **longest outer dimension**, including the base. They are this project's planning categories, not official product categories. Parts ranges combine size and detail; they are estimates, not promises about cost, build time or difficulty. Do not add filler just to hit a lower bound.

Size changes physical scale. Detail changes the number of distinctive features and the parts budget at that scale. Experience changes instruction granularity and how carefully small or obscured placements are separated. Beginner does not automatically mean small or simplified; experienced does not waive connection checks or justify hidden placements. The returned maximum parts per step is a ceiling, not a target to fill.

A highly detailed model still uses the currently supported rectangular parts. This choice does not enable slopes, curves, moving mechanisms or realistic CAD fidelity. If a distinctive requested feature cannot be represented, explain the specific limitation and resolve its interpretation before designing it.

Before rendering, compare actual dimensions, part count and step granularity against the resolved targets. Minor variation is acceptable when it improves the model; explain a material departure and resolve a conflict with an explicit user constraint before continuing. The helper standardizes intake and planning, not the exact geometry that an agent will invent.

Colors, a special feature, or an existing parts collection are conditional follow-ups only when they would materially change the design. Otherwise choose a suitable restrained palette and avoid extending the initial questionnaire.
