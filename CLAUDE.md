# CLAUDE.md — Curricular Sequence

## What This Is

A static web app that generates modifiable, printable curricular sequences for university degrees. Users select a catalog year and degree, then see courses organized by terms in recommended order. Data is hand-editable YAML. Target institution: Inter American University of Puerto Rico.

## Run

```bash
npx http-server . -p 8080 -c-1    # Serve locally (required for YAML fetch)
```

No build step. No dependencies beyond vendored js-yaml in `lib/`.

## Architecture

```
User selects Year → Degree
  ↓
YAML Loader (yaml-loader.js)
  → loads catalog-years.yaml → courses YAML → gen-ed template → degree YAML
  → merges gen-ed overrides
  → resolves course slots
  ↓
Settling Algorithm (settling.js)
  → topological sort (Kahn's) with credit packing
  → respects term_pins (YAML) + userPins (drag)
  ↓
Renderer (renderer.js)
  → CSS Grid term columns with draggable course cards
  → dropdowns for pick/choose_track rules
  → text inputs for open-elective
  ↓
Drag & Drop (drag.js) ←→ Re-settle / Reset
  ↓
Print (print.js + print.css)
```

## Project Layout

```
index.html                          # Single-page app
css/
  style.css                         # Screen styles (CSS Grid, cards)
  print.css                         # Print-specific (@media print)
js/
  app.js                            # Main: state, dropdowns, event wiring
  yaml-loader.js                    # Fetch/parse YAML, gen-ed merge, slot resolution
  settling.js                       # Term-settling algorithm (topological sort)
  renderer.js                       # DOM rendering: term grid, course cards, legend
  drag.js                           # HTML5 Drag & Drop between terms
  print.js                          # Print preparation
data/
  catalog-years.yaml                # Master index: years → degrees
  courses/
    courses-2025-26.yaml            # Course definitions (code, title, credits, prereqs)
  gen-ed/
    gen-ed-bachelor.yaml            # Shared Bachelor's Gen Ed template (48 cr)
    gen-ed-associate.yaml           # Shared Associate Gen Ed template (24 cr)
  degrees/
    2025-26/
      computer-science-bs.yaml      # Example degree file
lib/
  js-yaml.min.js                    # Vendored js-yaml 4.1.0
```

## Data Format

All data is YAML. Hand-edit these files directly.

### Adding a new catalog year
1. Create `data/courses/courses-YYYY-YY.yaml` with course definitions
2. Create degree files in `data/degrees/YYYY-YY/`
3. Add year entry to `data/catalog-years.yaml`

### Adding a new degree
1. Create `data/degrees/YYYY-YY/degree-name.yaml`
2. Reference it in `catalog-years.yaml` under the appropriate year

### Category Rule Types

| Rule | Behavior | UI |
|------|----------|-----|
| `fixed` | Exactly these courses | Static cards |
| `sequence` | Ordered, one per term | Static cards, ordered |
| `pick` | Choose N from options | Dropdown(s) |
| `choose_track` | Pick a track, then sequence | Track dropdown → cards |
| `prereq-order` | Settle by prerequisite graph | Static cards, auto-placed |
| `open-elective` | Free entry | Text input fields |

Add new rules: add name in YAML + handler in `settling.js` + renderer in `renderer.js`.

### Category Types (color-coded)
- `gen-ed` — blue
- `core` — purple
- `major` — green
- `distributive` — orange
- `elective` — gray

### Gen Ed Overrides
Degrees reference a shared gen-ed template and can override via `gen_ed.overrides`:
- Scalar properties (credits, default) → replaced
- `subcategories` as array → full replacement
- `subcategories` as object keyed by id → targeted merge
- `_remove: true` → deletes category entirely

### Term Pins
Degrees can pin courses to specific terms via `term_pins` (1-indexed). The settling algorithm respects these. Users can also drag courses to create runtime pins.

## Settling Algorithm

Modified Kahn's algorithm (topological sort):
1. Build prereq graph (only within-degree courses)
2. Apply YAML term_pins + user drag-pins
3. BFS to compute earliest possible term per course
4. Credit-pack unpinned courses into earliest term with room (≤ max_credits_per_term)
5. Validate no course placed before its prereqs

## Key Behaviors

- Changing a dropdown (pick, track) triggers full re-settle + re-render
- Dragging a course creates a user pin (does NOT trigger re-settle automatically)
- "Re-settle" re-runs algorithm preserving user pins
- "Reset" clears all user pins and selections
- Terms showing > max_credits_per_term display a red credit badge
- Elective field count formula: `5 + (elective_credits / 3)`

## Tech

- Vanilla HTML/CSS/JS — no framework, no build step
- ES modules (`type="module"` in app.js)
- js-yaml 4.1.0 loaded as global `jsyaml` via script tag
- CSS custom properties for theming
- HTML5 Drag and Drop API
