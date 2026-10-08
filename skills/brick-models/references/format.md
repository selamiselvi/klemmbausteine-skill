# Bundle contract v1 / v1.1

## Format 1.1 (default for new models)

`schema_version: "1.1"`, validated against `model-1.1.schema.json`. Same fields as 1.0, with three differences:

- `part` is any official LDraw part ID (e.g. `3039`, `3659`, `3069b`) that `brick.py part ID` reports as a grid part.
- `color` is any LDraw colour code that Rebrickable records as produced for that part (`brick.py part ID` lists them).
  Unrecorded combinations are errors; colours or parts that cannot be matched between the two sources are warnings.
- `rotation` is 0, 90, 180 or 270 degrees about the vertical axis (direction matters for slopes and arches).

Each part is placed in one of two ways:

- **Grid:** `x`/`y` are the minimum corner of the rotated footprint in studs, `z` the body bottom in plates, `rotation` 0/90/180/270.
  The footprint is measured from the part's geometry; parts whose body overhangs the grid (handles, clips, hinge
  fingers) are anchored by their studs and receivers.
- **Free:** `pos` is the part origin in LDraw units (20 per stud, 8 per plate) with LDraw axes (-Y is up; a grid piece
  at `z` sits at Y = -8·z), and `matrix` is a row-major 3x3 rotation with entries -1/0/1 (24 orientations). Use
  `brick.py snap` to compute it from two connectors.

Collision boxes and connectors are measured from official geometry (`scripts/ldraw.py`, `analyze3d`): studs and stud
receivers in any direction, Technic pins/axles and holes, bars, clips and hinge fingers. Pieces connect where a stud meets a
receiver at the same point and axis, a pin lies on a hole's axis, a clip sits on a bar, or two hinge fingers meet.
The validator checks body collisions (4 LDU measuring grid, 0.6 LDU tolerance; pins in holes, clips on bars and
interleaved hinge fingers may overlap), studs blocked by bodies without a receiver, that every piece joins an earlier
piece (pieces on the table excepted), top-down insertion for upright pieces, one connected assembly and the
produced-colour record. Pin, clip and hinge connections are reported separately as inferred. The insertion path of
sideways pieces, hinge angles, clutch and stability are not checked. The bundle's `catalog.json` records the measured
parts, colours and the LDraw library release used. `model.ldr` places each official part with its own origin; renders
use the official meshes.

## Format 1.0

The executable schema is `model.schema.json`; the part/color catalog is `catalog.json`. `brick.py catalog` prints both catalogs. This initial palette deliberately covers regular, upright rectangular bricks and plates only.

## Model

New community bundles use English for the title, description and all step prose, as well as the guide labels and inventory. Proper names retain their spelling. This is an authoring/review requirement; schema validation is not language detection. Additional translated PDFs stay outside this versioned bundle; see `language.md`.

`schema_version: "1.0"`, a lowercase hyphenated `id`, `title`, `description`, `author`, `license` (use `UNLICENSED` until the creator chooses), `parts`, and `steps`.

Each part has a unique `id`, catalog `part` and `color` strings, integer `x`, `y`, `z`, and `rotation` (0 or 90). X/Y are the minimum footprint corner in stud units; Z is the bottom of the brick body in plate units. One stud is 8 mm, one plate is 3.2 mm, a brick is 3 plates. Studs are not included in body height. Rotation swaps catalog length/depth around the footprint center; X/Y remain its minimum corner. All pieces are upright. Z cannot be negative.

Each step has a short `title`, optional `note`, a list of part instance IDs, and optional `view` (`front-right`, `back-right`, `back-left`, `front-left`). Every part appears exactly once. Step order and listed part order are assembly order. Max 8 parts per step; up to 8,000 parts and 2,000 steps per model. These are validation caps, not design targets. The foundation may be placed as loose pieces on a table; all pieces must ultimately join into one stud-connected assembly. Later pieces require support from previously placed pieces. Digital checks are limited to grid-volume collisions, vertical stud overlap, connection graph and assembly order.

The camera convention has front at negative Y. Prefer a stable camera for neighboring steps; explicitly choose a rear view when new parts would be hidden.

## Generated directory

```
manifest.json                  Bundle version, identity, exact file list, sizes and SHA-256
model.json                     Canonical, validated input
model.ldr                      Editable LDraw assembly with STEP boundaries
catalog.json                   Exact catalog snapshot used by this export
parts.csv                      part_id,part_name,color_id,color_name,quantity
validation.json                Digital report; physical/visual status remain unverified
renders/front-right.png        Four 1200x1200 views (draft: 720)
renders/back-right.png
renders/back-left.png
renders/front-left.png
instructions.pdf               Cover, numbered steps, inventory
instructions/index.html        Self-contained browser guide, works from file://
instructions/steps.json         Versioned steps and image paths
instructions/step-001.png       Cumulative 3D view per step
instructions/map-001.svg        Top-down placement map per step
```

The optional technical guide uses manifest `schema_version: "1.1"` and `instruction_style: "technical"`. Its model and step schemas remain `1.0`. It adds exactly one `instructions/parts/{part_id}-{color_id}.png` for every distinct inventory combination, each 320 x 320. Technical step images keep the existing 1000 x 1000 resolution (draft: 640). Maps and placements remain in the data contract, but the technical PDF/HTML do not display them. Existing manifest `1.0` bundles use the legacy studio style and continue to validate. No mixed or unknown styles are accepted.

Only this fixed inventory is packaged; any extra file, missing file, changed hash or invalid model prevents packing. The ZIP contains these paths at its root, no parent folder. It does not include scripts or installed dependencies. The browser guide is generated by this tool; a future website importer must still treat incoming HTML as untrusted and use structured model/step data for its own UI.

The same model determines renders, steps, PDF, CSV and LDraw. Large opaque images embedded in the PDF use high-quality JPEG compression at their original pixel dimensions; the separate PNG assets remain lossless. Catalog colors are approximate display colors; part/color market availability is not checked. LDraw references official part IDs without bundling third-party meshes. The renderer uses original simplified dimensional meshes, not the official LDraw mesh library. Hollow undersides, clutch tolerances and mechanical stability are not simulated. See [LDraw format](https://www.ldraw.org/article/218.html) and [official part library](https://library.ldraw.org/).
