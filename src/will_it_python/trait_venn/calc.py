"""Probability and display-formatting rules for trait combinations.

Traits are modeled as independent conditional on gender::

    P(region) = sum over g of P(g) * prod P(trait | g)

Traits without gender-specific prevalence have the same value for every
gender, so the formula reduces to a plain product unless a gender option or a
gender-dependent trait is selected.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from will_it_python.trait_venn.traits import GENDER_TRAITS, US, Gender, Trait

# Below this probability a fixed "1 in N" reads better than a fraction.
_RATIO_RARE: Final = 0.2
# At or above this probability, odds read as "nearly everyone".
_RATIO_NEARLY_ALL: Final = 0.995
# Largest denominator tried for "k in n" fractions of common traits.
_RATIO_MAX_DENOMINATOR: Final = 20
# Maximum relative error accepted for a "k in n" fraction.
_RATIO_TOLERANCE: Final = 0.1
# Rarer than 1 in 1,000,000: percentages would need scientific notation.
PCT_FLOOR: Final = 1e-6
# Numbers at or above this use long-form compact notation ("76.9 trillion").
_BIG_NUMBER: Final = 1_000_000_000
_COMPACT_UNITS: Final = (
    (1e12, "trillion", "T"),
    (1e9, "billion", "B"),
    (1e6, "million", "M"),
    (1e3, "thousand", "K"),
)
# Threshold factor so values that round up to the next unit use that unit.
_ROUND_UP: Final = 0.9995
_THOUSAND: Final = 1000


@dataclass(frozen=True, slots=True)
class RegionProbability:
    """Probabilities for one Venn region.

    Attributes:
        inclusive: Probability of having every trait in the region.
        exclusive: Probability of having exactly the region's traits among
            the selected traits (all others absent).
    """

    inclusive: float
    exclusive: float


def prevalence(trait: Trait, country: str | None) -> float:
    """Return a trait's marginal prevalence for a scope.

    Args:
        trait: The trait.
        country: Country code, or ``None`` for worldwide.

    Returns:
        The United States override when ``country`` is ``"US"`` and one
        exists, otherwise the worldwide value.
    """
    if country == US and trait.us is not None:
        return trait.us
    return trait.p


def conditional(trait: Trait, gender: Gender, country: str | None) -> float:
    """Return P(trait | gender) for a scope.

    Args:
        trait: The trait.
        gender: The conditioning gender.
        country: Country code, or ``None`` for worldwide.

    Returns:
        1 or 0 for the gender options themselves, the gender-specific value
        for gender-dependent traits, otherwise the marginal prevalence.
    """
    if trait.gender is not None:
        return 1.0 if trait.gender is gender else 0.0
    if trait.by_gender is not None:
        table = trait.by_gender
        if country == US and trait.by_gender_us is not None:
            table = trait.by_gender_us
        return table[gender]
    return prevalence(trait, country)


def region_probability(
    traits: Sequence[Trait], mask: int, country: str | None
) -> RegionProbability:
    """Return the probability of a Venn region.

    Args:
        traits: Selected traits; bit ``i`` of ``mask`` refers to ``traits[i]``.
        mask: Bitmask of the traits inside the region.
        country: Country code, or ``None`` for worldwide.

    Returns:
        Inclusive and exclusive probabilities for the region.
    """
    inclusive = exclusive = 0.0
    for gender, gender_trait in GENDER_TRAITS.items():
        weight = prevalence(gender_trait, country)
        inc = exc = weight
        for i, trait in enumerate(traits):
            p = conditional(trait, gender, country)
            if mask >> i & 1:
                inc *= p
                exc *= p
            else:
                exc *= 1 - p
        inclusive += inc
        exclusive += exc
    return RegionProbability(inclusive, exclusive)


def one_in(p: float) -> int:
    """Return ``int(1 / p)``, the N in "1 in N"."""
    return int(1 / p)


def compact(n: float, *, long: bool) -> str:
    """Return ``n`` in compact notation with three significant digits.

    Args:
        n: Non-negative number.
        long: Use unit words ("1.03 million") instead of suffixes ("1.03M").

    Returns:
        The compact string; values below 1,000 are returned unchanged.
    """
    for size, word, suffix in _COMPACT_UNITS:
        # Step up a unit when rounding would print 1000 (999,999 -> "1M").
        if n >= size * _ROUND_UP:
            scaled = n / size
            value = f"{scaled:,.0f}" if scaled >= _THOUSAND else f"{scaled:.3g}"
            return f"{value} {word}" if long else f"{value}{suffix}"
    return f"{n:,.0f}"


def big_number(n: int) -> str:
    """Return ``n`` with thousands separators, or long compact form if huge."""
    if n >= _BIG_NUMBER:
        return compact(n, long=True)
    return f"{n:,}"


def ratio(p: float) -> str:
    """Return odds as "k in N".

    Rare values (p < 0.2) use "1 in int(1/p)". Common values use the smallest
    fraction k/n (n <= 20) within 10% relative error.

    Args:
        p: Probability in [0, 1].

    Returns:
        The odds string.
    """
    if p >= _RATIO_NEARLY_ALL:
        return "nearly everyone"
    if p <= 0:
        return "no one"
    if p >= _RATIO_RARE and (fraction := simple_fraction(p)):
        return f"{fraction[0]} in {fraction[1]}"
    return f"1 in {big_number(one_in(p))}"


def simple_fraction(p: float) -> tuple[int, int] | None:
    """Return the smallest-denominator k/n (n <= 20) within 10% of p.

    Args:
        p: Probability in (0, 1).

    Returns:
        ``(k, n)``, or ``None`` when no such fraction exists.
    """
    for n in range(2, _RATIO_MAX_DENOMINATOR + 1):
        k = round(p * n)
        if 1 <= k < n and abs(k / n - p) / p < _RATIO_TOLERANCE:
            return k, n
    return None


def badge_ratio(p: float) -> str:
    """Return odds for the small center badge, abbreviating large N."""
    if 0 < p < _RATIO_RARE:
        return f"1 in {compact(one_in(p), long=False)}"
    return ratio(p)


def fmt_pct(p: float) -> str:
    """Return a percentage string, or ``""`` when p is below the floor.

    Values of 1% or more show one decimal place (trailing ``.0`` dropped);
    smaller values show two significant digits. Scientific notation is never
    produced because values below :data:`PCT_FLOOR` return ``""``.
    """
    if p < PCT_FLOOR:
        return ""
    pct = p * 100
    if pct >= 1:
        return f"{pct:.1f}".removesuffix(".0") + "%"
    digits = max(0, 1 - math.floor(math.log10(pct)))
    text = f"{pct:.{digits}f}".rstrip("0").rstrip(".")
    return f"{text}%"


def expected_count(population: int, p: float) -> str:
    """Return the expected number of people with a combination.

    Args:
        population: Population of the scope.
        p: Probability of the combination.

    Returns:
        "≈ N people" when at least one person is expected, otherwise
        "statistically nobody" with the expected value.
    """
    expected = population * p
    if expected >= 1:
        n = math.floor(expected)
        noun = "person" if n == 1 else "people"
        return f"≈ {n:,} {noun}"
    return f"statistically nobody (expected {expected:.2g})"


def join_phrases(phrases: Sequence[str]) -> str:
    """Join phrases as "a, b and c"."""
    if len(phrases) <= 1:
        return "".join(phrases)
    return ", ".join(phrases[:-1]) + " and " + phrases[-1]
