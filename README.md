# Brick Models

A local agent skill for designing brick assemblies and producing four studio views, step-by-step building instructions, a parts CSV and a portable ZIP bundle.

**Early working version.** The first engine supports upright rectangular bricks and plates on a stud grid. It does not yet support slopes, hinges, sideways connections or arbitrary imported CAD. The agent designs the model; the included tools validate and export that design.

## Use with your agent

Install the skill folder at `skills/brick-models` with your agent's skill installer, or ask your agent to read its `SKILL.md` directly from this checkout. Then ask:

> Use $brick-models to create a small brick lighthouse. Produce the model, four renders, a PDF building guide and a parts list. Inspect the result before offering to package it.

The skill is self-contained in that folder. It contains no website administration tools or publishing credentials.

## Run the example locally

Requirements: Python 3.11+ and Blender. Tested on macOS with Python 3.14 and Blender 5.2. Other supported Blender/Python combinations still need testing.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r skills/brick-models/requirements.txt
.venv/bin/python skills/brick-models/scripts/brick.py doctor
.venv/bin/python skills/brick-models/scripts/brick.py build examples/coastal-light.json --out outputs/coastal-light
```

On Windows, use the virtual environment's `Scripts/python.exe`. Supply `--blender /path/to/blender` or set `BLENDER_BIN` if Blender is not found automatically. The tool recognizes the standard macOS application path.

Open `outputs/coastal-light/instructions/index.html` directly in a browser. The guide works offline without a web server. The bundle also contains `instructions.pdf`, `parts.csv`, `model.json`, `model.ldr` and four PNG renders. LDraw viewing requires an external official parts library; no LDraw meshes are bundled here.

Use `--quality draft` for lower-resolution iteration. Existing output directories are never overwritten. To apply guide-layout changes without rerendering the model:

```sh
.venv/bin/python skills/brick-models/scripts/brick.py refresh-guide outputs/coastal-light --out outputs/coastal-light-guide-v2
```

To compare an optional technical guide with the same model and untouched hero renders:

```sh
.venv/bin/python skills/brick-models/scripts/brick.py refresh-guide outputs/coastal-light --out outputs/coastal-light-technical --instruction-style technical
```

This variant retains all brick colors, uses blue edges for new additions, replaces studio lighting with simple face tones, and shows rendered part icons and quantities. Coordinate maps stay in the bundle data but are hidden in the guide. For new models, `build --instruction-style technical` produces this style directly. It is currently an alternative for visual comparison; the default remains the original studio guide.

## Validate and package

```sh
.venv/bin/python skills/brick-models/scripts/brick.py validate examples/coastal-light.json
.venv/bin/python skills/brick-models/scripts/brick.py verify outputs/coastal-light
.venv/bin/python skills/brick-models/scripts/brick.py pack outputs/coastal-light --zip outputs/coastal-light.zip
.venv/bin/python -m unittest discover -s tests -v
```

Packaging is a local operation, not publication. After choosing to submit, the creator uploads the ZIP to WeTransfer or another transfer service and emails its download link. A community address will be provided when the website launches.

## Output contract and checks

The [versioned format](skills/brick-models/references/format.md) defines model coordinates, files and metadata. Geometry, renders, guides and inventory share one model. Export paths and camera conventions are fixed. Pixel-identical rendering across hardware or Blender versions is not promised.

Checks cover schema, unique instances, step coverage, body intersections, vertical stud connections, placement order and final connectivity. The generated reports keep physical-build and visual-review status unverified. They do not prove stability, clutch strength, market availability or all assembly motions. Rendered brick meshes are original dimensional approximations, including simplified undersides.

Manifest hashes detect file changes; they are not an authenticity signature. Community imports must independently validate submitted packages.

## License

License selection is pending. MIT is proposed for the skill and tools. Model-sharing licenses are separate; the example currently uses `UNLICENSED`. This is a development version, not a completed open-source release.
