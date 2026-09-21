"""Population clock: projects population forward from a base value.

Mirrors the U.S. Census Bureau Population Clock method (base value plus a
constant rate times elapsed time), using the base, per-second rate, and
update time published by the clock itself. Network access lives in the
server layer; this module only parses responses and projects values.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

POPCLOCK_URL: Final = "https://www.census.gov/popclock/data/population.php/{scope}"
POPCLOCK_PAGE: Final = "https://www.census.gov/popclock/"

# Sanity floor: both the world and US populations exceed this.
_MIN_POPULATION: Final = 100_000_000
_SECONDS_PER_YEAR: Final = 365.25 * 24 * 3600
_EPOCH_2026: Final = datetime(2026, 1, 1, tzinfo=UTC).timestamp()


@dataclass(frozen=True, slots=True)
class Clock:
    """A linear population projection.

    Attributes:
        base: Population at ``at``.
        at: POSIX timestamp of ``base``.
        per_second: Net growth in people per second.
    """

    base: int
    at: float
    per_second: float

    def now(self, timestamp: float) -> int:
        """Return the projected population at ``timestamp``."""
        return int(self.base + self.per_second * (timestamp - self.at))


# Fallbacks used when the Census clock cannot be reached; approximate
# 2026-01-01 values with ~70M/yr world and ~1.55M/yr US net growth.
FALLBACK_WORLD: Final = Clock(
    8_130_000_000, _EPOCH_2026, 70_000_000 / _SECONDS_PER_YEAR
)
FALLBACK_US: Final = Clock(342_300_000, _EPOCH_2026, 1_550_000 / _SECONDS_PER_YEAR)


@dataclass(frozen=True, slots=True)
class Snapshot:
    """World and US population clocks plus where they came from.

    Attributes:
        world: World clock.
        us: United States clock.
        live_world: Whether ``world`` came from the Census clock.
        live_us: Whether ``us`` came from the Census clock.
    """

    world: Clock
    us: Clock
    live_world: bool = False
    live_us: bool = False

    @property
    def source(self) -> str:
        """Return a human-readable description of the population source."""
        if self.live_world and self.live_us:
            return "live from census.gov/popclock"
        if self.live_world or self.live_us:
            return "partly live from census.gov/popclock, partly approximate projection"
        return "approximate projection (Census population clock unavailable)"


def parse_popclock(payload: object, scope: str, fetched_at: float) -> Clock | None:
    """Return a clock from a Census popclock response, or ``None`` if malformed.

    Expected shape (``scope`` is ``"us"`` or ``"world"``)::

        {scope: {"population": int, "population_rate": float,
                 "rate_interval": "second", "last_updated": "<POSIX seconds>"}}

    Args:
        payload: Decoded JSON.
        scope: Top-level key of the response.
        fetched_at: POSIX time of the fetch, used when ``last_updated`` is absent.

    Returns:
        A clock using the Census population, per-second rate, and update time.
        The rate falls back to the default when missing or not per second.
    """
    body = payload.get(scope) if isinstance(payload, dict) else None
    if not isinstance(body, dict):
        return None
    base = body.get("population")
    if isinstance(base, bool) or not isinstance(base, int) or base < _MIN_POPULATION:
        return None
    fallback = FALLBACK_US if scope == "us" else FALLBACK_WORLD
    rate = body.get("population_rate")
    per_second = (
        float(rate)
        if isinstance(rate, int | float) and body.get("rate_interval") == "second"
        else fallback.per_second
    )
    updated = body.get("last_updated")
    at = (
        float(updated) if isinstance(updated, str) and updated.isdigit() else fetched_at
    )
    return Clock(base, at, per_second)


def snapshot(world_payload: object, us_payload: object, timestamp: float) -> Snapshot:
    """Build a snapshot from Census responses, falling back where missing.

    Args:
        world_payload: Decoded world response, or ``None`` if unavailable.
        us_payload: Decoded US response, or ``None`` if unavailable.
        timestamp: POSIX time the responses were fetched.

    Returns:
        A snapshot using live clocks where the responses were valid.
    """
    world = parse_popclock(world_payload, "world", timestamp)
    us = parse_popclock(us_payload, "us", timestamp)
    return Snapshot(
        world=world or FALLBACK_WORLD,
        us=us or FALLBACK_US,
        live_world=world is not None,
        live_us=us is not None,
    )
