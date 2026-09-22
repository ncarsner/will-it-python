"""Validation of trait-selection requests and the selection rules.

A selection holds at most :data:`MAX_SELECTED` distinct traits, with at most
one trait from each mutually exclusive group (gender, handedness, eye color,
hair color, blood type).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from will_it_python.trait_venn.traits import (
    COUNTRIES_BY_CODE,
    DEFAULT_SELECTION,
    MAX_SELECTED,
    TRAITS_BY_ID,
    US,
    Trait,
)


class RequestError(ValueError):
    """Raised when a request's parameters are invalid."""


@dataclass(frozen=True, slots=True)
class Request:
    """A validated state request.

    Attributes:
        selection: Selected trait ids in selection order.
        country: Selected country code.
    """

    selection: tuple[str, ...]
    country: str


def can_add(selection: Sequence[str], trait: Trait) -> bool:
    """Return whether ``trait`` can be added to ``selection``.

    Swapping within an exclusive group is always allowed, even at the limit.
    """
    if len(selection) < MAX_SELECTED:
        return True
    return trait.group is not None and any(
        TRAITS_BY_ID[s].group == trait.group for s in selection
    )


def toggle(selection: Sequence[str], trait_id: str) -> tuple[str, ...]:
    """Return ``selection`` with ``trait_id`` toggled.

    Selecting the active trait clears it. Selecting another trait in an
    occupied exclusive group replaces the occupant in place. Otherwise the
    trait is appended if the limit allows; if not, the selection is returned
    unchanged.

    Args:
        selection: Current trait ids.
        trait_id: A known trait id.

    Returns:
        The new selection.
    """
    current = list(selection)
    if trait_id in current:
        current.remove(trait_id)
        return tuple(current)
    group = TRAITS_BY_ID[trait_id].group
    for i, existing in enumerate(current):
        if group is not None and TRAITS_BY_ID[existing].group == group:
            current[i] = trait_id
            return tuple(current)
    if len(current) < MAX_SELECTED:
        current.append(trait_id)
    return tuple(current)


def _single(query: Mapping[str, Sequence[str]], key: str) -> str:
    """Return the first value for ``key``, or ``""`` if absent."""
    values = query.get(key, [])
    return values[0].strip() if values else ""


def _validate_selection(ids: list[str]) -> tuple[str, ...]:
    unknown = [i for i in ids if i not in TRAITS_BY_ID]
    if unknown:
        raise RequestError(f"unknown trait id(s): {', '.join(unknown)}")
    if len(set(ids)) != len(ids):
        raise RequestError("duplicate trait ids")
    if len(ids) > MAX_SELECTED:
        raise RequestError(f"at most {MAX_SELECTED} traits may be selected")
    groups = [TRAITS_BY_ID[i].group for i in ids if TRAITS_BY_ID[i].group]
    if len(set(groups)) != len(groups):
        raise RequestError("at most one trait per exclusive group")
    return tuple(ids)


def parse_query(query: Mapping[str, Sequence[str]]) -> Request:
    """Validate a parsed query string and apply an optional toggle.

    Recognized keys: ``sel`` (comma-separated trait ids; absent means
    :data:`DEFAULT_SELECTION`, empty means nothing selected), ``country``
    (country code, default ``US``), and ``toggle`` (a trait id to toggle).

    Args:
        query: Output of :func:`urllib.parse.parse_qs` with
            ``keep_blank_values=True``.

    Returns:
        The validated request, with the toggle already applied.

    Raises:
        RequestError: If any parameter is invalid.
    """
    if "sel" in query:
        raw = _single(query, "sel")
        selection = _validate_selection(
            [s.strip() for s in raw.split(",") if s.strip()]
        )
    else:
        selection = DEFAULT_SELECTION
    country = _single(query, "country") or US
    if country not in COUNTRIES_BY_CODE:
        raise RequestError(f"unknown country code: {country}")
    toggled = _single(query, "toggle")
    if toggled:
        if toggled not in TRAITS_BY_ID:
            raise RequestError(f"unknown trait id: {toggled}")
        selection = toggle(selection, toggled)
    return Request(selection, country)
