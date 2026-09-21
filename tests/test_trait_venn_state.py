"""Tests for trait_venn validation, population clock, and page state."""

import pytest

from will_it_python.trait_venn import calc, population, state
from will_it_python.trait_venn.population import Clock, Snapshot
from will_it_python.trait_venn.traits import TRAITS_BY_ID
from will_it_python.trait_venn.validation import (
    Request,
    RequestError,
    can_add,
    parse_query,
    toggle,
)

NOW = 1_790_000_000.0
SNAP = Snapshot(world=Clock(8_000_000_000, NOW, 0.0), us=Clock(340_000_000, NOW, 0.0))

MINUS = "\u2212"  # blood-type labels use the true minus sign

# ---------------------------------------------------------------------------
# Selection rules
# ---------------------------------------------------------------------------


def test_can_add_below_limit_and_group_swap_at_limit():
    full = ("male", "left", "green", "red", "cb")
    assert can_add(("male",), TRAITS_BY_ID["pitch"])
    assert can_add(full, TRAITS_BY_ID["blue"])
    assert not can_add(full, TRAITS_BY_ID["pitch"])
    assert not can_add(full, TRAITS_BY_ID["blood_o_pos"])


def test_toggle_removes_active_trait():
    assert toggle(("male", "left"), "male") == ("left",)


def test_toggle_replaces_within_group_in_place():
    assert toggle(("male", "left"), "ambi") == ("male", "ambi")
    assert toggle(("male", "left"), "female") == ("female", "left")


def test_toggle_appends_until_limit():
    assert toggle(("male",), "pitch") == ("male", "pitch")
    full = ("male", "left", "green", "red", "cb")
    assert toggle(full, "pitch") == full
    assert toggle(full, "blue") == ("male", "left", "blue", "red", "cb")


def test_parse_query_defaults():
    assert parse_query({}) == Request((), "US")


def test_parse_query_valid_with_whitespace_and_toggle():
    request = parse_query(
        {"sel": [" male , left ,"], "country": ["JP"], "toggle": ["green"]}
    )
    assert request == Request(("male", "left", "green"), "JP")


@pytest.mark.parametrize(
    ("query", "message"),
    [
        ({"sel": ["nope"]}, "unknown trait"),
        ({"sel": ["male,male"]}, "duplicate"),
        ({"sel": ["left,green,red,cb,pitch,syn"]}, "at most 5"),
        ({"sel": ["male,female"]}, "exclusive group"),
        ({"country": ["XX"]}, "unknown country"),
        ({"toggle": ["nope"]}, "unknown trait id"),
    ],
)
def test_parse_query_rejects_invalid(query, message):
    with pytest.raises(RequestError, match=message):
        parse_query(query)


# ---------------------------------------------------------------------------
# Population clock
# ---------------------------------------------------------------------------


def test_clock_projects_linearly():
    assert Clock(100, 10.0, 2.0).now(15.0) == 110


US_RESPONSE = {
    "us": {
        "population": 342_880_179,
        "population_rate": 0.0346,
        "rate_interval": "second",
        "last_updated": "1790017858",
    }
}


def test_parse_popclock_uses_census_fields():
    clock = population.parse_popclock(US_RESPONSE, "us", NOW)
    assert clock == Clock(342_880_179, 1_790_017_858.0, 0.0346)


def test_parse_popclock_falls_back_for_rate_and_time():
    body = {"world": {"population": 8_212_225_975, "rate_interval": "minute"}}
    clock = population.parse_popclock(body, "world", NOW)
    assert clock == Clock(8_212_225_975, NOW, population.FALLBACK_WORLD.per_second)
    body = {
        "us": {
            "population": 342_880_179,
            "population_rate": 1,
            "rate_interval": "minute",
        }
    }
    assert (
        population.parse_popclock(body, "us", NOW).per_second
        == population.FALLBACK_US.per_second
    )


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {"us": "342880179"},
        {"world": {"population": 342_880_179}},
        {"us": {"population": True}},
        {"us": {"population": "342880179"}},
        {"us": {"population": 1_790_017}},
    ],
)
def test_parse_popclock_rejects_malformed(payload):
    assert population.parse_popclock(payload, "us", NOW) is None


def test_snapshot_live_and_fallback():
    world_response = {"world": {"population": 8_212_225_975}}
    live = population.snapshot(world_response, US_RESPONSE, NOW)
    assert live.world.base == 8_212_225_975
    assert live.us.at == 1_790_017_858.0
    assert live.source == "live from census.gov/popclock"
    partial = population.snapshot(None, US_RESPONSE, NOW)
    assert partial.world == population.FALLBACK_WORLD
    assert partial.source.startswith("partly live")
    fallback = population.snapshot(None, None, NOW)
    assert fallback.us == population.FALLBACK_US
    assert fallback.source.startswith("approximate projection")


# ---------------------------------------------------------------------------
# Page state
# ---------------------------------------------------------------------------


def build(sel, country="US"):
    return state.build_state(Request(tuple(sel), country), SNAP, NOW)


def test_countries_us_first_then_alphabetical():
    names = [c["name"] for c in state.ordered_countries()]
    assert names[0] == "United States"
    assert names[1:] == sorted(names[1:])


def test_state_headline_and_scopes():
    s = build(["female", "left", "green"])
    assert s["headline"] == {
        "is": "female, left-handed and green-eyed",
        "has": "",
        "odds": calc.ratio(0.496 * 0.10 * 0.02),
    }
    assert s["world"]["p"] == pytest.approx(0.496 * 0.10 * 0.02)
    assert s["nation"]["p"] == pytest.approx(0.505 * 0.10 * 0.09)
    assert s["countryName"] == "United States"
    assert s["population"]["source"] == SNAP.source


def test_state_has_phrases():
    s = build(["pitch", "blood_o_neg"])
    assert s["headline"]["is"] == ""
    assert s["headline"]["has"] == f"perfect pitch and O{MINUS} blood"


def test_state_categories_sorted_by_nation_prevalence():
    eyes = next(c for c in build([])["categories"] if c["name"] == "Eye color")
    assert [t["short"] for t in eyes["traits"]][:3] == ["Brown", "Blue", "Hazel"]
    eyes_jp = next(c for c in build([], "JP")["categories"] if c["name"] == "Eye color")
    assert [t["short"] for t in eyes_jp["traits"]][:2] == ["Brown", "Blue"]
    assert eyes_jp["traits"][-1]["short"] == "Gray"


def test_state_chip_slots_counts_and_disabled_at_limit():
    s = build(["male", "left", "green", "red", "cb"])
    chips = {t["id"]: t for c in s["categories"] for t in c["traits"]}
    assert chips["green"]["slot"] == 2
    assert chips["pitch"]["enabled"] is False
    assert chips["blue"]["enabled"] is True
    senses = next(c for c in s["categories"] if c["name"] == "Senses & mind")
    assert senses["selectedCount"] == 1
    assert chips["hsam"]["pct"] == ""


def test_state_diagram_labels_use_nation_prevalence():
    s = build(["female", "green", "blood_o_neg"])
    labels = {label["name"]: label["pct"] for label in s["diagram"]["labels"]}
    assert labels == {"Female": "50.5%", "Green eyes": "9%", f"Blood O{MINUS}": "6.6%"}
    assert len(s["diagram"]["ellipses"]) == 3
    assert s["diagram"]["badge"]["sets"] == 3


def test_state_regions_cover_every_mask():
    s = build(["male", "cb"])
    regions = {r["mask"]: r for r in s["regions"]}
    assert set(regions) == {1, 2, 3}
    center = regions[3]
    assert center["isCenter"]
    assert center["world"]["p"] == pytest.approx(0.504 * 0.08)
    assert regions[2]["nation"]["onlyOdds"] == calc.ratio(0.495 * 0 + 0.505 * 0.005)


def test_state_badge_splits_odds():
    badge = build(["male", "tall", "blood_o_neg", "green", "syn"])["diagram"]["badge"]
    assert badge["top"] == "1 in"
    assert badge["bottom"].endswith("K") or badge["bottom"].endswith("M")
    assert badge["r"] == 36


def test_state_badge_without_odds_split(monkeypatch):
    monkeypatch.setattr(calc, "badge_ratio", lambda p: "nearly everyone")
    badge = build(["left", "green"])["diagram"]["badge"]
    assert (badge["top"], badge["bottom"]) == ("nearly everyone", "")


def test_state_single_trait_has_no_badge():
    assert build(["left"])["diagram"]["badge"] is None


def test_state_empty_selection():
    s = build([], "JP")
    assert s["diagram"] is None
    assert s["regions"] == []
    assert s["population"]["source"] == "static 2026 estimate"
    assert s["nation"]["population"] == 123_000_000
