"""Tests for will_it_python.personalities."""

import json

import dash
import plotly.graph_objects as go
import pytest

from will_it_python.personalities import (
    _VALID_WINGS,
    EnneagramType,
    MBTIType,
    PersonalityDimension,
    PersonProfile,
    ZodiacSign,
    _profile_from_dict,
    _profile_to_dict,
    add_person_to_store,
    build_figure,
    compute_axis_options,
    compute_figure,
    create_app,
    get_axis_half_range,
    get_coord,
    get_label,
    get_pole_labels,
    get_tick_labels,
    get_tick_values,
    main,
    persons_from_json,
    persons_to_json,
)

# ---------------------------------------------------------------------------
# ZodiacSign
# ---------------------------------------------------------------------------


class TestZodiacSign:
    def test_twelve_members(self) -> None:
        assert len(ZodiacSign) == 12

    def test_aries_is_zero(self) -> None:
        assert ZodiacSign.ARIES == 0

    def test_pisces_is_eleven(self) -> None:
        assert ZodiacSign.PISCES == 11

    def test_all_values_sequential(self) -> None:
        values = [int(z) for z in ZodiacSign]
        assert values == list(range(12))


# ---------------------------------------------------------------------------
# EnneagramType
# ---------------------------------------------------------------------------


class TestEnneagramType:
    @pytest.mark.parametrize(
        ("type_num", "wing", "expected"),
        [
            (1, 9, 0.75),  # wraparound left
            (1, 2, 1.25),  # right wing
            (2, 1, 1.75),  # left wing
            (2, 3, 2.25),  # right wing
            (4, 3, 3.75),  # left wing
            (4, 5, 4.25),  # right wing
            (5, 4, 4.75),
            (5, 6, 5.25),
            (8, 7, 7.75),
            (8, 9, 8.25),
            (9, 8, 8.75),
            (9, 1, 9.25),  # wraparound right
        ],
    )
    def test_to_coord(self, type_num: int, wing: int, expected: float) -> None:
        assert EnneagramType(type_num, wing).to_coord() == expected

    def test_label(self) -> None:
        assert EnneagramType(4, 5).label() == "4w5"
        assert EnneagramType(1, 9).label() == "1w9"
        assert EnneagramType(9, 1).label() == "9w1"

    def test_invalid_type_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="type_num"):
            EnneagramType(0, 9)

    def test_invalid_type_ten_raises(self) -> None:
        with pytest.raises(ValueError, match="type_num"):
            EnneagramType(10, 9)

    def test_non_adjacent_wing_raises(self) -> None:
        with pytest.raises(ValueError, match="wing"):
            EnneagramType(4, 2)  # 2 is not adjacent to 4

    def test_same_as_type_wing_raises(self) -> None:
        with pytest.raises(ValueError, match="wing"):
            EnneagramType(5, 5)

    def test_all_nine_types_both_wings_valid(self) -> None:
        for t in range(1, 10):
            for w in _VALID_WINGS[t]:
                e = EnneagramType(t, w)
                coord = e.to_coord()
                assert abs(coord - t) == pytest.approx(0.25, abs=1e-9)


# ---------------------------------------------------------------------------
# MBTIType
# ---------------------------------------------------------------------------


class TestMBTIType:
    @pytest.mark.parametrize(
        ("code", "extraverted", "intuitive", "thinking", "judging", "coord", "label"),
        [
            ("ENTJ", True, True, True, True, 15, "ENTJ"),
            ("ENTP", True, True, True, False, 14, "ENTP"),
            ("ENFJ", True, True, False, True, 13, "ENFJ"),
            ("ENFP", True, True, False, False, 12, "ENFP"),
            ("ESTJ", True, False, True, True, 11, "ESTJ"),
            ("ESTP", True, False, True, False, 10, "ESTP"),
            ("ESFJ", True, False, False, True, 9, "ESFJ"),
            ("ESFP", True, False, False, False, 8, "ESFP"),
            ("INTJ", False, True, True, True, 7, "INTJ"),
            ("INTP", False, True, True, False, 6, "INTP"),
            ("INFJ", False, True, False, True, 5, "INFJ"),
            ("INFP", False, True, False, False, 4, "INFP"),
            ("ISTJ", False, False, True, True, 3, "ISTJ"),
            ("ISTP", False, False, True, False, 2, "ISTP"),
            ("ISFJ", False, False, False, True, 1, "ISFJ"),
            ("ISFP", False, False, False, False, 0, "ISFP"),
        ],
    )
    def test_from_str_all_16_types(
        self,
        code: str,
        extraverted: bool,
        intuitive: bool,
        thinking: bool,
        judging: bool,
        coord: int,
        label: str,
    ) -> None:
        m = MBTIType.from_str(code)
        assert m.extraverted == extraverted
        assert m.intuitive == intuitive
        assert m.thinking == thinking
        assert m.judging == judging
        assert m.to_coord() == coord
        assert m.label() == label

    def test_from_str_lowercase_normalizes(self) -> None:
        m = MBTIType.from_str("enfp")
        assert m.label() == "ENFP"

    def test_from_str_mixed_case_normalizes(self) -> None:
        m = MBTIType.from_str("eNfP")
        assert m.label() == "ENFP"

    def test_from_str_too_short_raises(self) -> None:
        with pytest.raises(ValueError, match="exactly 4"):
            MBTIType.from_str("ENF")

    def test_from_str_too_long_raises(self) -> None:
        with pytest.raises(ValueError, match="exactly 4"):
            MBTIType.from_str("ENFPX")

    def test_from_str_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="exactly 4"):
            MBTIType.from_str("")

    def test_from_str_bad_ei_raises(self) -> None:
        with pytest.raises(ValueError, match="E or I"):
            MBTIType.from_str("XNFP")

    def test_from_str_bad_ns_raises(self) -> None:
        with pytest.raises(ValueError, match="N or S"):
            MBTIType.from_str("EXFP")

    def test_from_str_bad_tf_raises(self) -> None:
        with pytest.raises(ValueError, match="T or F"):
            MBTIType.from_str("ENXP")

    def test_from_str_bad_jp_raises(self) -> None:
        with pytest.raises(ValueError, match="J or P"):
            MBTIType.from_str("ENFX")


# ---------------------------------------------------------------------------
# Coordinate & tick helpers
# ---------------------------------------------------------------------------


class TestGetCoord:
    def test_zodiac_present(self) -> None:
        p = PersonProfile(name="A", zodiac=ZodiacSign.ARIES)
        assert get_coord(p, PersonalityDimension.ZODIAC) == 0.0

    def test_zodiac_scorpio(self) -> None:
        p = PersonProfile(name="A", zodiac=ZodiacSign.SCORPIO)
        assert get_coord(p, PersonalityDimension.ZODIAC) == 7.0

    def test_zodiac_missing(self) -> None:
        p = PersonProfile(name="A")
        assert get_coord(p, PersonalityDimension.ZODIAC) is None

    def test_enneagram_present(self) -> None:
        p = PersonProfile(name="A", enneagram=EnneagramType(4, 5))
        assert get_coord(p, PersonalityDimension.ENNEAGRAM) == 4.25

    def test_enneagram_missing(self) -> None:
        p = PersonProfile(name="A")
        assert get_coord(p, PersonalityDimension.ENNEAGRAM) is None

    def test_mbti_present(self) -> None:
        p = PersonProfile(name="A", mbti=MBTIType.from_str("ENFP"))
        assert get_coord(p, PersonalityDimension.MBTI) == 12.0

    def test_mbti_missing(self) -> None:
        p = PersonProfile(name="A")
        assert get_coord(p, PersonalityDimension.MBTI) is None


class TestGetTickValues:
    def test_zodiac_has_twelve(self) -> None:
        vals = get_tick_values(PersonalityDimension.ZODIAC)
        assert len(vals) == 12

    def test_zodiac_range(self) -> None:
        vals = get_tick_values(PersonalityDimension.ZODIAC)
        assert vals[0] == 0.0
        assert vals[11] == 11.0

    def test_enneagram_has_eighteen(self) -> None:
        vals = get_tick_values(PersonalityDimension.ENNEAGRAM)
        assert len(vals) == 18

    def test_enneagram_contains_wraparound_coords(self) -> None:
        vals = get_tick_values(PersonalityDimension.ENNEAGRAM)
        assert 0.75 in vals  # 1w9
        assert 9.25 in vals  # 9w1

    def test_enneagram_sorted(self) -> None:
        vals = get_tick_values(PersonalityDimension.ENNEAGRAM)
        assert vals == sorted(vals)

    def test_mbti_has_sixteen(self) -> None:
        vals = get_tick_values(PersonalityDimension.MBTI)
        assert len(vals) == 16

    def test_mbti_range(self) -> None:
        vals = get_tick_values(PersonalityDimension.MBTI)
        assert vals[0] == 0.0
        assert vals[15] == 15.0


class TestGetTickLabels:
    def test_zodiac_first_and_last(self) -> None:
        labels = get_tick_labels(PersonalityDimension.ZODIAC)
        assert labels[0] == "Aries"
        assert labels[11] == "Pisces"

    def test_zodiac_count(self) -> None:
        assert len(get_tick_labels(PersonalityDimension.ZODIAC)) == 12

    def test_enneagram_count(self) -> None:
        assert len(get_tick_labels(PersonalityDimension.ENNEAGRAM)) == 18

    def test_enneagram_contains_wraparound_labels(self) -> None:
        labels = get_tick_labels(PersonalityDimension.ENNEAGRAM)
        assert "1w9" in labels
        assert "9w1" in labels

    def test_mbti_count(self) -> None:
        assert len(get_tick_labels(PersonalityDimension.MBTI)) == 16

    def test_mbti_contains_known_types(self) -> None:
        labels = get_tick_labels(PersonalityDimension.MBTI)
        assert "ENTJ" in labels
        assert "INFP" in labels
        assert "ISFP" in labels


class TestGetLabel:
    def test_zodiac_zero_is_aries(self) -> None:
        assert get_label(PersonalityDimension.ZODIAC, 0.0) == "Aries"

    def test_zodiac_seven_is_scorpio(self) -> None:
        assert get_label(PersonalityDimension.ZODIAC, 7.0) == "Scorpio"

    def test_mbti_twelve_is_enfp(self) -> None:
        assert get_label(PersonalityDimension.MBTI, 12.0) == "ENFP"

    def test_mbti_fifteen_is_entj(self) -> None:
        assert get_label(PersonalityDimension.MBTI, 15.0) == "ENTJ"

    def test_enneagram_4w5(self) -> None:
        assert get_label(PersonalityDimension.ENNEAGRAM, 4.25) == "4w5"

    def test_enneagram_1w9(self) -> None:
        assert get_label(PersonalityDimension.ENNEAGRAM, 0.75) == "1w9"

    def test_unknown_coord_returns_string(self) -> None:
        result = get_label(PersonalityDimension.ZODIAC, 99.0)
        assert "99" in result


# ---------------------------------------------------------------------------
# New axis helpers
# ---------------------------------------------------------------------------


class TestGetAxisHalfRange:
    def test_zodiac(self) -> None:
        assert get_axis_half_range(PersonalityDimension.ZODIAC) == 5.5

    def test_enneagram(self) -> None:
        assert get_axis_half_range(PersonalityDimension.ENNEAGRAM) == pytest.approx(
            4.25
        )

    def test_mbti(self) -> None:
        assert get_axis_half_range(PersonalityDimension.MBTI) == 7.5


class TestGetPoleLabels:
    def test_zodiac_lower_contains_aries(self) -> None:
        lower, _ = get_pole_labels(PersonalityDimension.ZODIAC)
        assert "Aries" in lower

    def test_zodiac_upper_contains_libra(self) -> None:
        _, upper = get_pole_labels(PersonalityDimension.ZODIAC)
        assert "Libra" in upper

    def test_enneagram_lower_mentions_1(self) -> None:
        lower, _ = get_pole_labels(PersonalityDimension.ENNEAGRAM)
        assert "1" in lower

    def test_enneagram_upper_mentions_5(self) -> None:
        _, upper = get_pole_labels(PersonalityDimension.ENNEAGRAM)
        assert "5" in upper

    def test_mbti_lower_is_introverted(self) -> None:
        lower, _ = get_pole_labels(PersonalityDimension.MBTI)
        assert "Intro" in lower

    def test_mbti_upper_is_extraverted(self) -> None:
        _, upper = get_pole_labels(PersonalityDimension.MBTI)
        assert "Extra" in upper


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


class TestSerialization:
    def _full_person(self) -> PersonProfile:
        return PersonProfile(
            name="Test",
            zodiac=ZodiacSign.SCORPIO,
            enneagram=EnneagramType(4, 5),
            mbti=MBTIType.from_str("ENFP"),
        )

    def _null_person(self) -> PersonProfile:
        return PersonProfile(name="Null")

    def test_profile_roundtrip_full(self) -> None:
        p = self._full_person()
        assert _profile_from_dict(_profile_to_dict(p)) == p

    def test_profile_roundtrip_nulls(self) -> None:
        p = self._null_person()
        assert _profile_from_dict(_profile_to_dict(p)) == p

    def test_profile_to_dict_zodiac_is_int(self) -> None:
        d = _profile_to_dict(self._full_person())
        assert isinstance(d["zodiac"], int)

    def test_profile_to_dict_null_zodiac_is_none(self) -> None:
        d = _profile_to_dict(self._null_person())
        assert d["zodiac"] is None

    def test_persons_to_json_roundtrip(self) -> None:
        persons = [self._full_person(), self._null_person()]
        result = persons_from_json(persons_to_json(persons))
        assert [p.name for p in result] == ["Test", "Null"]
        assert result[0].zodiac == ZodiacSign.SCORPIO
        assert result[1].zodiac is None

    def test_persons_to_json_is_valid_json(self) -> None:
        raw = persons_to_json([self._full_person()])
        parsed = json.loads(raw)
        assert isinstance(parsed, list)
        assert len(parsed) == 1

    def test_empty_list_roundtrip(self) -> None:
        assert persons_from_json(persons_to_json([])) == []


# ---------------------------------------------------------------------------
# Figure builder
# ---------------------------------------------------------------------------


@pytest.fixture
def complete_persons() -> list[PersonProfile]:
    return [
        PersonProfile(
            name="A",
            zodiac=ZodiacSign.ARIES,
            enneagram=EnneagramType(4, 5),
            mbti=MBTIType.from_str("ENFP"),
        ),
        PersonProfile(
            name="B",
            zodiac=ZodiacSign.LEO,
            enneagram=EnneagramType(8, 7),
            mbti=MBTIType.from_str("ESTJ"),
        ),
    ]


@pytest.fixture
def person_missing_mbti() -> PersonProfile:
    return PersonProfile(
        name="NoMBTI",
        zodiac=ZodiacSign.ARIES,
        enneagram=EnneagramType(4, 5),
        mbti=None,
    )


@pytest.fixture
def person_missing_zodiac() -> PersonProfile:
    return PersonProfile(
        name="NoZodiac",
        zodiac=None,
        enneagram=EnneagramType(4, 5),
        mbti=MBTIType.from_str("ENFP"),
    )


class TestBuildFigure:
    def test_3d_contains_surface(self, complete_persons: list[PersonProfile]) -> None:
        fig = build_figure(
            complete_persons,
            x_dim=PersonalityDimension.ZODIAC,
            y_dim=PersonalityDimension.ENNEAGRAM,
            z_dim=PersonalityDimension.MBTI,
        )
        assert any(isinstance(t, go.Surface) for t in fig.data)

    def test_3d_contains_scatter3d_for_persons(
        self, complete_persons: list[PersonProfile]
    ) -> None:
        fig = build_figure(
            complete_persons,
            x_dim=PersonalityDimension.ZODIAC,
            y_dim=PersonalityDimension.ENNEAGRAM,
            z_dim=PersonalityDimension.MBTI,
        )
        scatter3d = [t for t in fig.data if isinstance(t, go.Scatter3d)]
        person_traces = [t for t in scatter3d if t.name == "Complete"]
        assert len(person_traces) == 1

    def test_3d_contains_great_circle_loops(
        self, complete_persons: list[PersonProfile]
    ) -> None:
        fig = build_figure(
            complete_persons,
            x_dim=PersonalityDimension.ZODIAC,
            y_dim=PersonalityDimension.ENNEAGRAM,
            z_dim=PersonalityDimension.MBTI,
        )
        line_traces = [
            t for t in fig.data if isinstance(t, go.Scatter3d) and t.mode == "lines"
        ]
        assert len(line_traces) == 3

    def test_3d_contains_octant_labels(
        self, complete_persons: list[PersonProfile]
    ) -> None:
        fig = build_figure(
            complete_persons,
            x_dim=PersonalityDimension.ZODIAC,
            y_dim=PersonalityDimension.ENNEAGRAM,
            z_dim=PersonalityDimension.MBTI,
        )
        text_traces = [
            t for t in fig.data if isinstance(t, go.Scatter3d) and t.mode == "text"
        ]
        assert len(text_traces) == 1
        assert text_traces[0].x is not None
        assert len(text_traces[0].x) == 8  # type: ignore[arg-type]

    def test_2d_first_trace_is_scatter(
        self, complete_persons: list[PersonProfile]
    ) -> None:
        fig = build_figure(
            complete_persons,
            x_dim=PersonalityDimension.ZODIAC,
            y_dim=PersonalityDimension.ENNEAGRAM,
            z_dim=None,
        )
        assert isinstance(fig.data[0], go.Scatter)

    def test_2d_contains_no_surface(
        self, complete_persons: list[PersonProfile]
    ) -> None:
        fig = build_figure(
            complete_persons,
            x_dim=PersonalityDimension.ZODIAC,
            y_dim=PersonalityDimension.ENNEAGRAM,
            z_dim=None,
        )
        assert not any(isinstance(t, go.Surface) for t in fig.data)

    def test_2d_contains_quadrant_labels(
        self, complete_persons: list[PersonProfile]
    ) -> None:
        fig = build_figure(
            complete_persons,
            x_dim=PersonalityDimension.ZODIAC,
            y_dim=PersonalityDimension.ENNEAGRAM,
            z_dim=None,
        )
        text_scatters = [
            t for t in fig.data if isinstance(t, go.Scatter) and t.mode == "text"
        ]
        assert len(text_scatters) == 1
        assert text_scatters[0].x is not None
        assert len(text_scatters[0].x) == 4  # type: ignore[arg-type]

    def test_none_x_dim_returns_empty_figure(self) -> None:
        fig = build_figure(
            [],
            x_dim=None,
            y_dim=PersonalityDimension.ENNEAGRAM,
            z_dim=PersonalityDimension.MBTI,
        )
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0

    def test_none_y_dim_returns_empty_figure(self) -> None:
        fig = build_figure(
            [],
            x_dim=PersonalityDimension.ZODIAC,
            y_dim=None,
            z_dim=PersonalityDimension.MBTI,
        )
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0

    def test_empty_persons_3d_returns_figure(self) -> None:
        fig = build_figure(
            [],
            x_dim=PersonalityDimension.ZODIAC,
            y_dim=PersonalityDimension.ENNEAGRAM,
            z_dim=PersonalityDimension.MBTI,
        )
        assert isinstance(fig, go.Figure)
        assert any(isinstance(t, go.Surface) for t in fig.data)

    def test_empty_persons_2d_returns_figure(self) -> None:
        fig = build_figure(
            [],
            x_dim=PersonalityDimension.ZODIAC,
            y_dim=PersonalityDimension.ENNEAGRAM,
            z_dim=None,
        )
        assert isinstance(fig, go.Figure)
        assert isinstance(fig.data[0], go.Scatter)

    def test_missing_data_include_creates_hollow_trace(
        self,
        complete_persons: list[PersonProfile],
        person_missing_mbti: PersonProfile,
    ) -> None:
        fig = build_figure(
            [person_missing_mbti, *complete_persons],
            x_dim=PersonalityDimension.ZODIAC,
            y_dim=PersonalityDimension.ENNEAGRAM,
            z_dim=PersonalityDimension.MBTI,
            include_missing=True,
        )
        symbols = [
            str(t.marker.symbol)
            for t in fig.data
            if hasattr(t, "marker") and t.marker is not None
        ]  # type: ignore[union-attr]
        assert any("circle-open" in s for s in symbols)

    def test_missing_data_excluded_when_flag_false(
        self,
        complete_persons: list[PersonProfile],
        person_missing_mbti: PersonProfile,
    ) -> None:
        fig = build_figure(
            [person_missing_mbti, *complete_persons],
            x_dim=PersonalityDimension.ZODIAC,
            y_dim=PersonalityDimension.ENNEAGRAM,
            z_dim=PersonalityDimension.MBTI,
            include_missing=False,
        )
        all_names: list[str] = []
        for trace in fig.data:
            if hasattr(trace, "text") and trace.text:  # type: ignore[union-attr]
                if isinstance(trace.text, str):
                    all_names.append(trace.text)
                else:
                    all_names.extend(trace.text)  # type: ignore[arg-type]
        assert "NoMBTI" not in all_names

    def test_2d_missing_zodiac_hollow_trace(
        self,
        complete_persons: list[PersonProfile],
        person_missing_zodiac: PersonProfile,
    ) -> None:
        fig = build_figure(
            [person_missing_zodiac, *complete_persons],
            x_dim=PersonalityDimension.ZODIAC,
            y_dim=PersonalityDimension.ENNEAGRAM,
            z_dim=None,
            include_missing=True,
        )
        symbols = [
            str(t.marker.symbol)
            for t in fig.data
            if hasattr(t, "marker") and t.marker is not None
        ]  # type: ignore[union-attr]
        assert any("x-open" in s for s in symbols)

    def test_returns_go_figure_instance(
        self, complete_persons: list[PersonProfile]
    ) -> None:
        fig = build_figure(
            complete_persons,
            x_dim=PersonalityDimension.ENNEAGRAM,
            y_dim=PersonalityDimension.MBTI,
            z_dim=PersonalityDimension.ZODIAC,
        )
        assert isinstance(fig, go.Figure)

    def test_2d_all_missing_no_complete_trace(self) -> None:
        only_missing = PersonProfile(
            name="OnlyMissing",
            zodiac=None,
            enneagram=EnneagramType(4, 5),
            mbti=MBTIType.from_str("ENFP"),
        )
        fig = build_figure(
            [only_missing],
            x_dim=PersonalityDimension.ZODIAC,
            y_dim=PersonalityDimension.ENNEAGRAM,
            z_dim=None,
            include_missing=True,
        )
        symbols = [
            str(t.marker.symbol)
            for t in fig.data
            if hasattr(t, "marker") and t.marker is not None
        ]  # type: ignore[union-attr]
        assert any("x-open" in s for s in symbols)


# ---------------------------------------------------------------------------
# Callback logic (pure helpers)
# ---------------------------------------------------------------------------


class TestComputeAxisOptions:
    def test_y_and_z_disabled_in_x_options(self) -> None:
        x_opts, _, _ = compute_axis_options("zodiac", "enneagram", "mbti")
        disabled = {o["value"] for o in x_opts if o.get("disabled")}
        assert "enneagram" in disabled
        assert "mbti" in disabled

    def test_x_and_z_disabled_in_y_options(self) -> None:
        _, y_opts, _ = compute_axis_options("zodiac", "enneagram", "mbti")
        disabled = {o["value"] for o in y_opts if o.get("disabled")}
        assert "zodiac" in disabled
        assert "mbti" in disabled

    def test_x_and_y_disabled_in_z_options(self) -> None:
        _, _, z_opts = compute_axis_options("zodiac", "enneagram", "mbti")
        disabled = {o["value"] for o in z_opts if o.get("disabled")}
        assert "zodiac" in disabled
        assert "enneagram" in disabled

    def test_none_values_not_disabled(self) -> None:
        x_opts, y_opts, z_opts = compute_axis_options(None, None, None)
        for opts in (x_opts, y_opts, z_opts):
            assert not any(o.get("disabled") for o in opts)

    def test_returns_three_option_lists(self) -> None:
        result = compute_axis_options("zodiac", "enneagram", "mbti")
        assert len(result) == 3
        for opts in result:
            assert len(opts) == 3

    def test_null_z_not_excluded_from_siblings(self) -> None:
        x_opts, y_opts, _ = compute_axis_options("zodiac", "enneagram", None)
        x_disabled = {o["value"] for o in x_opts if o.get("disabled")}
        y_disabled = {o["value"] for o in y_opts if o.get("disabled")}
        assert "mbti" not in x_disabled
        assert "mbti" not in y_disabled


class TestComputeFigure:
    def _store(self) -> str:
        return persons_to_json(
            [
                PersonProfile(
                    name="X",
                    zodiac=ZodiacSign.ARIES,
                    enneagram=EnneagramType(4, 5),
                    mbti=MBTIType.from_str("ENFP"),
                )
            ]
        )

    def test_returns_figure_3d(self) -> None:
        fig = compute_figure(self._store(), "zodiac", "enneagram", "mbti", ["show"])
        assert isinstance(fig, go.Figure)
        assert any(isinstance(t, go.Surface) for t in fig.data)

    def test_returns_figure_2d(self) -> None:
        fig = compute_figure(self._store(), "zodiac", "enneagram", None, ["show"])
        assert isinstance(fig, go.Figure)
        assert isinstance(fig.data[0], go.Scatter)

    def test_null_x_returns_empty_figure(self) -> None:
        fig = compute_figure(self._store(), None, "enneagram", "mbti", ["show"])
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 0

    def test_include_missing_false_excludes(self) -> None:
        store = persons_to_json(
            [PersonProfile(name="Miss", zodiac=None, enneagram=EnneagramType(4, 5))]
        )
        fig = compute_figure(store, "zodiac", "enneagram", "mbti", [])
        all_names: list[str] = []
        for trace in fig.data:
            if hasattr(trace, "text") and trace.text:  # type: ignore[union-attr]
                texts = (
                    [trace.text] if isinstance(trace.text, str) else list(trace.text)
                )  # type: ignore[arg-type]
                all_names.extend(texts)
        assert "Miss" not in all_names

    def test_include_missing_true_includes(self) -> None:
        store = persons_to_json(
            [PersonProfile(name="Miss", zodiac=None, enneagram=EnneagramType(4, 5))]
        )
        fig = compute_figure(store, "zodiac", "enneagram", "mbti", ["show"])
        all_names: list[str] = []
        for trace in fig.data:
            if hasattr(trace, "text") and trace.text:  # type: ignore[union-attr]
                texts = (
                    [trace.text] if isinstance(trace.text, str) else list(trace.text)
                )  # type: ignore[arg-type]
                all_names.extend(texts)
        assert "Miss" in all_names


class TestAddPersonToStore:
    def _empty_store(self) -> str:
        return persons_to_json([])

    def test_adds_person_with_all_fields(self) -> None:
        result = add_person_to_store(
            1, self._empty_store(), "Tester", "7", "4", "5", "ENFP"
        )
        persons = persons_from_json(result)
        assert len(persons) == 1
        p = persons[0]
        assert p.name == "Tester"
        assert p.zodiac == ZodiacSign.SCORPIO
        assert p.enneagram == EnneagramType(4, 5)
        assert p.mbti is not None
        assert p.mbti.label() == "ENFP"

    def test_adds_person_with_no_optional_fields(self) -> None:
        result = add_person_to_store(
            1, self._empty_store(), "Bare", None, None, None, None
        )
        persons = persons_from_json(result)
        assert len(persons) == 1
        assert persons[0].name == "Bare"
        assert persons[0].zodiac is None
        assert persons[0].enneagram is None
        assert persons[0].mbti is None

    def test_empty_name_returns_unchanged_store(self) -> None:
        store = self._empty_store()
        result = add_person_to_store(1, store, "", None, None, None, None)
        assert result == store

    def test_blank_name_returns_unchanged_store(self) -> None:
        store = self._empty_store()
        result = add_person_to_store(1, store, "   ", None, None, None, None)
        assert result == store

    def test_none_name_returns_unchanged_store(self) -> None:
        store = self._empty_store()
        result = add_person_to_store(1, store, None, None, None, None, None)
        assert result == store

    def test_appends_to_existing_persons(self) -> None:
        existing = persons_to_json(
            [PersonProfile(name="Existing", zodiac=ZodiacSign.ARIES)]
        )
        result = add_person_to_store(1, existing, "New", None, None, None, None)
        persons = persons_from_json(result)
        assert len(persons) == 2
        assert persons[0].name == "Existing"
        assert persons[1].name == "New"

    def test_invalid_zodiac_results_in_none_zodiac(self) -> None:
        result = add_person_to_store(
            1, self._empty_store(), "Test", "999", None, None, None
        )
        persons = persons_from_json(result)
        assert persons[0].zodiac is None

    def test_invalid_enneagram_results_in_none_enneagram(self) -> None:
        result = add_person_to_store(
            1,
            self._empty_store(),
            "Test",
            None,
            "4",
            "2",
            None,  # 4w2 is invalid
        )
        persons = persons_from_json(result)
        assert persons[0].enneagram is None

    def test_invalid_mbti_results_in_none_mbti(self) -> None:
        result = add_person_to_store(
            1, self._empty_store(), "Test", None, None, None, "XXXX"
        )
        persons = persons_from_json(result)
        assert persons[0].mbti is None

    def test_name_is_stripped(self) -> None:
        result = add_person_to_store(
            1, self._empty_store(), "  Padded  ", None, None, None, None
        )
        persons = persons_from_json(result)
        assert persons[0].name == "Padded"


# ---------------------------------------------------------------------------
# Dash app
# ---------------------------------------------------------------------------


class TestCreateApp:
    def test_returns_dash_instance(self) -> None:
        app = create_app()
        assert isinstance(app, dash.Dash)

    def test_layout_not_none(self) -> None:
        app = create_app()
        assert app.layout is not None

    def test_custom_persons_accepted(self) -> None:
        persons = [PersonProfile(name="Custom", zodiac=ZodiacSign.ARIES)]
        app = create_app(persons=persons)
        assert app.layout is not None

    def test_empty_persons_list_accepted(self) -> None:
        app = create_app(persons=[])
        assert app.layout is not None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestMain:
    def test_returns_zero(self, mocker: pytest.MonkeyPatch) -> None:
        mocker.patch("will_it_python.personalities.dash.Dash.run")
        assert main(argv=[]) == 0

    def test_default_port_is_8050(self, mocker: pytest.MonkeyPatch) -> None:
        mock_run = mocker.patch("will_it_python.personalities.dash.Dash.run")
        main(argv=[])
        _, kwargs = mock_run.call_args
        assert kwargs.get("port") == 8050

    def test_custom_port(self, mocker: pytest.MonkeyPatch) -> None:
        mock_run = mocker.patch("will_it_python.personalities.dash.Dash.run")
        main(argv=["--port", "9000"])
        _, kwargs = mock_run.call_args
        assert kwargs.get("port") == 9000

    def test_debug_flag(self, mocker: pytest.MonkeyPatch) -> None:
        mock_run = mocker.patch("will_it_python.personalities.dash.Dash.run")
        main(argv=["--debug"])
        _, kwargs = mock_run.call_args
        assert kwargs.get("debug") is True

    def test_debug_false_by_default(self, mocker: pytest.MonkeyPatch) -> None:
        mock_run = mocker.patch("will_it_python.personalities.dash.Dash.run")
        main(argv=[])
        _, kwargs = mock_run.call_args
        assert kwargs.get("debug") is False
