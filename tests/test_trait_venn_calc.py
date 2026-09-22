"""Tests for trait_venn probability and formatting rules."""

import pytest

from will_it_python.trait_venn import calc
from will_it_python.trait_venn.traits import TRAITS_BY_ID, Gender

T = TRAITS_BY_ID

# ---------------------------------------------------------------------------
# Prevalence
# ---------------------------------------------------------------------------


def test_prevalence_uses_us_override_only_for_us():
    assert calc.prevalence(T["green"], "US") == 0.09
    assert calc.prevalence(T["green"], "JP") == 0.02
    assert calc.prevalence(T["green"], None) == 0.02


def test_prevalence_falls_back_to_world_without_override():
    assert calc.prevalence(T["left"], "US") == 0.10


def test_conditional_on_gender_options():
    assert calc.conditional(T["male"], Gender.MALE, None) == 1.0
    assert calc.conditional(T["male"], Gender.FEMALE, None) == 0.0


def test_conditional_gender_dependent_trait():
    assert calc.conditional(T["cb"], Gender.MALE, None) == 0.08
    assert calc.conditional(T["cb"], Gender.MALE, "US") == 0.08  # no US table
    assert calc.conditional(T["tall"], Gender.MALE, None) == 0.06
    assert calc.conditional(T["tall"], Gender.MALE, "US") == 0.145


def test_conditional_plain_trait_is_marginal():
    assert calc.conditional(T["blue"], Gender.FEMALE, "US") == 0.27


def test_region_probability_independent_traits_multiply():
    traits = [T["left"], T["green"]]
    r = calc.region_probability(traits, 0b11, None)
    assert r.inclusive == pytest.approx(0.10 * 0.02)
    only_left = calc.region_probability(traits, 0b01, None)
    assert only_left.exclusive == pytest.approx(0.10 * 0.98)
    assert only_left.inclusive == pytest.approx(0.10)


def test_region_probability_gender_conditioning():
    traits = [T["male"], T["cb"]]
    assert calc.region_probability(traits, 0b11, None).inclusive == pytest.approx(
        0.504 * 0.08
    )
    marginal = calc.region_probability([T["cb"]], 0b1, None).inclusive
    assert marginal == pytest.approx(0.504 * 0.08 + 0.496 * 0.005)


def test_region_probability_empty_selection_is_certain():
    assert calc.region_probability([], 0, None).inclusive == pytest.approx(1)


# ---------------------------------------------------------------------------
# Number formatting
# ---------------------------------------------------------------------------


def test_one_in_truncates():
    assert calc.one_in(0.00003) == 33333


@pytest.mark.parametrize(
    ("n", "long", "expected"),
    [
        (500, True, "500"),
        (1_033_399, False, "1.03M"),
        (1_033_399, True, "1.03 million"),
        (999_999, False, "1M"),
        (76_900_000_000_000, True, "76.9 trillion"),
        (5e15, False, "5,000T"),
    ],
)
def test_compact(n, long, expected):
    assert calc.compact(n, long=long) == expected


def test_big_number():
    assert calc.big_number(33_333) == "33,333"
    assert calc.big_number(14_727_822_000) == "14.7 billion"


@pytest.mark.parametrize(
    ("p", "expected"),
    [
        (0.999, "nearly everyone"),
        (0.0, "no one"),
        (0.504, "1 in 2"),
        (0.785, "3 in 4"),
        (0.27, "1 in 4"),
        (0.19, "1 in 5"),
        (0.00003, "1 in 33,333"),
        (1.3e-14, "1 in 76.9 trillion"),
    ],
)
def test_ratio(p, expected):
    assert calc.ratio(p) == expected


def test_simple_fraction_none_when_nothing_fits():
    assert calc.simple_fraction(0.01) is None


def test_badge_ratio_abbreviates_rare_odds_only():
    assert calc.badge_ratio(1 / 1_033_399) == "1 in 1.03M"
    assert calc.badge_ratio(0.5) == "1 in 2"


@pytest.mark.parametrize(
    ("p", "expected"),
    [
        (9.7e-7, ""),
        (0.505, "50.5%"),
        (0.01, "1%"),
        (0.09, "9%"),
        (0.005, "0.5%"),
        (1 / 1461, "0.068%"),
        (1.2e-6, "0.00012%"),
    ],
)
def test_fmt_pct(p, expected):
    assert calc.fmt_pct(p) == expected


def test_fmt_pct_never_uses_scientific_notation():
    for exponent in range(-6, 0):
        assert "e" not in calc.fmt_pct(10.0**exponent)


def test_expected_count():
    assert calc.expected_count(8_000_000_000, 0.00003) == "≈ 240,000 people"
    assert calc.expected_count(100, 0.01) == "≈ 1 person"
    assert calc.expected_count(100, 0.001) == "statistically nobody (expected 0.1)"


@pytest.mark.parametrize(
    ("phrases", "expected"),
    [
        ([], ""),
        (["a"], "a"),
        (["a", "b"], "a and b"),
        (["a", "b", "c"], "a, b and c"),
    ],
)
def test_join_phrases(phrases, expected):
    assert calc.join_phrases(phrases) == expected
