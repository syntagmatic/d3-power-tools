---
slug: hierarchy-bundles
mode: single-shot
schema: hierarchical
render-load: medium-svg
interactivity: [hover, morph]
skills: [hierarchy, coordination, encoding]
provenance: v1-fixture
ablate-skill: hierarchy
---

Hierarchical edge bundle for linked software modules. The dataset
(`data/linked-modules.json`) is 62 module rows with dotted `name`
paths, `size`, `team`, `status`, and an `imports` array of target
module paths. The dotted names define the containment tree; imports
define cross-branch dependency links. Hovering a module or link
highlights the active module, its incoming/outgoing dependency paths,
and its ancestor branch. A layout toggle morphs between a radial
bundled view and a sorted two-column linked-tree view.

Render-load is **medium-svg**: module labels, branch nodes, and
dependency curves are all SVG. The chart should have enough DOM
structure for the structural gate to locate labels, paths, hover
state, and the layout toggle.

## Expected output

The default view is radial. Top-level namespaces form branches around
the circle; leaf module labels sit around the circumference, rotated
for readability. Curved bundled paths run through the center to show
imports between leaves. Links use low-opacity strokes by default, with
color or stroke treatment separating active, deprecated, experimental,
and stable modules if the implementation chooses to encode status.

On hover, unrelated paths and labels dim. The hovered module, its
incoming and outgoing links, linked target/source labels, and ancestor
branch gain a DOM-visible state class such as `highlight`, `active`,
`hover`, or `focus`. The state should be readable even when a module
has four or five dependencies.

The toggle morphs the same data into a two-column linked-tree layout:
source branches and labels on the left, target branches and labels on
the right, with curved dependency paths between the columns. Existing
paths and labels animate into the new positions instead of hard
rebuilding. Toggling back restores the radial bundle with the same
hover behavior.

The expected-output sketch is a *visual contract*, not a pixel target.
The rubric (dossier 04) scores aesthetics; this sketch gives the matrix
author and the harness fingerprint shared vocabulary about what the
chart *looks like*.
