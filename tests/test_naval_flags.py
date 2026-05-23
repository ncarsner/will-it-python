"""Tests for naval_flags module."""

from unittest.mock import patch

import pytest

from will_it_python.naval_flags import (
    _ANSI_BG,
    _ASCII_CHARS,
    _COLS,
    _ROWS,
    FLAG_PATTERNS,
    PHONETIC_NAMES,
    RESET,
    _center_band_h,
    _center_band_v,
    _checkerboard,
    _circle,
    _cross,
    _diagonal_split,
    _diagonal_stripes,
    _diamond,
    _four_quarters,
    _horizontal_split,
    _horizontal_stripes,
    _inner_square,
    _per_saltire,
    _saltire,
    _solid,
    _three_nested,
    _vertical_split,
    _vertical_stripes,
    display_text,
    main,
    render_flag,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_flag_patterns_has_all_chars():
    expected = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    assert set(FLAG_PATTERNS.keys()) == expected


def test_phonetic_names_has_all_chars():
    expected = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    assert set(PHONETIC_NAMES.keys()) == expected


def test_ansi_bg_has_all_colors():
    for code in ("W", "B", "R", "Y", "K"):
        assert code in _ANSI_BG
        assert _ANSI_BG[code].startswith("\033[")


def test_ascii_chars_has_all_colors():
    for code in ("W", "B", "R", "Y", "K"):
        assert code in _ASCII_CHARS
        assert len(_ASCII_CHARS[code]) == 2


# ---------------------------------------------------------------------------
# Pattern factories — branch coverage
# ---------------------------------------------------------------------------


def test_solid_always_returns_color():
    fn = _solid("R")
    assert fn(0, 0, 6, 10) == "R"
    assert fn(5, 9, 6, 10) == "R"


def test_vertical_split_left_and_right():
    fn = _vertical_split("W", "B")
    assert fn(0, 0, 6, 10) == "W"  # left half
    assert fn(0, 9, 6, 10) == "B"  # right half


def test_horizontal_split_top_and_bottom():
    fn = _horizontal_split("B", "R")
    assert fn(0, 0, 6, 10) == "B"  # top half
    assert fn(5, 0, 6, 10) == "R"  # bottom half


def test_horizontal_stripes_all_bands():
    fn = _horizontal_stripes("B", "W", "R", "W", "B")
    # rows=5 → each row maps 1:1
    assert fn(0, 0, 5, 10) == "B"
    assert fn(1, 0, 5, 10) == "W"
    assert fn(2, 0, 5, 10) == "R"
    assert fn(3, 0, 5, 10) == "W"
    assert fn(4, 0, 5, 10) == "B"


def test_vertical_stripes_all_bands():
    fn = _vertical_stripes("R", "W", "B")
    # cols=3 → each col maps 1:1
    assert fn(0, 0, 6, 3) == "R"
    assert fn(0, 1, 6, 3) == "W"
    assert fn(0, 2, 6, 3) == "B"


def test_checkerboard_alternates():
    fn = _checkerboard("B", "W", 4)
    c1 = fn(0, 0, 6, 10)
    c2 = fn(0, 3, 6, 10)
    assert c1 in ("B", "W")
    assert c2 in ("B", "W")
    # adjacent cells in the same n-block should differ when block parity differs
    fn2 = _checkerboard("B", "W", 2)
    assert fn2(0, 0, 4, 4) != fn2(0, 2, 4, 4)


def test_four_quarters_all_four():
    fn = _four_quarters("Y", "K", "K", "Y")
    assert fn(0, 0, 6, 10) == "Y"  # TL
    assert fn(0, 9, 6, 10) == "K"  # TR
    assert fn(5, 0, 6, 10) == "K"  # BL
    assert fn(5, 9, 6, 10) == "Y"  # BR


def test_center_band_h_outer_and_inner():
    fn = _center_band_h("Y", "B")
    rows = 6
    # rows//3 = 2; 2*rows//3 = 4 → band is rows 2,3
    assert fn(0, 0, rows, 10) == "Y"  # outer (row 0)
    assert fn(2, 0, rows, 10) == "B"  # band (row 2)
    assert fn(5, 0, rows, 10) == "Y"  # outer (row 5)


def test_center_band_v_outer_and_inner():
    fn = _center_band_v("Y", "R")
    cols = 10
    # cols//3 = 3; 2*cols//3 = 6 → band is cols 3..5
    assert fn(0, 0, 6, cols) == "Y"  # outer
    assert fn(0, 4, 6, cols) == "R"  # band
    assert fn(0, 9, 6, cols) == "Y"  # outer


def test_cross_center_and_background():
    fn = _cross("W", "B")
    rows, cols = 6, 10
    # Thick = max(1, 6//4) = 1; center row = 3, center col = 5
    assert fn(3, 0, rows, cols) == "B"  # center row → cross
    assert fn(0, 5, rows, cols) == "B"  # center col → cross
    assert fn(0, 0, rows, cols) == "W"  # corner → background


def test_saltire_diagonal_and_background():
    fn = _saltire("W", "R")
    rows, cols = 6, 10
    assert fn(0, 0, rows, cols) == "R"  # top-left corner on diagonal
    assert fn(5, 9, rows, cols) == "R"  # bottom-right on diagonal
    assert fn(3, 0, rows, cols) == "W"  # off-diagonal → background


def test_saltire_edge_case_single_cell():
    fn = _saltire("W", "R")
    # rows=1, cols=1 → both fr and fc = 0.5; |0.5-0.5|=0 < 0.2 → cross
    result = fn(0, 0, 1, 1)
    assert result == "R"


def test_inner_square_outer_and_inner():
    fn = _inner_square("B", "W")
    rows, cols = 6, 10
    # mr = max(1, 6//4) = 1; mc = max(1, 10//4) = 2
    assert fn(0, 0, rows, cols) == "B"  # border
    assert fn(3, 5, rows, cols) == "W"  # inner square


def test_three_nested_all_three_regions():
    fn = _three_nested("B", "W", "R")
    rows, cols = 6, 10
    assert fn(0, 0, rows, cols) == "B"  # outer
    assert fn(1, 2, rows, cols) == "W"  # mid ring
    assert fn(3, 5, rows, cols) == "R"  # inner


def test_diamond_center_and_background():
    fn = _diamond("W", "R")
    # Center pixel should be diamond color
    assert fn(3, 5, 6, 10) == "R"
    # Corner should be background
    assert fn(0, 0, 6, 10) == "W"


def test_circle_center_and_background():
    fn = _circle("Y", "K")
    # Center pixel
    assert fn(3, 5, 6, 10) == "K"
    # Corner
    assert fn(0, 0, 6, 10) == "Y"


def test_diagonal_split_both_sides():
    fn = _diagonal_split("R", "Y")
    rows, cols = 6, 10
    # Upper-left corner → R
    assert fn(0, 0, rows, cols) == "R"
    # Lower-right corner → Y
    assert fn(5, 9, rows, cols) == "Y"


def test_diagonal_stripes_both_colors():
    fn = _diagonal_stripes("Y", "R", 5)
    rows, cols = 6, 10
    results = {fn(r, c, rows, cols) for r in range(rows) for c in range(cols)}
    assert "Y" in results
    assert "R" in results


def test_per_saltire_all_four_triangles():
    fn = _per_saltire("R", "Y", "B", "K")
    rows, cols = 6, 10
    # Top triangle: top-center pixel  → fr<0, abs(fr)>abs(fc)
    assert fn(0, 5, rows, cols) == "R"
    # Bottom triangle: bottom-center pixel → fr>0
    assert fn(5, 5, rows, cols) == "B"
    # Left triangle: left-center pixel → fc<0
    assert fn(3, 0, rows, cols) == "K"
    # Right triangle: right-center pixel → fc>0
    assert fn(3, 9, rows, cols) == "Y"


# ---------------------------------------------------------------------------
# render_flag
# ---------------------------------------------------------------------------


def test_render_flag_returns_correct_row_count():
    lines = render_flag("A")
    assert len(lines) == _ROWS


def test_render_flag_custom_dimensions():
    lines = render_flag("B", rows=3, cols=4)
    assert len(lines) == 3


def test_render_flag_unknown_char_returns_empty():
    assert render_flag("!") == []
    assert render_flag("@") == []
    assert render_flag(" ") == []


def test_render_flag_lowercase_normalized():
    upper = render_flag("A")
    lower = render_flag("a")
    assert upper == lower


def test_render_flag_ansi_mode_contains_escape_codes():
    lines = render_flag("B")  # solid red
    assert any("\033[" in line for line in lines)
    assert any(RESET in line for line in lines)


def test_render_flag_ascii_mode_no_escape_codes():
    lines = render_flag("B", ascii_mode=True)
    assert all("\033[" not in line for line in lines)
    # Solid red → all "##"
    assert all(line == "##" * _COLS for line in lines)


def test_render_flag_ascii_line_width():
    lines = render_flag("A", ascii_mode=True)
    for line in lines:
        assert len(line) == _COLS * 2


# ---------------------------------------------------------------------------
# All 36 flags produce correct colors at key positions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("char", "pos", "expected_color"),
    [
        # Letters
        ("A", (0, 0), "W"),  # Alfa: left = white
        ("A", (0, 9), "B"),  # Alfa: right = blue
        ("B", (3, 5), "R"),  # Bravo: solid red
        ("C", (0, 0), "B"),  # Charlie: top stripe = blue
        ("D", (3, 5), "B"),  # Delta: center band = blue
        ("D", (0, 0), "Y"),  # Delta: outer = gold
        ("E", (0, 0), "B"),  # Echo: top = blue
        ("E", (5, 0), "R"),  # Echo: bottom = red
        ("F", (3, 5), "R"),  # Foxtrot: center = diamond (red)
        ("F", (0, 0), "W"),  # Foxtrot: corner = white
        ("G", (0, 0), "Y"),  # Golf: first stripe = gold
        ("G", (0, 2), "B"),  # Golf: second stripe = blue
        ("H", (0, 0), "W"),  # Hotel: left = white
        ("H", (0, 9), "R"),  # Hotel: right = red
        ("I", (3, 5), "K"),  # India: center circle = black
        ("I", (0, 0), "Y"),  # India: corner = gold
        ("J", (3, 5), "W"),  # Juliett: center band = white
        ("J", (0, 0), "B"),  # Juliett: outer = blue
        ("K", (0, 0), "Y"),  # Kilo: left = gold
        ("K", (0, 9), "B"),  # Kilo: right = blue
        ("L", (0, 0), "Y"),  # Lima: TL = gold
        ("L", (0, 9), "K"),  # Lima: TR = black
        ("M", (0, 0), "W"),  # Mike: corner on main diagonal → cross color (white)
        ("N", (0, 0), "B"),  # November: first checker cell
        ("O", (0, 0), "R"),  # Oscar: upper-left = red
        ("O", (5, 9), "Y"),  # Oscar: lower-right = gold
        ("P", (0, 0), "B"),  # Papa: border = blue
        ("P", (3, 5), "W"),  # Papa: inner = white
        ("Q", (0, 0), "Y"),  # Quebec: solid gold
        ("R", (3, 5), "Y"),  # Romeo: center = cross (gold)
        ("R", (0, 0), "R"),  # Romeo: corner = background (red)
        ("S", (0, 0), "W"),  # Sierra: border = white
        ("S", (3, 5), "B"),  # Sierra: inner = blue
        ("T", (0, 0), "R"),  # Tango: left stripe = red
        ("T", (0, 9), "B"),  # Tango: right stripe = blue
        ("U", (0, 0), "R"),  # Uniform: TL = red
        ("U", (0, 9), "W"),  # Uniform: TR = white
        ("V", (0, 0), "R"),  # Victor: diagonal → cross color
        ("W", (0, 0), "B"),  # Whiskey: outer = blue
        ("W", (3, 5), "R"),  # Whiskey: inner = red
        ("X", (3, 5), "B"),  # X-ray: center = cross (blue)
        ("X", (0, 0), "W"),  # X-ray: corner = white
        ("Y", (0, 0), "Y"),  # Yankee: first stripe = gold
        ("Z", (0, 5), "R"),  # Zulu: top triangle = red
        ("Z", (5, 5), "B"),  # Zulu: bottom triangle = blue
        # Numerals
        ("0", (0, 4), "R"),  # Zero: center band = red
        ("0", (0, 0), "Y"),  # Zero: outer = gold
        ("1", (3, 5), "R"),  # One: center = red circle
        ("1", (0, 0), "W"),  # One: corner = white
        ("2", (3, 5), "W"),  # Two: center = white circle
        ("2", (0, 0), "B"),  # Two: corner = blue
        ("3", (0, 0), "R"),  # Three: left stripe = red
        ("4", (0, 0), "W"),  # Four: corner on main diagonal → cross color (white)
        ("5", (0, 0), "Y"),  # Five: left = gold
        ("5", (0, 9), "B"),  # Five: right = blue
        ("6", (0, 0), "K"),  # Six: top = black
        ("6", (5, 0), "W"),  # Six: bottom = white
        ("7", (0, 0), "Y"),  # Seven: top = gold
        ("7", (5, 0), "R"),  # Seven: bottom = red
        ("8", (0, 0), "R"),  # Eight: diagonal → cross color (red)
        ("9", (0, 0), "W"),  # Nine: TL = white
        ("9", (0, 9), "K"),  # Nine: TR = black
    ],
)
def test_flag_color_at_position(char, pos, expected_color):
    r, c = pos
    pattern = FLAG_PATTERNS[char]
    result = pattern(r, c, _ROWS, _COLS)
    assert result == expected_color, (
        f"Flag {char!r} at ({r},{c}): expected {expected_color!r}, got {result!r}"
    )


# ---------------------------------------------------------------------------
# display_text
# ---------------------------------------------------------------------------


def test_display_text_valid_letter(capsys):
    display_text("A")
    out, _ = capsys.readouterr()
    assert "A" in out
    assert "Alfa" in out


def test_display_text_valid_digit(capsys):
    display_text("5")
    out, _ = capsys.readouterr()
    assert "Five" in out


def test_display_text_space_inserts_blank_line(capsys):
    display_text("A B")
    out, _ = capsys.readouterr()
    lines = out.split("\n")
    # Should have content for A, blank separator, content for B
    assert any(line == "" for line in lines)


def test_display_text_unknown_only_shows_message(capsys):
    display_text("!@#$")
    out, _ = capsys.readouterr()
    assert "No valid characters" in out


def test_display_text_empty_string_shows_message(capsys):
    display_text("")
    out, _ = capsys.readouterr()
    assert "No valid characters" in out


def test_display_text_mixed_valid_and_invalid(capsys):
    display_text("A!B")  # ! skipped, A and B rendered
    out, _ = capsys.readouterr()
    assert "Alfa" in out
    assert "Bravo" in out


def test_display_text_ascii_mode(capsys):
    display_text("B", ascii_mode=True)
    out, _ = capsys.readouterr()
    assert "\033[" not in out  # no ANSI codes
    assert "Bravo" in out


def test_display_text_lowercase_input(capsys):
    display_text("sos")
    out, _ = capsys.readouterr()
    assert "Sierra" in out
    assert "Oscar" in out


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def test_main_renders_text(capsys):
    with patch("sys.argv", ["naval_flags", "AB"]):
        main()
    out, _ = capsys.readouterr()
    assert "Alfa" in out
    assert "Bravo" in out


def test_main_ascii_flag(capsys):
    with patch("sys.argv", ["naval_flags", "--ascii", "Q"]):
        main()
    out, _ = capsys.readouterr()
    assert "\033[" not in out
    assert "Quebec" in out


def test_main_with_digits(capsys):
    with patch("sys.argv", ["naval_flags", "42"]):
        main()
    out, _ = capsys.readouterr()
    assert "Four" in out
    assert "Two" in out
