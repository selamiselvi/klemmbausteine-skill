# Project scope

- This repository is public. Keep private briefs, voice recordings, credentials and unpublished submissions out of it.
- Write all repository documentation, instructions, canonical prompts, comments and example prose in English. The agent translates user-facing conversation into the user's language at runtime; do not maintain translated prompt copies in the source.
- Build the model-generation skill, reusable tools, documentation and the versioned output contract here.
- Keep generated models, renders, PDFs, ZIPs, review images and development revisions outside this repository and outside the website repository. Use a separate sibling working directory; `.gitignore` is not a substitute for this separation.
- `examples/` currently contains reproducible source inputs only. Add a finished output example only after the owner explicitly selects it for publication; document that single example and exclude development revisions from Git history.
- Deterministic exporters and validators enforce the output contract. Agent prose alone is not sufficient.
- This release is owner-maintained distribution only: do not invite external contributions, pull requests or model submissions. The skill may package local results when requested. It must not contain the website's importer, admin UI or publishing access.
- Community submission is disabled until the owner explicitly opens it. Do not prompt for submissions, send messages or publish work.
- Do not claim physical build verification from digital checks alone.
- The scaffold is not an implemented skill. Do not document installation or generation commands as working until tested.
