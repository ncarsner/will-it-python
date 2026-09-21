"""Venn diagram geometry for 1-5 sets on a 600 x 600 canvas.

The 1-3 set layouts are circles. The 4- and 5-set layouts are ellipses found
by numeric search and scaled to fill the canvas: every one of the 2**n - 1
regions exists, the narrowest region is as wide as possible, and the
all-traits center is kept small (inscribed radius about 48 for 4 sets and
78 for 5) so the other intersections have room for labels.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cache
from typing import Final

CANVAS: Final = 600
# Sampling step for label anchors; finer is slower with no visible gain.
_ANCHOR_STEP: Final = 4
_EPS: Final = 1e-6
# Center badge radius limits, in canvas units.
_BADGE_MIN: Final = 24
_BADGE_MAX: Final = 50
_BADGE_MAX_CROWDED: Final = 36
_BADGE_MARGIN: Final = 4
_CROWDED_SETS: Final = 4


@dataclass(frozen=True, slots=True)
class Ellipse:
    """An ellipse rotated ``rotation`` degrees about its center."""

    cx: float
    cy: float
    rx: float
    ry: float
    rotation: float = 0.0

    def local(self, x: float, y: float) -> tuple[float, float]:
        """Return (x, y) in the ellipse's unrotated local frame."""
        a = -math.radians(self.rotation)
        dx, dy = x - self.cx, y - self.cy
        return dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)

    def contains(self, x: float, y: float) -> bool:
        """Return whether (x, y) lies inside or on the ellipse."""
        u, v = self.local(x, y)
        return (u / self.rx) ** 2 + (v / self.ry) ** 2 <= 1

    def clearance(self, x: float, y: float) -> float:
        """Return the approximate distance from (x, y) to the boundary.

        Measured along the ray from the center through the point, which is
        exact for circles and a close approximation for ellipses.
        """
        u, v = self.local(x, y)
        k = math.hypot(u / self.rx, v / self.ry)
        return abs(k - 1) * math.hypot(u, v) / max(k, _EPS)


@dataclass(frozen=True, slots=True)
class Anchor:
    """Label position for a region and the room available around it."""

    x: float
    y: float
    clearance: float


def _circles(centers: list[tuple[float, float]], r: float) -> tuple[Ellipse, ...]:
    return tuple(Ellipse(cx, cy, r, r) for cx, cy in centers)


def _three() -> tuple[Ellipse, ...]:
    centers = [
        (300 + 100 * math.cos(math.radians(a)), 320 + 100 * math.sin(math.radians(a)))
        for a in (-90, 30, 150)
    ]
    return _circles(centers, 165)


def _four() -> tuple[Ellipse, ...]:
    placements = (
        (290.7, 237.8, 39.4),
        (309.3, 237.8, -39.4),
        (278.9, 362.2, 39.4),
        (321.1, 362.2, -39.4),
    )
    return tuple(Ellipse(cx, cy, 338.3, 98.8, r) for cx, cy, r in placements)


def _five() -> tuple[Ellipse, ...]:
    ellipses = []
    for i in range(5):
        angle = i * 72 - 90
        t = math.radians(angle)
        ellipses.append(
            Ellipse(
                300 + 95.8 * math.cos(t),
                300 + 95.8 * math.sin(t),
                189.2,
                68.0,
                angle + 6.9,
            )
        )
    return tuple(ellipses)


LAYOUTS: Final[dict[int, tuple[Ellipse, ...]]] = {
    1: (Ellipse(300, 300, 210, 210),),
    2: _circles([(210, 300), (390, 300)], 180),
    3: _three(),
    4: _four(),
    5: _five(),
}


def mask_at(ellipses: tuple[Ellipse, ...], x: float, y: float) -> int:
    """Return the bitmask of ellipses containing (x, y)."""
    mask = 0
    for i, e in enumerate(ellipses):
        if e.contains(x, y):
            mask |= 1 << i
    return mask


@cache
def anchors(n: int) -> dict[int, Anchor]:
    """Return a label anchor for every region of the n-set layout.

    Each anchor is the sampled point farthest from every boundary (an
    approximate pole of inaccessibility).

    Args:
        n: Number of sets (1-5).

    Returns:
        Mapping of region bitmask to anchor.
    """
    ellipses = LAYOUTS[n]
    best: dict[int, Anchor] = {}
    for x in range(_ANCHOR_STEP, CANVAS, _ANCHOR_STEP):
        for y in range(_ANCHOR_STEP, CANVAS, _ANCHOR_STEP):
            mask = mask_at(ellipses, x, y)
            if not mask:
                continue
            room = min(
                x, y, CANVAS - x, CANVAS - y, *(e.clearance(x, y) for e in ellipses)
            )
            if mask not in best or room > best[mask].clearance:
                best[mask] = Anchor(x, y, room)
    return best


def badge_radius(n: int) -> float:
    """Return the center badge radius for the n-set layout.

    The badge never exceeds the all-traits region and is smaller when four
    or more sets crowd the center.
    """
    center = anchors(n)[(1 << n) - 1]
    cap = _BADGE_MAX_CROWDED if n >= _CROWDED_SETS else _BADGE_MAX
    return max(_BADGE_MIN, min(cap, center.clearance - _BADGE_MARGIN))
