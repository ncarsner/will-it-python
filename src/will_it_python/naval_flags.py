"""Naval flags CLI - convert text to ICS signal flag representations."""

from __future__ import annotations

import argparse
from collections.abc import Callable

# ANSI reset sequence
RESET: str = "\033[0m"

# ANSI background color codes keyed by single-letter color code
_ANSI_BG: dict[str, str] = {
    "W": "\033[47m",  # White
    "B": "\033[44m",  # Blue
    "R": "\033[41m",  # Red
    "Y": "\033[43m",  # Yellow / Gold
    "K": "\033[40m",  # Black
}

# Monochrome ASCII character pairs for --ascii / NO_COLOR mode
_ASCII_CHARS: dict[str, str] = {
    "W": "  ",  # White  = blank
    "B": "~~",  # Blue   = tilde
    "R": "##",  # Red    = hash
    "Y": "++",  # Yellow = plus
    "K": "**",  # Black  = star
}

# Default render grid dimensions
_ROWS: int = 6
_COLS: int = 10

# Thresholds used by shape-pattern factories
_SALTIRE_THRESHOLD: float = 0.2
_DIAMOND_THRESHOLD: float = 0.3
_CIRCLE_THRESHOLD: float = 0.04

# Pattern function type: (row, col, total_rows, total_cols) -> color-code char
type _PatternFn = Callable[[int, int, int, int], str]


# ---------------------------------------------------------------------------
# Pattern factory functions - each returns a _PatternFn closure
# ---------------------------------------------------------------------------


def _solid(color: str) -> _PatternFn:
    """Return a pattern function that fills the flag with one color."""

    def fn(r: int, c: int, rows: int, cols: int) -> str:
        return color

    return fn


def _vertical_split(left: str, right: str) -> _PatternFn:
    """Return a pattern function split left/right at the midpoint."""

    def fn(r: int, c: int, rows: int, cols: int) -> str:
        return left if c < cols // 2 else right

    return fn


def _horizontal_split(top: str, bottom: str) -> _PatternFn:
    """Return a pattern function split top/bottom at the midpoint."""

    def fn(r: int, c: int, rows: int, cols: int) -> str:
        return top if r < rows // 2 else bottom

    return fn


def _horizontal_stripes(*colors: str) -> _PatternFn:
    """Return a pattern function with evenly-spaced horizontal stripes."""
    n = len(colors)

    def fn(r: int, c: int, rows: int, cols: int) -> str:
        return colors[r * n // rows]

    return fn


def _vertical_stripes(*colors: str) -> _PatternFn:
    """Return a pattern function with evenly-spaced vertical stripes."""
    n = len(colors)

    def fn(r: int, c: int, rows: int, cols: int) -> str:
        return colors[c * n // cols]

    return fn


def _checkerboard(color1: str, color2: str, n: int) -> _PatternFn:
    """Return a pattern function with an NxN checkerboard grid."""

    def fn(r: int, c: int, rows: int, cols: int) -> str:
        return color1 if (r * n // rows + c * n // cols) % 2 == 0 else color2

    return fn


def _four_quarters(tl: str, tr: str, bl: str, br: str) -> _PatternFn:
    """Return a pattern function with four solid-color quadrants."""

    def fn(r: int, c: int, rows: int, cols: int) -> str:
        if r < rows // 2:
            return tl if c < cols // 2 else tr
        return bl if c < cols // 2 else br

    return fn


def _center_band_h(outer: str, band: str) -> _PatternFn:
    """Return a pattern function with a horizontal center band."""

    def fn(r: int, c: int, rows: int, cols: int) -> str:
        return band if rows // 3 <= r < 2 * rows // 3 else outer

    return fn


def _center_band_v(outer: str, band: str) -> _PatternFn:
    """Return a pattern function with a vertical center band."""

    def fn(r: int, c: int, rows: int, cols: int) -> str:
        return band if cols // 3 <= c < 2 * cols // 3 else outer

    return fn


def _cross(background: str, cross_color: str) -> _PatternFn:
    """Return a pattern function with a horizontal/vertical cross."""

    def fn(r: int, c: int, rows: int, cols: int) -> str:
        thick = max(1, rows // 4)
        if abs(r - rows // 2) < thick or abs(c - cols // 2) < thick:
            return cross_color
        return background

    return fn


def _saltire(background: str, cross_color: str) -> _PatternFn:
    """Return a pattern function with a diagonal X cross (saltire)."""

    def fn(r: int, c: int, rows: int, cols: int) -> str:
        fr = r / (rows - 1) if rows > 1 else 0.5
        fc = c / (cols - 1) if cols > 1 else 0.5
        if (
            abs(fr - fc) < _SALTIRE_THRESHOLD
            or abs(fr - (1.0 - fc)) < _SALTIRE_THRESHOLD
        ):
            return cross_color
        return background

    return fn


def _inner_square(outer: str, inner: str) -> _PatternFn:
    """Return a pattern function with an outer border and inner filled square."""

    def fn(r: int, c: int, rows: int, cols: int) -> str:
        mr = max(1, rows // 4)
        mc = max(1, cols // 4)
        if mr <= r < rows - mr and mc <= c < cols - mc:
            return inner
        return outer

    return fn


def _three_nested(outer: str, mid: str, inner: str) -> _PatternFn:
    """Return a pattern function with three nested rectangles."""

    def fn(r: int, c: int, rows: int, cols: int) -> str:
        mr1, mc1 = max(1, rows // 5), max(1, cols // 5)
        mr2, mc2 = max(1, rows // 3), max(1, cols // 3)
        if mr2 <= r < rows - mr2 and mc2 <= c < cols - mc2:
            return inner
        if mr1 <= r < rows - mr1 and mc1 <= c < cols - mc1:
            return mid
        return outer

    return fn


def _diamond(background: str, diamond_color: str) -> _PatternFn:
    """Return a pattern function with a diamond (rotated square) shape."""

    def fn(r: int, c: int, rows: int, cols: int) -> str:
        cr = (rows - 1) / 2.0
        cc = (cols - 1) / 2.0
        dr = abs(r - cr) / rows
        dc = abs(c - cc) / cols
        if dr + dc < _DIAMOND_THRESHOLD:
            return diamond_color
        return background

    return fn


def _circle(background: str, circle_color: str) -> _PatternFn:
    """Return a pattern function with an approximate circle."""

    def fn(r: int, c: int, rows: int, cols: int) -> str:
        cr = (rows - 1) / 2.0
        cc = (cols - 1) / 2.0
        dr = (r - cr) / rows
        dc = (c - cc) / cols
        if dr * dr + dc * dc < _CIRCLE_THRESHOLD:
            return circle_color
        return background

    return fn


def _diagonal_split(upper_left: str, lower_right: str) -> _PatternFn:
    """Return a pattern function divided diagonally (upper-left / lower-right)."""

    def fn(r: int, c: int, rows: int, cols: int) -> str:
        return upper_left if r / rows + c / cols < 1.0 else lower_right

    return fn


def _diagonal_stripes(color1: str, color2: str, n: int) -> _PatternFn:
    """Return a pattern function with diagonal stripes at 45 degrees."""

    def fn(r: int, c: int, rows: int, cols: int) -> str:
        return color1 if ((r + c) * n // (rows + cols)) % 2 == 0 else color2

    return fn


def _per_saltire(top: str, right: str, bottom: str, left: str) -> _PatternFn:
    """Return a pattern function with four diagonal triangles (per saltire)."""

    def fn(r: int, c: int, rows: int, cols: int) -> str:
        fr = r / rows - 0.5
        fc = c / cols - 0.5
        if abs(fr) > abs(fc):
            return top if fr < 0 else bottom
        return left if fc < 0 else right

    return fn


# ---------------------------------------------------------------------------
# ICS signal flag patterns - character to pattern function
# ---------------------------------------------------------------------------

FLAG_PATTERNS: dict[str, _PatternFn] = {
    # Letters A-Z
    "A": _vertical_split("W", "B"),  # Alfa: white/blue vertical
    "B": _solid("R"),  # Bravo: solid red
    "C": _horizontal_stripes("B", "W", "R", "W", "B"),  # Charlie: 5 horizontal stripes
    "D": _center_band_h("Y", "B"),  # Delta: gold, blue center band
    "E": _horizontal_split("B", "R"),  # Echo: blue top / red bottom
    "F": _diamond("W", "R"),  # Foxtrot: white, red diamond
    "G": _vertical_stripes(
        "Y", "B", "Y", "B", "Y", "B"
    ),  # Golf: 6 alternating V-stripes
    "H": _vertical_split("W", "R"),  # Hotel: white/red vertical
    "I": _circle("Y", "K"),  # India: gold, black circle
    "J": _center_band_h("B", "W"),  # Juliett: blue, white center band
    "K": _vertical_split("Y", "B"),  # Kilo: gold/blue vertical
    "L": _four_quarters("Y", "K", "K", "Y"),  # Lima: gold/black quarters
    "M": _saltire("B", "W"),  # Mike: blue, white saltire
    "N": _checkerboard("B", "W", 4),  # November: 4x4 blue/white check
    "O": _diagonal_split("R", "Y"),  # Oscar: red/gold diagonal
    "P": _inner_square("B", "W"),  # Papa: blue border, white inner
    "Q": _solid("Y"),  # Quebec: solid gold
    "R": _cross("R", "Y"),  # Romeo: red, gold cross
    "S": _inner_square("W", "B"),  # Sierra: white border, blue inner
    "T": _vertical_stripes("R", "W", "B"),  # Tango: red/white/blue vertical
    "U": _four_quarters("R", "W", "W", "R"),  # Uniform: red/white quarters
    "V": _saltire("W", "R"),  # Victor: white, red saltire
    "W": _three_nested("B", "W", "R"),  # Whiskey: blue/white/red nested
    "X": _cross("W", "B"),  # X-ray: white, blue cross
    "Y": _diagonal_stripes("Y", "R", 5),  # Yankee: diagonal gold/red stripes
    "Z": _per_saltire("R", "Y", "B", "K"),  # Zulu: R/Y/B/K saltire quarters
    # Numerals 0-9 (ICS versions)
    "0": _center_band_v("Y", "R"),  # Zero: gold, red vertical band
    "1": _circle("W", "R"),  # One: white, red circle
    "2": _circle("B", "W"),  # Two: blue, white circle
    "3": _vertical_stripes("R", "W", "B"),  # Three: red/white/blue vertical
    "4": _saltire("R", "W"),  # Four: red, white saltire
    "5": _vertical_split("Y", "B"),  # Five: gold/blue vertical
    "6": _horizontal_split("K", "W"),  # Six: black top / white bottom
    "7": _horizontal_split("Y", "R"),  # Seven: gold top / red bottom
    "8": _saltire("W", "R"),  # Eight: white, red saltire
    "9": _four_quarters("W", "K", "R", "Y"),  # Nine: W/K/R/Y quarters
}

# Phonetic / spoken name for each supported character
PHONETIC_NAMES: dict[str, str] = {
    "A": "Alfa",
    "B": "Bravo",
    "C": "Charlie",
    "D": "Delta",
    "E": "Echo",
    "F": "Foxtrot",
    "G": "Golf",
    "H": "Hotel",
    "I": "India",
    "J": "Juliett",
    "K": "Kilo",
    "L": "Lima",
    "M": "Mike",
    "N": "November",
    "O": "Oscar",
    "P": "Papa",
    "Q": "Quebec",
    "R": "Romeo",
    "S": "Sierra",
    "T": "Tango",
    "U": "Uniform",
    "V": "Victor",
    "W": "Whiskey",
    "X": "X-ray",
    "Y": "Yankee",
    "Z": "Zulu",
    "0": "Zero",
    "1": "One",
    "2": "Two",
    "3": "Three",
    "4": "Four",
    "5": "Five",
    "6": "Six",
    "7": "Seven",
    "8": "Eight",
    "9": "Niner",
}


# ---------------------------------------------------------------------------
# Rendering functions
# ---------------------------------------------------------------------------


def render_flag(
    char: str,
    rows: int = _ROWS,
    cols: int = _COLS,
    ascii_mode: bool = False,
) -> list[str]:
    """Render a single ICS flag as a list of terminal-ready strings.

    Args:
        char: Single character (A-Z or 0-9, case-insensitive).
        rows: Height of the rendered flag in cell rows.
        cols: Width of the rendered flag in cell columns.
        ascii_mode: Render with monochrome ASCII characters instead of ANSI
            colors. Suitable for NO_COLOR terminals.

    Returns:
        List of strings, one per row. Empty list for unsupported characters.
    """
    key = char.upper()
    pattern = FLAG_PATTERNS.get(key)
    if pattern is None:
        return []
    lines: list[str] = []
    for r in range(rows):
        line = ""
        for c in range(cols):
            color = pattern(r, c, rows, cols)
            if ascii_mode:
                line += _ASCII_CHARS.get(color, "  ")
            else:
                line += _ANSI_BG.get(color, "") + "  " + RESET
        lines.append(line)
    return lines


def display_text(text: str, ascii_mode: bool = False) -> None:
    """Render and print ICS flags for each character in text.

    A-Z and 0-9 are rendered as flags. Spaces insert a blank-line separator.
    Unrecognised characters are silently skipped.

    Args:
        text: Input string to convert to flags.
        ascii_mode: If True, use monochrome ASCII output (NO_COLOR compatible).
    """
    valid = [ch.upper() for ch in text if ch.upper() in FLAG_PATTERNS or ch == " "]
    if not valid:
        print("No valid characters to display. Supported: A-Z, 0-9.")
        return
    for ch in valid:
        if ch == " ":
            print()
            continue
        for line in render_flag(ch, ascii_mode=ascii_mode):
            print(line)
        print(f" {ch} - {PHONETIC_NAMES.get(ch, ch)}")
        print()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Entry point for the naval_flags CLI.

    Usage:
        naval_flags TEXT [--ascii]
    """
    parser = argparse.ArgumentParser(
        prog="naval_flags",
        description="Convert text to International Code of Signals (ICS) naval flags.",
    )
    parser.add_argument("text", help="Text to display as ICS flags (A-Z, 0-9)")
    parser.add_argument(
        "--ascii",
        action="store_true",
        help="Render in monochrome ASCII mode (NO_COLOR compatible)",
    )
    args = parser.parse_args()
    display_text(args.text, ascii_mode=args.ascii)


if __name__ == "__main__":
    main()
