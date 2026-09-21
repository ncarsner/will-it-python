"""Trait, category, and country reference data for the trait Venn app.

Prevalence values are the share of people with a trait (0 < p < 1). They are
rough published estimates intended for illustration, not medical or genetic
reference values.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

US: Final = "US"
MAX_SELECTED: Final = 5


class Side(StrEnum):
    """Which column of the page a category is shown in."""

    CONVENTIONAL = "conventional"
    UNCONVENTIONAL = "unconventional"


class Gender(StrEnum):
    """Genders used to condition gender-dependent prevalence."""

    MAN = "man"
    WOMAN = "woman"


@dataclass(frozen=True, slots=True)
class Category:
    """A named group of traits shown together in the picker.

    Attributes:
        name: Display name, e.g. ``"Eye color"``.
        side: Column the category is rendered in.
    """

    name: str
    side: Side


@dataclass(frozen=True, slots=True)
class Trait:
    """A selectable trait and its prevalence.

    Attributes:
        id: Stable identifier used in requests.
        category: Name of the owning :class:`Category`.
        name: Full display name, e.g. ``"Green eyes"``.
        short: Compact chip label, e.g. ``"Green"``.
        p: Worldwide prevalence.
        us: United States prevalence override, if known.
        group: Mutually exclusive group key; at most one trait per group may
            be selected.
        gender: Set only on the gender options themselves.
        by_gender: Worldwide prevalence conditional on gender.
        by_gender_us: United States override for ``by_gender``.
        is_phrase: Predicate for the headline ("is <phrase>").
        has_phrase: Object for the headline ("has <phrase>").
    """

    id: str
    category: str
    name: str
    short: str
    p: float
    us: float | None = None
    group: str | None = None
    gender: Gender | None = None
    by_gender: MappingProxyType[Gender, float] | None = None
    by_gender_us: MappingProxyType[Gender, float] | None = None
    is_phrase: str | None = None
    has_phrase: str | None = None


@dataclass(frozen=True, slots=True)
class Country:
    """A selectable nation of origin.

    Attributes:
        code: ISO 3166-1 alpha-2 code.
        name: Display name.
        population: Static 2026 estimate; the United States value is replaced
            by the Census population clock at runtime.
    """

    code: str
    name: str
    population: int


def _by_gender(man: float, woman: float) -> MappingProxyType[Gender, float]:
    """Return an immutable gender-conditional prevalence mapping."""
    return MappingProxyType({Gender.MAN: man, Gender.WOMAN: woman})


CATEGORIES: Final[tuple[Category, ...]] = (
    Category("Gender", Side.CONVENTIONAL),
    Category("Handedness", Side.CONVENTIONAL),
    Category("Eye color", Side.CONVENTIONAL),
    Category("Hair color", Side.CONVENTIONAL),
    Category("Blood type", Side.CONVENTIONAL),
    Category("Everyday", Side.CONVENTIONAL),
    Category("Senses & mind", Side.UNCONVENTIONAL),
    Category("Health", Side.UNCONVENTIONAL),
    Category("Genetic quirks", Side.UNCONVENTIONAL),
    Category("Birth", Side.UNCONVENTIONAL),
)

# (id suffix, label, worldwide, US). Labels use U+2212 MINUS SIGN for display;
# ids stay ASCII so they are safe in query strings.
_MINUS: Final = "\u2212"
_BLOOD_TYPES: Final = (
    ("o_pos", "O+", 0.386, 0.374),
    ("a_pos", "A+", 0.27, 0.357),
    ("b_pos", "B+", 0.22, 0.085),
    ("ab_pos", "AB+", 0.05, 0.034),
    ("o_neg", f"O{_MINUS}", 0.04, 0.066),
    ("a_neg", f"A{_MINUS}", 0.02, 0.063),
    ("b_neg", f"B{_MINUS}", 0.01, 0.015),
    ("ab_neg", f"AB{_MINUS}", 0.004, 0.006),
)

# Roughly 60 documented people worldwide have superior autobiographical memory.
_HSAM_CASES: Final = 60
_WORLD_2026: Final = 8_100_000_000

TRAITS: Final[tuple[Trait, ...]] = (
    # Gender
    Trait(
        "man",
        "Gender",
        "Man",
        "Man",
        0.504,
        us=0.495,
        group="gender",
        gender=Gender.MAN,
        is_phrase="a man",
    ),
    Trait(
        "woman",
        "Gender",
        "Woman",
        "Woman",
        0.496,
        us=0.505,
        group="gender",
        gender=Gender.WOMAN,
        is_phrase="a woman",
    ),
    # Handedness
    Trait(
        "right",
        "Handedness",
        "Right-handed",
        "Right-handed",
        0.89,
        group="hand",
        is_phrase="right-handed",
    ),
    Trait(
        "left",
        "Handedness",
        "Left-handed",
        "Left-handed",
        0.10,
        group="hand",
        is_phrase="left-handed",
    ),
    Trait(
        "ambi",
        "Handedness",
        "Ambidextrous",
        "Ambidextrous",
        0.01,
        group="hand",
        is_phrase="ambidextrous",
    ),
    # Eye color
    Trait(
        "brown",
        "Eye color",
        "Brown eyes",
        "Brown",
        0.785,
        us=0.45,
        group="eyes",
        is_phrase="brown-eyed",
    ),
    Trait(
        "blue",
        "Eye color",
        "Blue eyes",
        "Blue",
        0.09,
        us=0.27,
        group="eyes",
        is_phrase="blue-eyed",
    ),
    Trait(
        "hazel",
        "Eye color",
        "Hazel eyes",
        "Hazel",
        0.05,
        us=0.18,
        group="eyes",
        is_phrase="hazel-eyed",
    ),
    Trait(
        "amber",
        "Eye color",
        "Amber eyes",
        "Amber",
        0.05,
        us=0.005,
        group="eyes",
        is_phrase="amber-eyed",
    ),
    Trait(
        "green",
        "Eye color",
        "Green eyes",
        "Green",
        0.02,
        us=0.09,
        group="eyes",
        is_phrase="green-eyed",
    ),
    Trait(
        "gray",
        "Eye color",
        "Gray eyes",
        "Gray",
        0.005,
        us=0.005,
        group="eyes",
        is_phrase="gray-eyed",
    ),
    # Hair color
    Trait(
        "black",
        "Hair color",
        "Black hair",
        "Black",
        0.75,
        us=0.30,
        group="hair",
        is_phrase="black-haired",
    ),
    Trait(
        "brunet",
        "Hair color",
        "Brown hair",
        "Brown",
        0.19,
        us=0.52,
        group="hair",
        is_phrase="brown-haired",
    ),
    Trait(
        "blond",
        "Hair color",
        "Blond hair",
        "Blond",
        0.04,
        us=0.16,
        group="hair",
        is_phrase="blond",
    ),
    Trait(
        "red",
        "Hair color",
        "Red hair",
        "Red",
        0.015,
        us=0.02,
        group="hair",
        is_phrase="red-haired",
    ),
    # Blood type
    *(
        Trait(
            f"blood_{key}",
            "Blood type",
            f"Blood {b}",
            b,
            p,
            us=us,
            group="blood",
            has_phrase=f"{b} blood",
        )
        for key, b, p, us in _BLOOD_TYPES
    ),
    # Everyday
    Trait(
        "glasses",
        "Everyday",
        "Wears glasses/contacts",
        "Glasses/contacts",
        0.40,
        us=0.64,
        is_phrase="a glasses or contacts wearer",
    ),
    Trait(
        "tall",
        "Everyday",
        "Over 6 ft tall",
        "Over 6 ft",
        0.03,
        us=0.077,
        by_gender=_by_gender(0.06, 0.004),
        by_gender_us=_by_gender(0.145, 0.01),
        is_phrase="over 6 ft tall",
    ),
    Trait(
        "tattoo",
        "Everyday",
        "Has a tattoo",
        "Tattoo",
        0.20,
        us=0.32,
        has_phrase="a tattoo",
    ),
    Trait(
        "freckle",
        "Everyday",
        "Freckles",
        "Freckles",
        0.10,
        us=0.15,
        has_phrase="freckles",
    ),
    Trait("dimple", "Everyday", "Cheek dimples", "Dimples", 0.20, has_phrase="dimples"),
    Trait(
        "braces",
        "Everyday",
        "Had braces",
        "Had braces",
        0.15,
        us=0.45,
        is_phrase="a former braces wearer",
    ),
    # Senses & mind
    Trait(
        "cb",
        "Senses & mind",
        "Red-green color blind",
        "Color blind",
        0.045,
        by_gender=_by_gender(0.08, 0.005),
        is_phrase="color blind",
    ),
    Trait(
        "pitch",
        "Senses & mind",
        "Perfect pitch",
        "Perfect pitch",
        0.0001,
        has_phrase="perfect pitch",
    ),
    Trait(
        "syn",
        "Senses & mind",
        "Synesthesia",
        "Synesthesia",
        0.04,
        has_phrase="synesthesia",
    ),
    Trait(
        "aphan",
        "Senses & mind",
        "Aphantasia",
        "Aphantasia",
        0.03,
        has_phrase="aphantasia",
    ),
    Trait(
        "super",
        "Senses & mind",
        "Supertaster",
        "Supertaster",
        0.25,
        is_phrase="a supertaster",
    ),
    Trait(
        "sneeze",
        "Senses & mind",
        "Photic sneeze reflex",
        "Photic sneeze",
        0.25,
        has_phrase="a photic sneeze",
    ),
    Trait(
        "cilan",
        "Senses & mind",
        "Cilantro tastes like soap",
        "Cilantro = soap",
        0.10,
        is_phrase="a cilantro-hater",
    ),
    Trait(
        "hsam",
        "Senses & mind",
        "Superior autobiographical memory",
        "Total recall",
        _HSAM_CASES / _WORLD_2026,
        has_phrase="total recall of their life",
    ),
    # Health
    Trait(
        "celiac",
        "Health",
        "Celiac disease",
        "Celiac",
        0.014,
        us=0.01,
        has_phrase="celiac disease",
    ),
    Trait(
        "migr",
        "Health",
        "Migraines",
        "Migraines",
        0.14,
        by_gender=_by_gender(0.09, 0.19),
        has_phrase="migraines",
    ),
    Trait("asthma", "Health", "Asthma", "Asthma", 0.043, us=0.08, has_phrase="asthma"),
    Trait(
        "t1d",
        "Health",
        "Type 1 diabetes",
        "Type 1 diabetes",
        0.001,
        us=0.006,
        has_phrase="type 1 diabetes",
    ),
    Trait(
        "lactose",
        "Health",
        "Lactose intolerant",
        "Lactose intolerant",
        0.68,
        us=0.36,
        is_phrase="lactose intolerant",
    ),
    Trait(
        "peanut",
        "Health",
        "Peanut allergy",
        "Peanut allergy",
        0.01,
        us=0.02,
        has_phrase="a peanut allergy",
    ),
    Trait(
        "hayfev",
        "Health",
        "Hay fever",
        "Hay fever",
        0.20,
        us=0.25,
        has_phrase="hay fever",
    ),
    # Genetic quirks
    Trait(
        "morton",
        "Genetic quirks",
        "Morton's toe",
        "Morton's toe",
        0.20,
        has_phrase="Morton's toe",
    ),
    Trait(
        "hetero",
        "Genetic quirks",
        "Heterochromia",
        "Heterochromia",
        0.006,
        has_phrase="heterochromia",
    ),
    Trait(
        "hyperm",
        "Genetic quirks",
        "Hypermobile joints",
        "Hypermobile",
        0.15,
        is_phrase="double-jointed",
    ),
    Trait(
        "tongue",
        "Genetic quirks",
        "Can roll tongue",
        "Tongue roller",
        0.70,
        is_phrase="a tongue-roller",
    ),
    Trait(
        "ears",
        "Genetic quirks",
        "Can wiggle ears",
        "Ear wiggler",
        0.15,
        is_phrase="an ear-wiggler",
    ),
    Trait(
        "polyd",
        "Genetic quirks",
        "Extra finger or toe",
        "Extra digit",
        0.0015,
        has_phrase="an extra digit",
    ),
    Trait(
        "crib",
        "Genetic quirks",
        "Extra (cervical) rib",
        "Extra rib",
        0.005,
        has_phrase="an extra rib",
    ),
    # Birth
    Trait(
        "twin",
        "Birth",
        "Identical twin",
        "Identical twin",
        0.008,
        is_phrase="an identical twin",
    ),
    Trait(
        "ftwin",
        "Birth",
        "Fraternal twin",
        "Fraternal twin",
        0.016,
        is_phrase="a fraternal twin",
    ),
    Trait(
        "leap",
        "Birth",
        "Born on Feb 29",
        "Feb 29",
        1 / 1461,
        is_phrase="a leap-day baby",
    ),
    Trait(
        "xmas",
        "Birth",
        "Born on Dec 25",
        "Dec 25",
        1 / 365.25,
        is_phrase="a Christmas baby",
    ),
    Trait(
        "csect",
        "Birth",
        "Born by C-section",
        "C-section",
        0.21,
        us=0.32,
        is_phrase="a C-section baby",
    ),
    Trait(
        "caul",
        "Birth",
        "Born in the caul",
        "Born in the caul",
        1 / 80_000,
        is_phrase="born in the caul",
    ),
)

TRAITS_BY_ID: Final[MappingProxyType[str, Trait]] = MappingProxyType(
    {t.id: t for t in TRAITS}
)

GENDER_TRAITS: Final[MappingProxyType[Gender, Trait]] = MappingProxyType(
    {t.gender: t for t in TRAITS if t.gender is not None}
)

COUNTRIES: Final[tuple[Country, ...]] = (
    Country(US, "United States", 342_300_000),
    Country("AU", "Australia", 27_200_000),
    Country("BD", "Bangladesh", 176_000_000),
    Country("BR", "Brazil", 213_000_000),
    Country("CA", "Canada", 40_100_000),
    Country("CN", "China", 1_408_000_000),
    Country("FR", "France", 66_700_000),
    Country("DE", "Germany", 84_000_000),
    Country("IN", "India", 1_470_000_000),
    Country("ID", "Indonesia", 285_000_000),
    Country("IE", "Ireland", 5_300_000),
    Country("IT", "Italy", 58_900_000),
    Country("JP", "Japan", 123_000_000),
    Country("MX", "Mexico", 133_000_000),
    Country("NG", "Nigeria", 237_000_000),
    Country("PK", "Pakistan", 255_000_000),
    Country("PH", "Philippines", 117_000_000),
    Country("RU", "Russia", 143_000_000),
    Country("KR", "South Korea", 51_600_000),
    Country("SE", "Sweden", 10_600_000),
    Country("GB", "United Kingdom", 69_500_000),
)

COUNTRIES_BY_CODE: Final[MappingProxyType[str, Country]] = MappingProxyType(
    {c.code: c for c in COUNTRIES}
)
