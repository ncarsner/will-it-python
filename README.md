# will-it-python
an array of programs written just to see if the idea can be accomplished in Python code

## Naval Flags

A CLI that converts text to [International Code of Signals (ICS)](https://en.wikipedia.org/wiki/International_maritime_signal_flags) naval signal flags rendered in the terminal.

### Usage

```
naval_flags TEXT [--ascii]
```

| Flag | Description |
|------|-------------|
| `TEXT` | Text to render as flags (A-Z, 0-9; spaces separate flag groups) |
| `--ascii` | Render in monochrome ASCII mode (NO_COLOR compatible) |

### Examples

```bash
# Render "SOS" as ANSI color-block flags
uv run naval_flags SOS

# Render in monochrome ASCII mode (works in any terminal)
uv run naval_flags --ascii HELLO
```

### Supported characters

- Letters A-Z (rendered as ICS phonetic alphabet flags: Alfa through Zulu)
- Digits 0-9 (ICS numeral flags: Zero through Niner)
- Flags render left-to-right on the same rows; the input text is printed as a header above them
- Spaces insert a 3-cell visual gap between flag groups (no phonetic labels shown)
- Unknown characters are silently skipped

### Flag images

SVG reference images for all 36 flags are stored in `assets/naval_flags/`.
See [`assets/naval_flags/CREDITS.md`](assets/naval_flags/CREDITS.md) for
license and source information.

---

## Trait Venn

A web app that estimates how rare a person is from a combination of traits. Pick 1–5 traits; the app draws a Venn diagram of them, shows each trait's prevalence and every intersection, and converts the all-traits center into "1 in N" odds and expected head counts for the world and for a selected nation of origin.

### Usage

```
trait_venn [--host HOST] [--port PORT] [--no-browser]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `127.0.0.1` | Interface to bind |
| `--port` | `8765` | Port to listen on |
| `--no-browser` | off | Do not open a browser window on start |

```bash
uv run trait_venn
# equivalent:
uv run python3 -m will_it_python.trait_venn
```

The selection and nation are kept in the page URL (`?sel=female,left,green&country=US`), so a combination can be bookmarked or shared.

### Layout

- **Header** — "Someone who is … is **1 in N** worldwide", expected counts on Earth and in the selected nation, and the nation selector (United States first, then all others alphabetically).
- **Left column, Conventional** — gender, age, handedness, eye color, hair color, blood type, and where you live; one choice per row.
- **Center** — the Venn diagram (circles for 1–3 traits, ellipses for 4–5). Hover a region, or focus the diagram and use the arrow keys, to inspect it.
- **Right column, Less conventional** — everyday, senses & mind, health, genetic quirks, birth, lifestyle, and rare experiences, as drill-down categories (one open at a time).
- **Inspector (lower right)** — the hovered region, or the all-traits center by default: odds, share, "only these" odds, and expected counts.

Traits in each category are sorted from most to least common for the selected nation. The diagram, chips, and inspector use the selected nation's prevalence; the headline is worldwide.

### Calculations

- Traits are treated as independent conditional on gender (female/male): P = Σ_g P(g) · Π P(trait | g). Color blindness, height over 6 ft, and migraines carry gender-specific prevalence.
- Odds are shown as "1 in int(1/p)" for p < 0.2, otherwise as the simplest fraction k/n (n ≤ 20) within 10% (e.g., "3 in 4").
- Percentages are omitted for combinations rarer than 1 in 1,000,000.
- Expected counts are ⌊population × p⌋; below one person the app shows "statistically nobody" with the expected value.

### Data sources

- **Population** — world and United States figures come from the [U.S. Census Bureau Population Clock](https://www.census.gov/popclock/) (base value, per-second growth rate, and update time), refreshed at most every 10 minutes and projected forward each second. If the clock is unreachable, an approximate projection is used and labeled as such. Other nations use static 2026 estimates.
- **Trait prevalence** — rough published estimates for illustration; not medical or genetic reference values.

---

## Personality Space

An interactive 3D/2D scatter plot that maps persons onto three personality-system axes: **Zodiac sign** (12 positions), **Enneagram type with wing** (18 positions), and **MBTI type** (16 positions). Any permutation of the three systems can be assigned to any axis. Persons with missing data for a selected axis are placed at the axis midpoint with a hollow marker.

### Usage

```
personalities [--port PORT] [--debug]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--port` | `8050` | Port the Dash server listens on |
| `--debug` | off | Enable Dash debug/hot-reload mode |

### Features

- Drag to rotate, scroll to zoom (3D mode uses Plotly's built-in orbit controls)
- Swap which personality system appears on each axis via the X / Y / Z dropdowns; already-selected systems are disabled in sibling dropdowns
- Toggle between 3D scatter and 2D scatter with the mode radio button
- Add new persons via the name + axis-value form at the bottom; persons with partial data are shown with a hollow marker rather than silently dropped (toggle with the "Show persons with missing data" checkbox)
- Five sample persons are loaded on startup to seed the chart

### Running locally

```bash
uv run personalities
# or with options:
uv run personalities --port 9000 --debug
```
