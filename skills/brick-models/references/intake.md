# Short intake before model design

After establishing the subject, offer a choice between automatic and guided planning. Both routes resolve size, detail and instruction granularity. `scripts/intake.py` is the single source of mode/profile question wording, option IDs and numeric design targets. It uses only Python's standard library and writes JSON to stdout; no installation, network call or output folder is needed.

## Conversation

1. Establish the subject from a text description, reference image, or both. If none is given, use the entry invitation in `SKILL.md`, which explicitly offers both input types, unless the user also delegates the subject. Do not add a separate text-versus-image selection question. For an image, inspect the main shape, proportions, colors and distinctive features; a caption is optional. Clarify only an unclear target when several objects are equally plausible, or an inaccessible image. Unseen sides require a design interpretation, not a mandatory request for more photos. Reference images guide geometry; do not automatically copy them into the sharing bundle.
2. Reuse explicit preferences and mode choices already given. “Just make it”, “you decide”, “skip the questions” and equivalent wording select auto mode immediately. A request to work through the choices selects guided mode. Do not ask the mode question again when intent is already clear. When all three preferences are supplied, proceed directly.
3. Otherwise run the helper with known choices, for example `python scripts/intake.py --language de --size small`. Its only question is “How would you like to start?” with two options. Wait for this choice before showing any detailed questions. Silence or a preselected option is not consent to a mode.
4. In guided mode, call the helper with `--mode guided` and known answers. Present only its remaining questions together in the returned order: size, detail, experience. Wait for answers, preserving partial answers. Use the host's question UI when available, otherwise a short numbered list. For other languages, translate the English copy without changing the choices. Do not expose internal IDs or ask for stud counts, render settings, file formats or exact part counts.
5. In auto mode, choose the missing preferences internally from the subject and brief, then call the helper with `--mode auto`. Pass user-supplied choices as `--size`, `--detail`, `--experience` and your decisions as `--choose-size`, `--choose-detail`, `--choose-experience`. The helper never returns user questions in this mode. `needs_agent_choices` means **you** still need to decide the listed fields; do not forward that request to the user.
6. Once ready, briefly state the intended model in everyday language and proceed. Do not turn the summary into a second confirmation gate. Retain the resolved profile in working context and use its targets during design and instruction planning.

The user may switch to auto mode halfway through the questionnaire. Keep all answers already supplied and decide only the remainder. Revisions retain previous choices and mode; do not restart onboarding for a color or layout adjustment.

## Choosing on the user's behalf

Choose the smallest practical scale that leaves the subject's defining features legible. A simple single object may suit small; an assembly with multiple roofs, towers or a courtyard may need medium. Use large when the brief or composition warrants it, not merely because questions were skipped. Balanced detail is a useful starting point, but simplify or enrich it to match the actual subject. Avoid a fixed small/balanced profile for every request and avoid rigid subject-name lookup tables.

For example, “Just make a Japanese temple” could warrant a medium model with balanced detail to leave room for a recognizable layered roof, columns and entrance. This is a design judgment, not a mandatory temple preset. A request for a tiny temple retains the small scale. Work within supported geometry; in auto mode, choose and briefly state a reasonable stylized interpretation instead of asking routine design questions.

If experience is unknown, the helper uses beginner-friendly steps as a presentation choice; do not claim the user is a beginner. Size and detail still depend on the motif. `--mode auto --choose-size medium --choose-detail balanced` therefore yields medium/balanced targets with clear small steps. Auto mode does not fill size and detail with universal defaults.

Free-text preferences and explicit limits override presets and agent decisions. A precise height or a maximum number of pieces remains a constraint even if it differs from the nearest profile. Retain these overrides with the working brief outside the skill repository and outside the exported bundle. Do not add unrecognized fields to `model.json`. Auto mode delegates ordinary design decisions, not permission to ignore constraints. Ask only if a missing essential input or incompatible explicit requirements actually prevent a workable interpretation.

## Design targets

The helper's size ranges describe the **longest outer dimension**, including the base. They are this project's planning categories, not official product categories. Parts ranges combine size and detail; they are estimates, not promises about cost, build time or difficulty. Do not add filler just to hit a lower bound.

Size changes physical scale. Detail changes the number of distinctive features and the parts budget at that scale. Experience changes instruction granularity and how carefully small or obscured placements are separated. Beginner does not automatically mean small or simplified; experienced does not waive connection checks or justify hidden placements. The returned maximum parts per step is a ceiling, not a target to fill.

A highly detailed model still uses the currently supported rectangular parts. This choice does not enable slopes, curves, moving mechanisms or realistic CAD fidelity. Explain a material limitation honestly. Guided mode can clarify an important interpretation; auto mode should choose a reasonable stylization unless it would contradict an explicit requirement.

Before rendering, compare actual dimensions, part count and step granularity against the resolved targets. Minor variation is acceptable when it improves the model; explain a material departure and resolve a conflict with an explicit user constraint before continuing. The helper standardizes intake and planning, not the exact geometry that an agent will invent.

In guided mode, colors, a special feature or an existing parts collection are conditional follow-ups only when they would materially change the design. In auto mode choose these yourself unless explicitly constrained. Avoid extending the questionnaire for routine design choices.
