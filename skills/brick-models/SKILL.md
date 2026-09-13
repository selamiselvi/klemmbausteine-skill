---
name: brick-models
description: Design or revise buildable brick models from a text brief or reference image, then generate consistent 3D renders, step-by-step instructions, parts lists and a sharing bundle with local tools.
---

# Brick Models

Create an editable brick assembly, not an image that merely resembles bricks. Work in the user's output directory. All paths below are relative to this skill directory; resolve them before running commands.

## Start

Read [the model contract](references/format.md) before authoring a model. Run `python scripts/brick.py doctor` to check Python dependencies and Blender. Install requirements into a project-local virtual environment if missing; use the Blender path reported by doctor or supplied by the user.

Translate the brief into a silhouette, scale, palette and a sensible parts budget. Ask only about choices that materially change the result. For a first unspecified model, propose a compact design and proceed. An image is a visual reference; reconstruct the assembly, not its pixels.

## Design and iterate

Write `model.json` using the supported catalog returned by `python scripts/brick.py catalog`. Use [design guidance](references/design.md) for connection, sequencing and visibility choices. The agent designs the assembly; the exporter does not interpret prose or invent geometry.

This first engine supports upright rectangular bricks and plates at integer stud/plate coordinates, with 0/90-degree rotation. If a brief needs slopes, hinges, curved parts or sideways connections, explain that limitation and agree on a simplified interpretation or extend and test the engine. Never silently substitute unsupported parts or claim general CAD/physics validation.

Run `python scripts/brick.py validate MODEL`. Fix errors in the source. Consider warnings about support and temporary loose foundation pieces. Keep each numbered step small and its title meaningful.

Run `python scripts/brick.py build MODEL --out OUTPUT` to produce the complete result. For a faster iteration use `--quality draft`; final output defaults to `standard`. Use a new output directory for revisions; an existing directory is never overwritten.

Inspect all four renders and representative early/middle/late instruction pages plus the parts inventory. Check silhouette, actual placement visibility, framing and readable labels. The guide includes a cumulative 3D view and a stud-grid placement inset; newly added pieces retain their color while earlier pieces are muted. If a step is ambiguous, split it or change its camera in the model and rebuild. Rendering success alone is not quality approval.

When only the guide layout or UI code changes, use `python scripts/brick.py refresh-guide OUTPUT --out NEW_OUTPUT` to regenerate PDF/HTML/maps while preserving the validated model and rendered images.

## Deliver and share

Return the preview, the local `instructions/index.html`, PDF, parts CSV and editable model. State which digital checks passed and whether anyone has physically built it. The generated report intentionally leaves visual approval and physical testing unverified; do not rewrite those fields to manufacture a pass.

Only after the result is ready, ask whether the user wants to submit it to the community. If yes, run `python scripts/brick.py pack OUTPUT --zip PATH.zip`. The package command revalidates outputs and checks their inventory and hashes. It does not publish anything.

Explain that the creator can upload the ZIP to WeTransfer or another transfer service and email its download link to the community. The community destination has not launched yet: do not invent an address or claim an upload was submitted. Confirm the creator's preferred attribution and sharing license before an actual submission. Never include credentials or the website's private administration tools.
