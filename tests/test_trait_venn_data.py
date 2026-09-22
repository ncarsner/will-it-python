"""Tests for trait_venn reference data and geometry."""

import math

import pytest

from will_it_python.trait_venn import geometry
from will_it_python.trait_venn.traits import (
    CATEGORIES,
    COUNTRIES,
    COUNTRIES_BY_CODE,
    GENDER_TRAITS,
    TRAITS,
    TRAITS_BY_ID,
    US,
    Gender,
    Side,
)

MINUS = "\u2212"  # blood-type labels use the true minus sign

# ---------------------------------------------------------------------------
# Traits and countries
# ---------------------------------------------------------------------------


def test_trait_ids_unique_and_ascii():
    ids = [t.id for t in TRAITS]
    assert len(ids) == len(set(ids)) == len(TRAITS_BY_ID)
    assert all(i.isascii() and " " not in i for i in ids)


def test_every_trait_belongs_to_a_category_and_every_category_has_traits():
    names = {c.name for c in CATEGORIES}
    assert {t.category for t in TRAITS} == names


@pytest.mark.parametrize("trait", TRAITS, ids=lambda t: t.id)
def test_prevalence_values_are_probabilities(trait):
    values = [trait.p, trait.us] + [
        v
        for table in (trait.by_gender, trait.by_gender_us)
        if table
        for v in table.values()
    ]
    assert all(0 < v < 1 for v in values if v is not None)


@pytest.mark.parametrize("trait", TRAITS, ids=lambda t: t.id)
def test_each_trait_has_exactly_one_headline_phrase(trait):
    assert (trait.is_phrase is None) != (trait.has_phrase is None)


def test_exclusive_groups_sum_to_about_one():
    groups: dict[str, list[float]] = {}
    for t in TRAITS:
        if t.group:
            groups.setdefault(t.group, []).append(t.p)
    for values in groups.values():
        assert sum(values) == pytest.approx(1, abs=0.02)


def test_gender_traits_cover_every_gender():
    assert set(GENDER_TRAITS) == set(Gender)
    assert GENDER_TRAITS[Gender.FEMALE].id == "female"
    assert CATEGORIES[0].name == "Gender"


def test_gender_dependent_traits_define_both_genders():
    for t in TRAITS:
        for table in (t.by_gender, t.by_gender_us):
            if table is not None:
                assert set(table) == set(Gender)


def test_categories_split_into_conventional_then_unconventional():
    sides = [c.side for c in CATEGORIES]
    assert sides == sorted(sides, key=lambda s: s is Side.UNCONVENTIONAL)
    assert set(sides) == set(Side)


def test_blood_type_labels_use_minus_sign_and_ascii_ids():
    trait = TRAITS_BY_ID["blood_o_neg"]
    assert trait.short == f"O{MINUS}"
    assert trait.name == f"Blood O{MINUS}"


def test_countries_unique_and_us_present():
    assert len({c.code for c in COUNTRIES}) == len(COUNTRIES) == len(COUNTRIES_BY_CODE)
    assert COUNTRIES_BY_CODE[US].name == "United States"


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n", range(1, 6))
def test_every_region_exists_and_fits_canvas(n):
    anchors = geometry.anchors(n)
    assert set(anchors) == set(range(1, 2**n))
    for a in anchors.values():
        assert 0 < a.x < geometry.CANVAS
        assert 0 < a.y < geometry.CANVAS
        assert a.clearance > 0


@pytest.mark.parametrize("n", range(1, 6))
def test_anchor_lies_in_its_region(n):
    ellipses = geometry.LAYOUTS[n]
    for mask, a in geometry.anchors(n).items():
        assert geometry.mask_at(ellipses, a.x, a.y) == mask


@pytest.mark.parametrize("n", [4, 5])
def test_center_is_small_in_crowded_layouts(n):
    anchors = geometry.anchors(n)
    center = anchors[2**n - 1].clearance
    widest = max(a.clearance for a in anchors.values())
    assert center < 90
    assert center < widest


def test_anchors_are_cached():
    assert geometry.anchors(3) is geometry.anchors(3)


def test_ellipse_contains_and_clearance():
    e = geometry.Ellipse(0, 0, 10, 5, rotation=90)
    assert e.contains(0, 9)
    assert not e.contains(9, 0)
    assert geometry.Ellipse(0, 0, 10, 10).clearance(0, 4) == pytest.approx(6)
    assert geometry.Ellipse(0, 0, 10, 10).clearance(0, 0) == pytest.approx(0)


def test_mask_at_outside_everything_is_zero():
    assert geometry.mask_at(geometry.LAYOUTS[3], 1, 1) == 0


def test_badge_radius_capped_by_layout_size():
    assert geometry.badge_radius(2) == 50
    assert geometry.badge_radius(5) == 36
    assert 24 <= geometry.badge_radius(4) <= 36


def test_three_set_layout_is_symmetric():
    xs = sorted(e.cx for e in geometry.LAYOUTS[3])
    assert math.isclose(xs[0] + xs[2], 600)


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


def test_gender_options_are_female_and_male():
    names = [t.name for t in TRAITS if t.group == "gender"]
    assert sorted(names) == ["Female", "Male"]
    assert TRAITS_BY_ID["female"].is_phrase == "female"


def test_birth_date_chips_read_as_events():
    assert TRAITS_BY_ID["xmas"].short == "on Dec 25"
    assert TRAITS_BY_ID["leap"].short == "on Feb 29"
    assert TRAITS_BY_ID["leap"].name == "Born on Feb 29"


def test_born_in_the_caul_removed():
    assert "caul" not in TRAITS_BY_ID
    assert all("caul" not in t.name.lower() for t in TRAITS)


def test_age_brackets_are_exclusive_and_named_consistently():
    ages = [t for t in TRAITS if t.category == "Age"]
    assert {t.group for t in ages} == {"age"}
    assert all(t.name.startswith("Age ") for t in ages)


def test_everyday_is_a_drill_down_category():
    everyday = next(c for c in CATEGORIES if c.name == "Everyday")
    assert everyday.side is Side.UNCONVENTIONAL


def test_handedness_chips_are_short():
    shorts = sorted(t.short for t in TRAITS if t.group == "hand")
    assert shorts == ["Ambidextrous", "Left", "Right"]


def test_drivers_license_removed():
    assert "license" not in TRAITS_BY_ID
