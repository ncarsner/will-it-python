# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased] — venn-diagrams (issue #9)

### Added

- `trait_venn` web app: select 1–5 traits and see a Venn diagram of their
  prevalence, every intersection, "1 in N" odds, and expected head counts for
  the world and a selected nation of origin
- 100 traits in 14 categories, split into conventional (always visible:
  gender, age, handedness, eye color, hair color, blood type, where you
  live) and less conventional (drill-down: everyday, senses & mind, health,
  genetic quirks, birth, lifestyle, rare experiences); one choice per
  exclusive group; age brackets ordered youngest to oldest
- Gender-conditional probability model for color blindness, height, and
  migraines
- Tuned 4- and 5-set ellipse layouts that keep the all-traits center small
- World and US population from the Census Population Clock with a labeled
  fallback projection; static 2026 estimates for other nations
- Keyboard exploration of diagram regions and WCAG-oriented focus, contrast,
  and ARIA state handling
- Text view: a live text summary (headline, counts, selected traits, table
  of every intersection) that replaces the diagram on demand
- Reader-view support: the summary stays available to browser reader views
  and screen readers when hidden, is server-rendered into the initial HTML
  for the URL's selection, and selection changes are pushed to browser
  history so reader views re-read the page; the SVG uses concrete colors,
  the document title follows the result, and print styles show the summary
- 347 tests with 100% branch coverage for the `trait_venn` package

---

## [Unreleased] — naval-flags (PR #8, merged 2026-05-24)

### Added

- `naval_flags` CLI: converts text (A-Z, 0-9) to ICS signal flag
  representations rendered in the terminal as ANSI color blocks
- `--ascii` flag for monochrome NO_COLOR-compatible output
- 36 ICS reference SVGs sourced from Wikimedia Commons stored in
  `assets/naval_flags/`
- 103 tests with 100% branch coverage

### Changed

- Flags now render left-to-right on the same rows instead of stacking
  vertically; input text is printed as a header above the flags
- Word spaces create a 3-cell visual gap between flag groups
- Removed per-flag phonetic label (CLI is a translator, not a glossary)
- Reduced flag width from 20 to 16 characters (`_COLS` 10 → 8)

---

## [Unreleased] — feat-personalities-v2 (planned)

### Added

- `PRD-personalities-v2.md` — visual/UX improvement spec: drop backdrop,
  bolder borders, remove grid, floating tick labels, axis normalization,
  randomized sample persons, sphere/cube toggle
- GitHub issues #2–#6 tracking all v2 work items

---

## [Unreleased] — feat-personalities (PR #1)

### Added

- **`personalities` CLI command** (`uv run personalities [--port 8050] [--debug]`) —
  launches an interactive Dash web app for visualizing personality profiles
- **3-D ellipsoid sphere visualization** — semi-transparent shell divided into
  8 labeled octants by three great-circle loops, one per selected personality axis;
  rotatable and zoomable via Plotly's built-in controls
- **2-D circle fallback** — clearing the Z-axis dropdown collapses the view to a
  flat circle with 4 quadrant labels; all three axis dropdowns are clearable
- **Personality systems supported**:
  - Zodiac (12 signs, ARIES–PISCES)
  - Enneagram with wing (types 1–9 × 2 wings = 18 positions; wraparound wings
    1w9 and 9w1 handled correctly)
  - MBTI (16 types via 4-bit E/I·N/S·T/F·J/P encoding)
- **Axis assignment** — any permutation of the three systems can be assigned to
  X, Y, or Z; already-selected systems are disabled in sibling dropdowns
- **Missing-data handling** — persons lacking data for a selected axis are plotted
  at the axis midpoint with a hollow marker; a checkbox toggles their visibility
- **Add-person form** — name + all three personality fields; partial profiles
  accepted; person appended to the live chart without a restart
- **5 sample persons** seed the chart on startup (two intentionally missing a
  field to demonstrate hollow-marker behavior)
- `authorized_libraries.md` — approved third-party library manifest per project
  rules (plotly, dash, pytest, pytest-cov, pytest-mock)
- `pyproject.toml` — added ruff, mypy, pytest, and coverage configuration;
  `personalities` entry point

### Changed

- `README.md` — added Personality Space section with usage instructions

---

## [0.1.0] — 2026-05-22

### Added

- Initial project commit: `police_lights` module with `police_lights`, `emgy`,
  `code3`, `pursuit`, `traffic`, and `cruise` CLI entry points
- `pyproject.toml` with project metadata and entry points
