# PRD: Personality Space — Visual & UX Improvements (v2)

**Branch target:** `feat-personalities` (or new branch off `main` after PR #1 merges)
**Scope:** `src/will_it_python/personalities.py` and `tests/test_personalities.py`
**Date:** 2026-05-22

---

## Background

PR #1 shipped the initial Personality Space visualizer: a Dash app with a 3D scatter plot inside a semi-transparent ellipsoid shell, great-circle dividers, and a 2D circle fallback. User testing revealed several visual and UX pain points:

- The ellipsoid backdrop is visually noisy and obscures the person markers
- The Plotly default "graph-paper" axis planes and grid lines compete with the data
- Axis tick labels appear on flat boundary planes, disconnected from the 3D space
- The three personality axes use different raw scales (Zodiac 0–11, Enneagram 0.75–9.25, MBTI 0–15), giving unequal visual weight
- The sample persons (Alice/Bob/Carol/Dave/Eve) are generic and don't update on reload
- There is no way to switch between sphere and cube visualizations

---

## Goals

1. Clean up the visual layer — data and structure, no decorative clutter
2. Make axis labels legible and spatially anchored to the 3D geometry
3. Equal visual weight per axis via normalization
4. Fresher, randomized sample data on every launch
5. Sphere/cube toggle so users can compare spatial intuitions

---

## Non-Goals

- A user-triggered "Randomize persons" button (future feature, noted below)
- Changing the personality systems (Zodiac, Enneagram, MBTI)
- Persistent storage of persons between sessions

---

## Requirements

### 1. Drop the ellipsoid surface backdrop

Remove the semi-transparent `go.Surface` shell from 3D mode entirely.
The great-circle loops (XY, XZ, YZ planes) remain as the primary 3D structure.

**Acceptance criteria:**
- [ ] No `go.Surface` trace appears in any figure produced by `build_figure`
- [ ] `_make_ellipsoid_surface` function is removed from the module
- [ ] Existing tests for the surface are removed; 100% coverage maintained

---

### 2. Bolder great-circle and quadrant divider lines

Increase line weight and opacity on both 3D great circles and 2D quadrant dividers.

**Target values:**
- 3D great circles: `width=3`, `rgba(80,120,200,0.70)` (up from width=2, opacity=0.45)
- 2D quadrant dividers: same proportional increase

**Acceptance criteria:**
- [ ] All great-circle `go.Scatter3d` traces use `width≥3` and opacity `≥0.65`
- [ ] 2D divider lines updated to match
- [ ] Visual regression: run app and confirm lines are clearly visible at default zoom

---

### 3. Remove Plotly axis background panes and grid lines (3D)

Set `showgrid=False`, `showbackground=False`, and `zeroline=False` on all three
scene axes so the chart renders against a clean void.

**Acceptance criteria:**
- [ ] `build_figure` 3D layout sets all three scene axes with `showgrid=False`,
  `showbackground=False`, `zeroline=False`
- [ ] No `tickvals`/`ticktext` remain on scene axes (replaced by floating labels)

---

### 4. Per-tick labels floating on sphere surface (3D mode)

Replace flat axis-plane tick labels with `go.Scatter3d` text traces that position
each label at its normalized coordinate on the relevant great circle.

**Placement rules (unit sphere, axes normalized to [-1, 1]):**
- X-axis labels: `(x_norm, 0, -(1 - x_norm²)^0.5)` — bottom of the XZ great circle
- Y-axis labels: `(0, y_norm, -(1 - y_norm²)^0.5)` — bottom of the YZ great circle
- Z-axis labels: `(-(1 - z_norm²)^0.5, 0, z_norm)` — left side of the XZ great circle

Font: size 7, `rgba(60,60,80,0.80)`. One Scatter3d per axis dimension.

**Open question — octant pole labels:**
The existing octant labels (`"Aries-Virgo"` / `"Libra-Pisces"` etc.) at 1.18× radius
overlap with per-tick labels. Decision required before implementation:
- Option A: Remove octant pole labels entirely (per-tick labels are sufficient)
- Option B: Keep octant labels, position them further out (1.35×) to avoid collision
- Option C: Keep octant labels in cube mode only

**Acceptance criteria:**
- [ ] Three `go.Scatter3d` text traces added for X/Y/Z tick labels in 3D mode
- [ ] Labels visually adjacent to their respective coordinate positions
- [ ] Octant pole label behavior resolved and implemented per chosen option
- [ ] 2D mode: per-tick labels NOT added (2D uses standard axis ticks — no change)

---

### 5. Normalize all axes to [-1, 1] unit sphere

All three personality axes are rescaled to the range [-1, 1] before plotting.
Hover text and tick labels continue to show original human-readable values.

**Normalization formula:**
```
normalized = (raw_value - _MIDPOINTS[dim]) / _HALF_RANGES[dim]
```

Missing-data midpoint becomes `0.0` (center of the unit sphere).

**Acceptance criteria:**
- [ ] `_normalize(value: float, dim: PersonalityDimension) -> float` function added
- [ ] All person coordinates in `build_figure` pass through `_normalize`
- [ ] Great circles, octant labels, and tick label traces all use unit-sphere geometry
  (center = origin, radius = 1 in each axis)
- [ ] Hover text still shows original labels (e.g., "Zodiac: Scorpio"), not normalized floats
- [ ] All existing tests updated to use normalized coordinate assertions
- [ ] 100% coverage maintained

---

### 6. Randomize sample persons on app load

Replace `SAMPLE_PERSONS` (static list) with a `make_sample_persons()` function
that returns five `PersonProfile` instances each time it is called, using names
Alex, Blake, Chris, Dylan, and Elliott with randomly chosen personality values
(each field independently has a ~20% chance of being `None` to exercise missing-data paths).

**Constraints:**
- Use Python's `random` module (already stdlib, no new dep)
- `create_app` calls `make_sample_persons()` as the default — each server start is fresh
- `SAMPLE_PERSONS` constant is removed

**Future feature note:** A user-triggered "Randomize" button that re-seeds the store
in-browser (without restarting the server) is deferred.

**Acceptance criteria:**
- [ ] `make_sample_persons() -> list[PersonProfile]` added; returns 5 persons with the given names
- [ ] Each call can produce different values (non-deterministic); test with `random.seed`
- [ ] `SAMPLE_PERSONS` constant removed
- [ ] `create_app` default changed from `SAMPLE_PERSONS` to `make_sample_persons()`
- [ ] Tests: seed-based tests confirm name list, value types, and null distribution

---

### 7. Sphere / Cube toggle (3D mode only)

Add a `dcc.RadioItems` control (id `"shape-toggle"`) with options `"sphere"` and `"cube"`.
Visible only when the Z axis is selected. Defaults to `"sphere"`.

**Cube wireframe:** 12 `go.Scatter3d` line segments forming a unit cube from
`(-1,-1,-1)` to `(1,1,1)`. Same line style as great circles (bolder values from §2).

**Tick label placement in cube mode:**
- X labels at `(x_norm, -1.15, -1.15)` — bottom-back edge of cube
- Y labels at `(-1.15, y_norm, -1.15)` — left-back edge of cube
- Z labels at `(-1.15, -1.15, z_norm)` — left-bottom edge of cube

**Acceptance criteria:**
- [ ] `_make_cube_wireframe() -> list[go.Scatter3d]` added
- [ ] `build_figure` accepts `shape: Literal["sphere", "cube"] = "sphere"` parameter
- [ ] In 3D mode: sphere → great circles; cube → cube wireframe
- [ ] Tick label placement switches between sphere-surface and cube-edge positions
- [ ] `compute_figure` passes `shape` through from UI
- [ ] `shape-toggle` RadioItems hidden when Z axis is unset (2D mode)
- [ ] `add_person_to_store` callback unaffected
- [ ] 100% coverage maintained

---

## Test coverage requirements

All new and changed functions require 100% branch coverage:
- `_normalize` — both normal and midpoint (missing) cases
- `make_sample_persons` — seed-based; assert names, non-None counts
- `_make_cube_wireframe` — assert 12 traces, all `go.Scatter3d`
- `build_figure` with `shape="cube"` — assert no great-circle traces; cube traces present
- Tick label traces — assert 3 per 3D figure; correct mode="text"
- Layout assertions — `showgrid`, `showbackground`, `zeroline` all False

---

## Out of scope / future backlog

- **Randomize button**: user-triggered in-browser randomization of all persons
- **Cube as standalone mode**: making cube permanent default
- **Axis label density control**: show every Nth label for crowded axes (Enneagram 18 ticks)
- **Persistent storage**: save persons to a file or database between sessions
