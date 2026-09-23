# will-it-python
an array of programs written just to see if the idea can be accomplished in Python code

## Development

```bash
uv sync                    # create the environment, including dev tools
uv run pre-commit install  # wire the secret-scanning hooks into git commit
```

`pre-commit install` is a one-time step per clone. After it, every commit runs
`detect-secrets` against `.secrets.baseline`, plus checks for private keys,
files over 500 KB, and unresolved merge conflict markers.

Before requesting review, run:

```bash
uv run pre-commit run --all-files
uvx ruff check src tests
uv run mypy src
uv run pytest
```

If `detect-secrets` flags a line that is not a secret, confirm that by reading
it, then record it in the baseline and say why in the commit message:

```bash
uv run detect-secrets scan --baseline .secrets.baseline
```

Hook versions are pinned in `.pre-commit-config.yaml`; refresh them with
`uv run pre-commit autoupdate`.

---

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

### Running with uvx

`uvx` builds the project into an isolated, cached environment and runs the `trait_venn` script; no virtual environment setup is needed on the local machine, only [uv](https://docs.astral.sh/uv/).

```bash
# From the root of a local clone
uvx --from . trait_venn

# From any directory, pointing at a local clone
uvx --from /path/to/will-it-python trait_venn

# Straight from GitHub (main), without cloning
uvx --from git+https://github.com/ncarsner/will-it-python trait_venn

# Options pass through after the script name
uvx --from . trait_venn --port 9000 --no-browser
```

**From a branch.** Append `@<branch>` to the repository URL; the script name, `trait_venn`, follows:

```bash
uvx --from git+https://github.com/ncarsner/will-it-python@venn-diagrams trait_venn

# Pick up commits pushed to the branch since the last run
uvx --refresh --from git+https://github.com/ncarsner/will-it-python@venn-diagrams trait_venn
```

Use a tag or commit hash in place of the branch name (for example `@91de062`) to pin an exact version.

The first run downloads the project's dependencies into uv's cache, so it takes longer than later runs. Git sources are cached after the first build, so pass `--refresh` to fetch new commits. Local runs (`--from .` or a path) rebuild automatically when any file under `src/` changes, so trait edits show up on the next launch without extra flags.

The selection and nation are kept in the page URL (`?sel=female,left,green&country=US`), so a combination can be bookmarked or shared; without `sel`, the default selection (female, left-handed, green eyes) is shown, and `sel=` means nothing selected.

### Layout

- **Header** — "Someone who is … is **1 in N** worldwide", expected counts on Earth and in the selected nation, and the nation of origin, shown as text; the ▾ button next to it opens the picker (United States first, then all others alphabetically).
- **Left column, Conventional** — gender, age, handedness, eye color, hair color, blood type, and where you live; one choice per row.
- **Center** — the Venn diagram (circles for 1–3 traits, ellipses for 4–5). Hover a region, or focus the diagram and use the arrow keys, to inspect it.
- **Right column, Less conventional** — everyday, senses & mind, health, genetic quirks, birth, lifestyle, and rare experiences, as drill-down categories (one open at a time).
- **Inspector (lower right)** — the hovered region, or the all-traits center by default: odds, share, "only these" odds, and expected counts.

Traits in each category are sorted from most to least common for the selected nation, except age brackets, which run youngest to oldest. The diagram, chips, and inspector use the selected nation's prevalence; the headline is worldwide.

### Text view, reader views, and printing

**Text view** (header link, or `?view=text` in the URL) replaces the diagram with a text summary of the current result: the headline, counts for the selected nation and the world, the selected traits, and a table of every intersection. It updates immediately as traits or the nation change.

Outside text view, the same summary is visually hidden with clipping rather than `display: none`, so browser reader views (Safari Reader, Firefox Reader View) and screen readers still pick it up, and printing shows it in place of the controls. The server also renders the headline, title, and summary into the HTML for the selection in the URL, so the page is complete before any script runs. Each selection change is recorded as a browser history entry (Back undoes it), which prompts reader views to re-read the page. The summary is the page's only `<article>`, the header shows the nation as text with the picker created only while open, and the column headings are CSS-generated text, so reader views show the result rather than inert controls or picker labels; change the nation or traits on the page itself. The diagram is drawn with concrete colors so it keeps its colors when a reader view copies it.

### Accessibility

Scanned with `@axe-core/cli` (headless Firefox, tags `wcag2a,wcag2aa,wcag21a,wcag21aa`) in five states — default, five traits, text view, empty selection, and a non-US nation — with zero violations (#11).

```bash
npx @axe-core/cli --browser firefox --load-delay 1500 \
  --tags wcag2a,wcag2aa,wcag21a,wcag21aa http://127.0.0.1:8765/
```

axe cannot compute contrast for the diagram's labels, because translucent ellipses overlap them; those ratios were checked by hand. In the light theme the worst case is 4.88:1 for a label over its own fill and 6.70:1 for white chip text on the solid color; the dark theme is 5.42:1 or better.

### Calculations

- Traits are treated as independent conditional on gender (female/male): P = Σ_g P(g) · Π P(trait | g). Color blindness, height over 6 ft, and migraines carry gender-specific prevalence.
- Odds are shown as "1 in int(1/p)" for p < 0.2, otherwise as the simplest fraction k/n (n ≤ 20) within 10% (e.g., "3 in 4").
- Percentages are omitted for combinations rarer than 1 in 1,000,000.
- Expected counts are ⌊population × p⌋; below one person the app shows "statistically nobody" with the expected value.

### Updating traits

All trait, category, and country data lives in [`src/will_it_python/trait_venn/traits.py`](src/will_it_python/trait_venn/traits.py). Ordering, percentages, odds, the diagram, and the summary are derived from it; no other file needs to change.

**Add or edit a trait** by adding a `Trait(...)` entry to the `TRAITS` tuple:

```python
Trait(
    "widowpeak",             # id: stable, ASCII, no spaces; used in URLs (?sel=widowpeak)
    "Genetic quirks",        # category: must match a name in CATEGORIES
    "Widow's peak",          # name: shown in the diagram, inspector, and summary
    "Widow's peak",          # short: chip label in the picker
    0.30,                    # p: worldwide prevalence, 0 < p < 1
    us=0.28,                 # optional United States override
    has_phrase="a widow's peak",  # headline: "Someone who has a widow's peak ..."
),
```

| Field | Required | Meaning |
|-------|----------|---------|
| `id`, `category`, `name`, `short`, `p` | yes | Positional, in that order |
| `us` | no | United States prevalence, used when the nation is the US |
| `group` | no | Exclusive-group key; at most one trait per group can be selected (e.g. `"eyes"`) |
| `by_gender`, `by_gender_us` | no | Gender-dependent prevalence: `_by_gender(female=0.005, male=0.08)` |
| `is_phrase` / `has_phrase` | exactly one | Headline wording: "is *phrase*" or "has *phrase*" |
| `gender` | — | Only on the Female and Male options |

For extremely rare traits, express `p` as a count of living people over the world population, as the existing entries do (for example `_EVEREST_SUMMITERS / _WORLD_2026`). Percentages below 1 in 1,000,000 are not displayed; odds still are.

**Rules checked by the test suite:**

- Ids are unique, ASCII, and contain no spaces.
- Every trait's category exists, and every category has at least one trait.
- All prevalence values are strictly between 0 and 1.
- Each trait has exactly one of `is_phrase` and `has_phrase`.
- The worldwide values of each exclusive group sum to 1 (± 0.02).
- Every `by_gender` table defines both female and male.

Renaming an id breaks saved links that use it; those pages fall back to the default selection.

**Add a category** to `CATEGORIES`: `Category("Name", Side.CONVENTIONAL)` places it in the left column (always expanded; intended for one-choice groups), `Side.UNCONVENTIONAL` in the right column as a drill-down. Categories appear in tuple order. Traits within a category are sorted by prevalence for the selected nation; pass `by_prevalence=False` to keep their tuple order instead (as Age does, youngest to oldest).

**Add a nation** to `COUNTRIES`: `Country("CODE", "Name", population)`, using the ISO 3166-1 alpha-2 code and a population estimate. The United States stays first in the picker and the rest are listed alphabetically; US figures come from the Census clock at runtime.

**After editing**, run the checks and restart the app:

```bash
uv run pytest tests/test_trait_venn_*.py
uv run ruff check src/will_it_python/trait_venn
uv run trait_venn          # or: uvx --from . trait_venn
```

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
