#!/usr/bin/env python3
"""Personality Space — interactive 3D/2D scatter plot of persons by personality axes.

Maps PersonProfile instances onto configurable personality-system axes
(Zodiac, Enneagram with wings, MBTI). Runs as a Dash web application with
live axis-swap controls, a 2D/3D toggle, and an in-browser form to add persons.

Run with:
    personalities [--port 8050] [--debug]
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from dataclasses import dataclass
from enum import IntEnum, StrEnum

import dash
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html

logger = logging.getLogger(__name__)

_ENNEAGRAM_MIN_TYPE: int = 1
_ENNEAGRAM_MAX_TYPE: int = 9
_MBTI_CODE_LENGTH: int = 4
_COORD_EPSILON: float = 1e-9

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ZodiacSign(IntEnum):
    """The twelve Western zodiac signs in calendar order."""

    ARIES = 0
    TAURUS = 1
    GEMINI = 2
    CANCER = 3
    LEO = 4
    VIRGO = 5
    LIBRA = 6
    SCORPIO = 7
    SAGITTARIUS = 8
    CAPRICORN = 9
    AQUARIUS = 10
    PISCES = 11


class PersonalityDimension(StrEnum):
    """The three personality systems available as visualization axes."""

    ZODIAC = "zodiac"
    ENNEAGRAM = "enneagram"
    MBTI = "mbti"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

# Valid wing pairs for each Enneagram type (type → set of valid wing values).
_VALID_WINGS: dict[int, set[int]] = {
    1: {9, 2},
    2: {1, 3},
    3: {2, 4},
    4: {3, 5},
    5: {4, 6},
    6: {5, 7},
    7: {6, 8},
    8: {7, 9},
    9: {8, 1},
}


@dataclass
class EnneagramType:
    """An Enneagram personality type with its dominant wing.

    Args:
        type_num: Core type, 1-9.
        wing: The adjacent type that flavors this type (e.g. 4w5 has wing=5).

    Raises:
        ValueError: If type_num is outside 1-9, or wing is not adjacent.
    """

    type_num: int
    wing: int

    def __post_init__(self) -> None:
        """Validate type_num and wing on construction."""
        if self.type_num not in _VALID_WINGS:
            raise ValueError(
                f"type_num must be {_ENNEAGRAM_MIN_TYPE}-{_ENNEAGRAM_MAX_TYPE}, "
                f"got {self.type_num!r}"
            )
        valid = _VALID_WINGS[self.type_num]
        if self.wing not in valid:
            raise ValueError(
                f"wing must be one of {sorted(valid)} for type {self.type_num}, "
                f"got {self.wing!r}"
            )

    def to_coord(self) -> float:
        """Return a numeric coordinate encoding type and wing direction.

        The wing is encoded as a +-0.25 offset from the core type number.
        Type 1 wing 9 (1w9) maps to 0.75; type 9 wing 1 (9w1) maps to 9.25.

        Returns:
            Float in the range [0.75, 9.25].
        """
        if self.type_num == _ENNEAGRAM_MAX_TYPE and self.wing == _ENNEAGRAM_MIN_TYPE:
            return 9.25
        if self.type_num == _ENNEAGRAM_MIN_TYPE and self.wing == _ENNEAGRAM_MAX_TYPE:
            return 0.75
        if self.wing < self.type_num:
            return float(self.type_num) - 0.25
        return float(self.type_num) + 0.25

    def label(self) -> str:
        """Return the human-readable label, e.g. '4w5'.

        Returns:
            String in the form '<type>w<wing>'.
        """
        return f"{self.type_num}w{self.wing}"


@dataclass
class MBTIType:
    """An MBTI personality type defined by its four dichotomies.

    Args:
        extraverted: True for E, False for I.
        intuitive: True for N, False for S.
        thinking: True for T, False for F.
        judging: True for J, False for P.
    """

    extraverted: bool
    intuitive: bool
    thinking: bool
    judging: bool

    def to_coord(self) -> int:
        """Return an integer 0-15 via 4-bit encoding (bit3=E, bit2=N, bit1=T, bit0=J).

        Returns:
            Integer in [0, 15]. ENTJ=15, ENFP=12, ISTJ=3, INFP=4.
        """
        return (
            (int(self.extraverted) << 3)
            | (int(self.intuitive) << 2)
            | (int(self.thinking) << 1)
            | int(self.judging)
        )

    def label(self) -> str:
        """Return the four-letter MBTI code, e.g. 'ENFP'.

        Returns:
            Four-character uppercase string.
        """
        return (
            ("E" if self.extraverted else "I")
            + ("N" if self.intuitive else "S")
            + ("T" if self.thinking else "F")
            + ("J" if self.judging else "P")
        )

    @classmethod
    def from_str(cls, code: str) -> MBTIType:
        """Parse a four-letter MBTI code string into an MBTIType.

        Args:
            code: Four-letter code e.g. 'ENFP', 'ISTJ'. Case-insensitive.

        Returns:
            MBTIType instance.

        Raises:
            ValueError: If the code is not exactly 4 characters or contains
                characters invalid for their position.
        """
        normalized = code.strip().upper()
        if len(normalized) != _MBTI_CODE_LENGTH:
            raise ValueError(
                "MBTI code must be exactly 4 characters, "
                f"got {len(normalized)}: {code!r}"
            )
        ei, ns, tf, jp = normalized[0], normalized[1], normalized[2], normalized[3]
        if ei not in ("E", "I"):
            raise ValueError(f"First character must be E or I, got {ei!r} in {code!r}")
        if ns not in ("N", "S"):
            raise ValueError(f"Second character must be N or S, got {ns!r} in {code!r}")
        if tf not in ("T", "F"):
            raise ValueError(f"Third character must be T or F, got {tf!r} in {code!r}")
        if jp not in ("J", "P"):
            raise ValueError(f"Fourth character must be J or P, got {jp!r} in {code!r}")
        return cls(
            extraverted=(ei == "E"),
            intuitive=(ns == "N"),
            thinking=(tf == "T"),
            judging=(jp == "J"),
        )


@dataclass
class PersonProfile:
    """A person's personality profile with optional system values.

    Any dimension may be None; missing dimensions are handled gracefully
    during visualization (midpoint placement with a hollow marker).

    Args:
        name: Display name for this person.
        zodiac: Western zodiac sign, or None if unknown.
        enneagram: Enneagram type with wing, or None if unknown.
        mbti: MBTI type, or None if unknown.
    """

    name: str
    zodiac: ZodiacSign | None = None
    enneagram: EnneagramType | None = None
    mbti: MBTIType | None = None


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_PERSONS: list[PersonProfile] = [
    PersonProfile(
        name="Alice",
        zodiac=ZodiacSign.SCORPIO,
        enneagram=EnneagramType(type_num=4, wing=5),
        mbti=MBTIType.from_str("INFJ"),
    ),
    PersonProfile(
        name="Bob",
        zodiac=ZodiacSign.ARIES,
        enneagram=EnneagramType(type_num=8, wing=7),
        mbti=MBTIType.from_str("ESTJ"),
    ),
    PersonProfile(
        name="Carol",
        zodiac=ZodiacSign.LIBRA,
        enneagram=EnneagramType(type_num=2, wing=3),
        mbti=MBTIType.from_str("ENFP"),
    ),
    PersonProfile(
        name="Dave",
        zodiac=ZodiacSign.AQUARIUS,
        enneagram=EnneagramType(type_num=5, wing=4),
        mbti=None,  # intentionally missing to exercise missing-data path
    ),
    PersonProfile(
        name="Eve",
        zodiac=None,  # intentionally missing to exercise missing-data path
        enneagram=EnneagramType(type_num=7, wing=8),
        mbti=MBTIType.from_str("ENTP"),
    ),
]

# ---------------------------------------------------------------------------
# Coordinate & tick helpers
# ---------------------------------------------------------------------------

_MIDPOINTS: dict[PersonalityDimension, float] = {
    PersonalityDimension.ZODIAC: 5.5,
    PersonalityDimension.ENNEAGRAM: 5.0,
    PersonalityDimension.MBTI: 7.5,
}

# Distance from midpoint to the outermost tick on each axis.
_HALF_RANGES: dict[PersonalityDimension, float] = {
    PersonalityDimension.ZODIAC: 5.5,     # 0-11, center 5.5
    PersonalityDimension.ENNEAGRAM: 4.25,  # 0.75-9.25, center 5.0
    PersonalityDimension.MBTI: 7.5,       # 0-15, center 7.5
}


def get_coord(person: PersonProfile, dim: PersonalityDimension) -> float | None:
    """Return the numeric coordinate for a person on the given dimension.

    Args:
        person: The person to look up.
        dim: Which personality dimension to query.

    Returns:
        A float coordinate, or None if the person lacks data for this dimension.
    """
    match dim:
        case PersonalityDimension.ZODIAC:
            return float(person.zodiac) if person.zodiac is not None else None
        case PersonalityDimension.ENNEAGRAM:
            return person.enneagram.to_coord() if person.enneagram is not None else None
        case PersonalityDimension.MBTI:
            return float(person.mbti.to_coord()) if person.mbti is not None else None
        case _:  # pragma: no cover
            raise AssertionError(f"Unhandled dimension: {dim!r}")


def get_tick_values(dim: PersonalityDimension) -> list[float]:
    """Return all valid tick positions for the given axis.

    Args:
        dim: The personality dimension.

    Returns:
        Sorted list of float tick positions.
        ZODIAC: 12 values (0.0-11.0).
        ENNEAGRAM: 18 values (9 types x 2 wing offsets).
        MBTI: 16 values (0.0-15.0).
    """
    match dim:
        case PersonalityDimension.ZODIAC:
            return [float(v) for v in range(12)]
        case PersonalityDimension.ENNEAGRAM:
            return sorted(
                EnneagramType(t, w).to_coord()
                for t in range(1, 10)
                for w in _VALID_WINGS[t]
            )
        case PersonalityDimension.MBTI:
            return [float(v) for v in range(16)]
        case _:  # pragma: no cover
            raise AssertionError(f"Unhandled dimension: {dim!r}")


def get_tick_labels(dim: PersonalityDimension) -> list[str]:
    """Return human-readable tick label strings aligned to get_tick_values order.

    Args:
        dim: The personality dimension.

    Returns:
        List of label strings in the same order as get_tick_values(dim).
    """
    match dim:
        case PersonalityDimension.ZODIAC:
            return [z.name.capitalize() for z in ZodiacSign]
        case PersonalityDimension.ENNEAGRAM:
            pairs = sorted(
                (EnneagramType(t, w).to_coord(), EnneagramType(t, w).label())
                for t in range(1, 10)
                for w in _VALID_WINGS[t]
            )
            return [label for _, label in pairs]
        case PersonalityDimension.MBTI:
            return [
                MBTIType(
                    extraverted=bool(i & 8),
                    intuitive=bool(i & 4),
                    thinking=bool(i & 2),
                    judging=bool(i & 1),
                ).label()
                for i in range(16)
            ]
        case _:  # pragma: no cover
            raise AssertionError(f"Unhandled dimension: {dim!r}")


def get_label(dim: PersonalityDimension, coord: float) -> str:
    """Return the human-readable label for a coordinate on the given axis.

    Args:
        dim: The personality dimension.
        coord: A numeric coordinate value from get_tick_values(dim).

    Returns:
        Human-readable string label, or the coordinate formatted as a string
        if no match is found.
    """
    tick_vals = get_tick_values(dim)
    tick_lbls = get_tick_labels(dim)
    for val, lbl in zip(tick_vals, tick_lbls, strict=False):
        if abs(val - coord) < _COORD_EPSILON:
            return lbl
    return str(coord)


def get_axis_half_range(dim: PersonalityDimension) -> float:
    """Return the half-range of the axis (distance from midpoint to far end).

    Args:
        dim: The personality dimension.

    Returns:
        Positive float representing the half-span of the axis.
    """
    return _HALF_RANGES[dim]


def get_pole_labels(dim: PersonalityDimension) -> tuple[str, str]:
    """Return human-readable labels for the lower and upper halves of an axis.

    Args:
        dim: The personality dimension.

    Returns:
        Tuple of (lower_pole_label, upper_pole_label).
    """
    match dim:
        case PersonalityDimension.ZODIAC:
            return ("Aries-Virgo", "Libra-Pisces")
        case PersonalityDimension.ENNEAGRAM:
            return ("Types 1-4", "Types 5-9")
        case PersonalityDimension.MBTI:
            return ("Introverted", "Extraverted")
        case _:  # pragma: no cover
            raise AssertionError(f"Unhandled dimension: {dim!r}")


# ---------------------------------------------------------------------------
# Serialization helpers (for dcc.Store)
# ---------------------------------------------------------------------------


def _profile_to_dict(person: PersonProfile) -> dict[str, object]:
    """Serialize a PersonProfile to a JSON-safe dict.

    Args:
        person: The profile to serialize.

    Returns:
        Dict with primitive values suitable for json.dumps.
    """
    ennea: dict[str, int] | None = None
    if person.enneagram is not None:
        ennea = {
            "type_num": person.enneagram.type_num,
            "wing": person.enneagram.wing,
        }
    mbti_str: str | None = None
    if person.mbti is not None:
        mbti_str = person.mbti.label()
    return {
        "name": person.name,
        "zodiac": int(person.zodiac) if person.zodiac is not None else None,
        "enneagram": ennea,
        "mbti": mbti_str,
    }


def _profile_from_dict(data: dict[str, object]) -> PersonProfile:
    """Deserialize a PersonProfile from a dict produced by _profile_to_dict.

    Args:
        data: Dict as produced by _profile_to_dict.

    Returns:
        Reconstructed PersonProfile.
    """
    zodiac: ZodiacSign | None = None
    zodiac_raw = data["zodiac"]
    if zodiac_raw is not None:
        assert isinstance(zodiac_raw, int)
        zodiac = ZodiacSign(zodiac_raw)

    enneagram: EnneagramType | None = None
    if data["enneagram"] is not None:
        e = data["enneagram"]
        assert isinstance(e, dict)
        enneagram = EnneagramType(
            type_num=int(e["type_num"]),
            wing=int(e["wing"]),
        )

    mbti: MBTIType | None = None
    if data["mbti"] is not None:
        mbti = MBTIType.from_str(str(data["mbti"]))

    return PersonProfile(
        name=str(data["name"]),
        zodiac=zodiac,
        enneagram=enneagram,
        mbti=mbti,
    )


def persons_to_json(persons: list[PersonProfile]) -> str:
    """Serialize a list of PersonProfiles to a JSON string.

    Args:
        persons: List of profiles to serialize.

    Returns:
        JSON string representation.
    """
    return json.dumps([_profile_to_dict(p) for p in persons])


def persons_from_json(raw: str) -> list[PersonProfile]:
    """Deserialize a list of PersonProfiles from a JSON string.

    Args:
        raw: JSON string produced by persons_to_json.

    Returns:
        List of reconstructed PersonProfile instances.
    """
    return [_profile_from_dict(d) for d in json.loads(raw)]


# ---------------------------------------------------------------------------
# Sphere / circle drawing helpers
# ---------------------------------------------------------------------------

_N_SPHERE: int = 40  # grid resolution for the ellipsoid surface
_N_CIRCLE: int = 100  # point count for each great-circle loop


def _linspace(start: float, stop: float, n: int) -> list[float]:
    """Return n evenly-spaced floats from start to stop inclusive."""
    return [start + (stop - start) * i / (n - 1) for i in range(n)]


def _make_ellipsoid_surface(
    cx: float,
    cy: float,
    cz: float,
    rx: float,
    ry: float,
    rz: float,
) -> go.Surface:
    """Return a semi-transparent ellipsoid surface centred at (cx,cy,cz).

    Args:
        cx, cy, cz: Centre of the ellipsoid.
        rx, ry, rz: Semi-axis radii.

    Returns:
        go.Surface trace with low opacity, no colour scale bar.
    """
    thetas = _linspace(0.0, 2.0 * math.pi, _N_SPHERE)
    phis = _linspace(0.0, math.pi, _N_SPHERE)
    surf_x = [
        [cx + rx * math.sin(phi) * math.cos(theta) for theta in thetas] for phi in phis
    ]
    surf_y = [
        [cy + ry * math.sin(phi) * math.sin(theta) for theta in thetas] for phi in phis
    ]
    surf_z = [[cz + rz * math.cos(phi) for _ in thetas] for phi in phis]
    return go.Surface(
        x=surf_x,
        y=surf_y,
        z=surf_z,
        opacity=0.07,
        colorscale=[[0, "#9EC4E8"], [1, "#9EC4E8"]],
        showscale=False,
        hoverinfo="skip",
        name="",
        showlegend=False,
    )


def _make_great_circles(
    cx: float,
    cy: float,
    cz: float,
    rx: float,
    ry: float,
    rz: float,
) -> list[go.Scatter3d]:
    """Return three great-circle loops that divide the ellipsoid into octants.

    Args:
        cx, cy, cz: Centre of the ellipsoid.
        rx, ry, rz: Semi-axis radii.

    Returns:
        List of three go.Scatter3d line traces (XY, XZ, YZ planes).
    """
    ts = _linspace(0.0, 2.0 * math.pi, _N_CIRCLE)
    line_style: dict[str, object] = {"color": "rgba(80,120,200,0.45)", "width": 2}
    # Equator in the XY plane (z = cz)
    gc_xy = go.Scatter3d(
        x=[cx + rx * math.cos(t) for t in ts],
        y=[cy + ry * math.sin(t) for t in ts],
        z=[cz] * _N_CIRCLE,
        mode="lines",
        line=line_style,
        hoverinfo="skip",
        name="",
        showlegend=False,
    )
    # Loop in the XZ plane (y = cy)
    gc_xz = go.Scatter3d(
        x=[cx + rx * math.cos(t) for t in ts],
        y=[cy] * _N_CIRCLE,
        z=[cz + rz * math.sin(t) for t in ts],
        mode="lines",
        line=line_style,
        hoverinfo="skip",
        name="",
        showlegend=False,
    )
    # Loop in the YZ plane (x = cx)
    gc_yz = go.Scatter3d(
        x=[cx] * _N_CIRCLE,
        y=[cy + ry * math.cos(t) for t in ts],
        z=[cz + rz * math.sin(t) for t in ts],
        mode="lines",
        line=line_style,
        hoverinfo="skip",
        name="",
        showlegend=False,
    )
    return [gc_xy, gc_xz, gc_yz]


def _make_octant_labels(
    cx: float,
    cy: float,
    cz: float,
    rx: float,
    ry: float,
    rz: float,
    x_dim: PersonalityDimension,
    y_dim: PersonalityDimension,
    z_dim: PersonalityDimension,
) -> go.Scatter3d:
    """Return text labels at the centre of each of the 8 sphere octants.

    Args:
        cx, cy, cz: Centre of the ellipsoid.
        rx, ry, rz: Semi-axis radii.
        x_dim, y_dim, z_dim: Dimensions assigned to each axis.

    Returns:
        go.Scatter3d in text-only mode with 8 annotation points.
    """
    x_poles = get_pole_labels(x_dim)
    y_poles = get_pole_labels(y_dim)
    z_poles = get_pole_labels(z_dim)
    scale = 1.18  # just outside the ellipsoid surface
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    texts: list[str] = []
    for xi, x_lbl in enumerate(x_poles):
        for yi, y_lbl in enumerate(y_poles):
            for zi, z_lbl in enumerate(z_poles):
                sx = -1 if xi == 0 else 1
                sy = -1 if yi == 0 else 1
                sz = -1 if zi == 0 else 1
                xs.append(cx + sx * rx * scale)
                ys.append(cy + sy * ry * scale)
                zs.append(cz + sz * rz * scale)
                texts.append(f"{x_lbl}<br>{y_lbl}<br>{z_lbl}")
    return go.Scatter3d(
        x=xs,
        y=ys,
        z=zs,
        mode="text",
        text=texts,
        textfont={"size": 9, "color": "rgba(70,70,90,0.75)"},
        hoverinfo="skip",
        name="",
        showlegend=False,
    )


def _make_circle_background(
    cx: float,
    cy: float,
    rx: float,
    ry: float,
) -> list[go.Scatter]:
    """Return an ellipse outline and two quadrant-divider lines for 2-D mode.

    Args:
        cx, cy: Centre of the ellipse.
        rx, ry: Semi-axis radii.

    Returns:
        List of three go.Scatter traces: ellipse, vertical line, horizontal line.
    """
    ts = _linspace(0.0, 2.0 * math.pi, _N_CIRCLE)
    line_dim: dict[str, object] = {"color": "rgba(80,120,200,0.3)", "width": 1}
    line_div: dict[str, object] = {
        "color": "rgba(80,120,200,0.45)",
        "width": 1,
        "dash": "dash",
    }
    ellipse = go.Scatter(
        x=[cx + rx * math.cos(t) for t in ts],
        y=[cy + ry * math.sin(t) for t in ts],
        mode="lines",
        line=line_dim,
        fill="toself",
        fillcolor="rgba(158,196,232,0.06)",
        hoverinfo="skip",
        name="",
        showlegend=False,
    )
    v_line = go.Scatter(
        x=[cx, cx],
        y=[cy - ry, cy + ry],
        mode="lines",
        line=line_div,
        hoverinfo="skip",
        name="",
        showlegend=False,
    )
    h_line = go.Scatter(
        x=[cx - rx, cx + rx],
        y=[cy, cy],
        mode="lines",
        line=line_div,
        hoverinfo="skip",
        name="",
        showlegend=False,
    )
    return [ellipse, v_line, h_line]


def _make_quadrant_labels(
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    x_dim: PersonalityDimension,
    y_dim: PersonalityDimension,
) -> go.Scatter:
    """Return text labels at the centre of each of the 4 circle quadrants.

    Args:
        cx, cy: Centre of the ellipse.
        rx, ry: Semi-axis radii.
        x_dim, y_dim: Dimensions assigned to each axis.

    Returns:
        go.Scatter in text-only mode with 4 annotation points.
    """
    x_poles = get_pole_labels(x_dim)
    y_poles = get_pole_labels(y_dim)
    scale = 0.88
    xs: list[float] = []
    ys: list[float] = []
    texts: list[str] = []
    for xi, x_lbl in enumerate(x_poles):
        for yi, y_lbl in enumerate(y_poles):
            sx = -1 if xi == 0 else 1
            sy = -1 if yi == 0 else 1
            xs.append(cx + sx * rx * scale)
            ys.append(cy + sy * ry * scale)
            texts.append(f"{x_lbl}<br>{y_lbl}")
    return go.Scatter(
        x=xs,
        y=ys,
        mode="text",
        text=texts,
        textfont={"size": 10, "color": "rgba(70,70,90,0.6)"},
        hoverinfo="skip",
        name="",
        showlegend=False,
    )


# ---------------------------------------------------------------------------
# Figure builder
# ---------------------------------------------------------------------------


def build_figure(
    persons: list[PersonProfile],
    x_dim: PersonalityDimension | None,
    y_dim: PersonalityDimension | None,
    z_dim: PersonalityDimension | None,
    include_missing: bool = True,
) -> go.Figure:
    """Build a Plotly Figure mapping persons onto personality axes.

    When z_dim is provided the chart renders as a 3-D sphere with an
    ellipsoid shell, three great-circle loops, and octant labels.  When
    z_dim is None the chart renders as a 2-D circle with quadrant lines
    and labels.  Returns an empty Figure when x_dim or y_dim is None.

    Args:
        persons: Persons to plot.
        x_dim: Dimension mapped to the X axis, or None.
        y_dim: Dimension mapped to the Y axis, or None.
        z_dim: Dimension mapped to the Z axis; None triggers 2-D mode.
        include_missing: If True (default), persons missing data on any
            selected axis are plotted at the axis midpoint with a hollow
            marker.  If False they are excluded.

    Returns:
        A go.Figure ready for display in a dcc.Graph.
    """
    if x_dim is None or y_dim is None:
        return go.Figure()

    selected_dims: list[PersonalityDimension] = (
        [x_dim, y_dim, z_dim] if z_dim is not None else [x_dim, y_dim]
    )

    complete: list[PersonProfile] = []
    missing: list[PersonProfile] = []
    for p in persons:
        if all(get_coord(p, d) is not None for d in selected_dims):
            complete.append(p)
        else:
            missing.append(p)

    if not include_missing:
        missing = []

    def _resolve(person: PersonProfile, dim: PersonalityDimension) -> float:
        val = get_coord(person, dim)
        return val if val is not None else _MIDPOINTS[dim]

    def _hover(person: PersonProfile, is_missing: bool) -> str:
        parts = [f"<b>{person.name}</b>"]
        for d in selected_dims:
            val = get_coord(person, d)
            if val is None:
                parts.append(f"{d.value.capitalize()}: <i>missing</i>")
            else:
                parts.append(f"{d.value.capitalize()}: {get_label(d, val)}")
        if is_missing:
            missing_dims = [
                d.value for d in selected_dims if get_coord(person, d) is None
            ]
            parts.append(f"[!] No {', '.join(missing_dims)} data")
        return "<br>".join(parts)

    cx = _MIDPOINTS[x_dim]
    cy = _MIDPOINTS[y_dim]
    rx = _HALF_RANGES[x_dim]
    ry = _HALF_RANGES[y_dim]

    traces: list[go.BaseTraceType] = []
    layout: go.Layout

    if z_dim is not None:
        cz = _MIDPOINTS[z_dim]
        rz = _HALF_RANGES[z_dim]

        traces.append(_make_ellipsoid_surface(cx, cy, cz, rx, ry, rz))
        traces.extend(_make_great_circles(cx, cy, cz, rx, ry, rz))
        traces.append(_make_octant_labels(cx, cy, cz, rx, ry, rz, x_dim, y_dim, z_dim))

        if complete:
            traces.append(
                go.Scatter3d(
                    x=[_resolve(p, x_dim) for p in complete],
                    y=[_resolve(p, y_dim) for p in complete],
                    z=[_resolve(p, z_dim) for p in complete],
                    mode="markers+text",
                    text=[p.name for p in complete],
                    textposition="top center",
                    hovertext=[_hover(p, False) for p in complete],
                    hoverinfo="text",
                    marker={"size": 8, "symbol": "circle"},
                    name="Complete",
                )
            )
        if missing:
            traces.append(
                go.Scatter3d(
                    x=[_resolve(p, x_dim) for p in missing],
                    y=[_resolve(p, y_dim) for p in missing],
                    z=[_resolve(p, z_dim) for p in missing],
                    mode="markers+text",
                    text=[p.name for p in missing],
                    textposition="top center",
                    hovertext=[_hover(p, True) for p in missing],
                    hoverinfo="text",
                    marker={"size": 8, "symbol": "circle-open"},
                    name="Missing data",
                )
            )
        layout = go.Layout(
            scene={
                "xaxis": {
                    "title": x_dim.value.capitalize(),
                    "tickvals": get_tick_values(x_dim),
                    "ticktext": get_tick_labels(x_dim),
                },
                "yaxis": {
                    "title": y_dim.value.capitalize(),
                    "tickvals": get_tick_values(y_dim),
                    "ticktext": get_tick_labels(y_dim),
                },
                "zaxis": {
                    "title": z_dim.value.capitalize(),
                    "tickvals": get_tick_values(z_dim),
                    "ticktext": get_tick_labels(z_dim),
                },
            },
            margin={"l": 0, "r": 0, "t": 40, "b": 0},
            legend={"x": 0, "y": 1},
            uirevision="stable",
        )
    else:
        traces.extend(_make_circle_background(cx, cy, rx, ry))
        traces.append(_make_quadrant_labels(cx, cy, rx, ry, x_dim, y_dim))

        if complete:
            traces.append(
                go.Scatter(
                    x=[_resolve(p, x_dim) for p in complete],
                    y=[_resolve(p, y_dim) for p in complete],
                    mode="markers+text",
                    text=[p.name for p in complete],
                    textposition="top center",
                    hovertext=[_hover(p, False) for p in complete],
                    hoverinfo="text",
                    marker={"size": 10, "symbol": "circle"},
                    name="Complete",
                )
            )
        if missing:
            traces.append(
                go.Scatter(
                    x=[_resolve(p, x_dim) for p in missing],
                    y=[_resolve(p, y_dim) for p in missing],
                    mode="markers+text",
                    text=[p.name for p in missing],
                    textposition="top center",
                    hovertext=[_hover(p, True) for p in missing],
                    hoverinfo="text",
                    marker={"size": 10, "symbol": "x-open"},
                    name="Missing data",
                )
            )
        layout = go.Layout(
            xaxis={
                "title": x_dim.value.capitalize(),
                "tickvals": get_tick_values(x_dim),
                "ticktext": get_tick_labels(x_dim),
            },
            yaxis={
                "title": y_dim.value.capitalize(),
                "tickvals": get_tick_values(y_dim),
                "ticktext": get_tick_labels(y_dim),
            },
            margin={"l": 60, "r": 20, "t": 40, "b": 60},
            legend={"x": 0, "y": 1},
            uirevision="stable",
        )

    return go.Figure(data=traces, layout=layout)


# ---------------------------------------------------------------------------
# Callback logic (pure helpers — extracted for testability)
# ---------------------------------------------------------------------------

_DIM_OPTIONS: list[dict[str, str]] = [
    {"label": d.value.capitalize(), "value": d.value} for d in PersonalityDimension
]


def compute_axis_options(
    x_val: str | None,
    y_val: str | None,
    z_val: str | None,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    """Return option lists for the X, Y, Z axis dropdowns.

    Each option list disables values already selected in the sibling dropdowns
    so users cannot assign the same system to two axes.

    Args:
        x_val: Currently selected X-axis dimension value, or None.
        y_val: Currently selected Y-axis dimension value, or None.
        z_val: Currently selected Z-axis dimension value, or None.

    Returns:
        Tuple of three option lists (x_options, y_options, z_options).
    """

    def _options_excluding(
        *exclude: str | None,
    ) -> list[dict[str, object]]:
        excluded = {v for v in exclude if v is not None}
        return [{**opt, "disabled": opt["value"] in excluded} for opt in _DIM_OPTIONS]

    return (
        _options_excluding(y_val, z_val),
        _options_excluding(x_val, z_val),
        _options_excluding(x_val, y_val),
    )


def compute_figure(
    store_data: str,
    x_val: str | None,
    y_val: str | None,
    z_val: str | None,
    include_missing_flags: list[str] | None,
) -> go.Figure:
    """Deserialize the store and build a figure for the current axis selection.

    A null z_val triggers 2-D mode; null x_val or y_val returns an empty figure.

    Args:
        store_data: JSON string from dcc.Store.
        x_val: PersonalityDimension value for X axis, or None.
        y_val: PersonalityDimension value for Y axis, or None.
        z_val: PersonalityDimension value for Z axis, or None (2-D mode).
        include_missing_flags: List from dcc.Checklist; contains 'show' if
            missing-data persons should be displayed.

    Returns:
        A go.Figure.
    """
    persons = persons_from_json(store_data)
    include_missing = bool(include_missing_flags)
    return build_figure(
        persons=persons,
        x_dim=PersonalityDimension(x_val) if x_val else None,
        y_dim=PersonalityDimension(y_val) if y_val else None,
        z_dim=PersonalityDimension(z_val) if z_val else None,
        include_missing=include_missing,
    )


def add_person_to_store(
    n_clicks: int | None,
    store_data: str,
    name: str | None,
    zodiac_val: str | None,
    ennea_type: str | None,
    ennea_wing: str | None,
    mbti_val: str | None,
) -> str:
    """Validate form inputs, build a PersonProfile, and append to the store.

    Args:
        n_clicks: Button click count (unused; triggers callback).
        store_data: Current JSON string from dcc.Store.
        name: Person name from text input.
        zodiac_val: Selected zodiac int value as string, or None.
        ennea_type: Selected Enneagram type as string, or None.
        ennea_wing: Selected Enneagram wing as string, or None.
        mbti_val: Selected MBTI code string, or None.

    Returns:
        Updated JSON string for dcc.Store. Returns unchanged store_data
        if name is missing or blank.
    """
    if not name or not name.strip():
        logger.debug("add_person_to_store: skipped — name is empty")
        return store_data

    zodiac: ZodiacSign | None = None
    if zodiac_val is not None:
        try:
            zodiac = ZodiacSign(int(zodiac_val))
        except (ValueError, KeyError):
            logger.warning("add_person_to_store: invalid zodiac value %r", zodiac_val)

    enneagram: EnneagramType | None = None
    if ennea_type is not None and ennea_wing is not None:
        try:
            enneagram = EnneagramType(type_num=int(ennea_type), wing=int(ennea_wing))
        except ValueError as exc:
            logger.warning("add_person_to_store: invalid enneagram: %s", exc)

    mbti: MBTIType | None = None
    if mbti_val is not None:
        try:
            mbti = MBTIType.from_str(mbti_val)
        except ValueError as exc:
            logger.warning("add_person_to_store: invalid MBTI: %s", exc)

    persons = persons_from_json(store_data)
    persons.append(
        PersonProfile(
            name=name.strip(),
            zodiac=zodiac,
            enneagram=enneagram,
            mbti=mbti,
        )
    )
    logger.info("add_person_to_store: added %r (total: %d)", name.strip(), len(persons))
    return persons_to_json(persons)


# ---------------------------------------------------------------------------
# Dash layout
# ---------------------------------------------------------------------------

_ZODIAC_OPTIONS = [
    {"label": z.name.capitalize(), "value": str(int(z))} for z in ZodiacSign
]
_ENNEA_TYPE_OPTIONS = [{"label": str(t), "value": str(t)} for t in range(1, 10)]
_MBTI_OPTIONS = [
    {"label": lbl, "value": lbl} for lbl in get_tick_labels(PersonalityDimension.MBTI)
]


def build_layout(initial_persons: list[PersonProfile]) -> html.Div:
    """Build the full Dash layout tree.

    Args:
        initial_persons: Persons to load into the store on startup.

    Returns:
        Root html.Div containing the full page layout.
    """
    return html.Div(
        style={
            "fontFamily": "sans-serif",
            "maxWidth": "1200px",
            "margin": "0 auto",
            "padding": "16px",
        },
        children=[
            html.H1("Personality Space", style={"textAlign": "center"}),
            html.Div(
                style={
                    "display": "flex",
                    "gap": "16px",
                    "flexWrap": "wrap",
                    "marginBottom": "12px",
                },
                children=[
                    html.Div(
                        [
                            html.Label("X axis"),
                            dcc.Dropdown(
                                id="x-axis-dim",
                                options=_DIM_OPTIONS,
                                value=PersonalityDimension.ZODIAC.value,
                                clearable=True,
                                style={"width": "160px"},
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("Y axis"),
                            dcc.Dropdown(
                                id="y-axis-dim",
                                options=_DIM_OPTIONS,
                                value=PersonalityDimension.ENNEAGRAM.value,
                                clearable=True,
                                style={"width": "160px"},
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("Z axis (blank = 2D)"),
                            dcc.Dropdown(
                                id="z-axis-dim",
                                options=_DIM_OPTIONS,
                                value=None,
                                clearable=True,
                                style={"width": "160px"},
                            ),
                        ]
                    ),
                ],
            ),
            dcc.Graph(
                id="personality-graph",
                style={"height": "600px"},
                config={"scrollZoom": True},
            ),
            html.Hr(),
            html.H3("Add a Person"),
            html.Div(
                style={
                    "display": "flex",
                    "gap": "12px",
                    "flexWrap": "wrap",
                    "alignItems": "flex-end",
                },
                children=[
                    html.Div(
                        [
                            html.Label("Name *"),
                            dcc.Input(
                                id="person-name",
                                type="text",
                                placeholder="Name",
                                style={"width": "120px"},
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("Zodiac"),
                            dcc.Dropdown(
                                id="zodiac-input",
                                options=_ZODIAC_OPTIONS,
                                placeholder="Select...",
                                style={"width": "140px"},
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("Ennea type"),
                            dcc.Dropdown(
                                id="ennea-type-input",
                                options=_ENNEA_TYPE_OPTIONS,
                                placeholder="1-9",
                                style={"width": "80px"},
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("Wing"),
                            dcc.Dropdown(
                                id="ennea-wing-input",
                                options=_ENNEA_TYPE_OPTIONS,
                                placeholder="1-9",
                                style={"width": "80px"},
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label("MBTI"),
                            dcc.Dropdown(
                                id="mbti-input",
                                options=_MBTI_OPTIONS,
                                placeholder="Select...",
                                style={"width": "100px"},
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label(" "),
                            html.Button(
                                "Add Person",
                                id="add-person-btn",
                                n_clicks=0,
                                style={"cursor": "pointer"},
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Label(" "),
                            dcc.Checklist(
                                id="include-missing-toggle",
                                options=[
                                    {"label": "Show missing data", "value": "show"}
                                ],
                                value=["show"],
                            ),
                        ]
                    ),
                ],
            ),
            dcc.Store(
                id="persons-store",
                data=persons_to_json(initial_persons),
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Dash app factory and callbacks
# ---------------------------------------------------------------------------


def _register_callbacks(app: dash.Dash) -> None:
    """Register all Dash callbacks on the application instance.

    Args:
        app: The Dash application to register callbacks on.
    """

    @app.callback(
        Output("x-axis-dim", "options"),
        Output("y-axis-dim", "options"),
        Output("z-axis-dim", "options"),
        Input("x-axis-dim", "value"),
        Input("y-axis-dim", "value"),
        Input("z-axis-dim", "value"),
    )
    def _update_axis_options(
        x_val: str | None,
        y_val: str | None,
        z_val: str | None,
    ) -> tuple[
        list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]
    ]:
        return compute_axis_options(x_val, y_val, z_val)  # pragma: no cover

    @app.callback(
        Output("personality-graph", "figure"),
        Input("persons-store", "data"),
        Input("x-axis-dim", "value"),
        Input("y-axis-dim", "value"),
        Input("z-axis-dim", "value"),
        Input("include-missing-toggle", "value"),
    )
    def _update_graph(
        store_data: str,
        x_val: str | None,
        y_val: str | None,
        z_val: str | None,
        include_missing_flags: list[str] | None,
    ) -> go.Figure:
        return compute_figure(  # pragma: no cover
            store_data, x_val, y_val, z_val, include_missing_flags
        )

    @app.callback(
        Output("persons-store", "data"),
        Input("add-person-btn", "n_clicks"),
        State("persons-store", "data"),
        State("person-name", "value"),
        State("zodiac-input", "value"),
        State("ennea-type-input", "value"),
        State("ennea-wing-input", "value"),
        State("mbti-input", "value"),
        prevent_initial_call=True,
    )
    def _add_person(
        n_clicks: int | None,
        store_data: str,
        name: str | None,
        zodiac_val: str | None,
        ennea_type: str | None,
        ennea_wing: str | None,
        mbti_val: str | None,
    ) -> str:
        return add_person_to_store(  # pragma: no cover
            n_clicks, store_data, name, zodiac_val, ennea_type, ennea_wing, mbti_val
        )


def create_app(persons: list[PersonProfile] | None = None) -> dash.Dash:
    """Create and configure the Personality Space Dash application.

    Does not start the server. Call app.run() separately.

    Args:
        persons: Initial list of persons to display. Defaults to SAMPLE_PERSONS.

    Returns:
        A fully configured dash.Dash instance.
    """
    if persons is None:
        persons = SAMPLE_PERSONS
    app = dash.Dash(__name__, title="Personality Space")
    app.layout = build_layout(persons)
    _register_callbacks(app)
    logger.info("Personality Space app created with %d initial persons", len(persons))
    return app


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and launch the Personality Space Dash server.

    Args:
        argv: Argument list. Defaults to sys.argv[1:] when None.

    Returns:
        Exit code (always 0 on normal termination).
    """
    parser = argparse.ArgumentParser(
        description="Launch the Personality Space interactive visualizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8050,
        help="Port to serve on (default: 8050)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable Dash debug mode",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    app = create_app()
    logger.info(
        "Starting Personality Space on port %d (debug=%s)", args.port, args.debug
    )
    app.run(debug=args.debug, port=args.port)  # pragma: no cover
    return 0


if __name__ == "__main__":
    sys.exit(main())
