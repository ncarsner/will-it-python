# will-it-python
an array of programs written just to see if the idea can be accomplished in Python code

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
