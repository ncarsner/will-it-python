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

    FEMALE = "female"
    MALE = "male"


@dataclass(frozen=True, slots=True)
class Category:
    """A named group of traits shown together in the picker.

    Attributes:
        name: Display name, e.g. ``"Eye color"``.
        side: Column the category is rendered in.
        by_prevalence: Sort traits most to least common; when False, keep
            their natural order (e.g. age brackets youngest to oldest).
    """

    name: str
    side: Side
    by_prevalence: bool = True


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


def _by_gender(*, female: float, male: float) -> MappingProxyType[Gender, float]:
    """Return an immutable gender-conditional prevalence mapping."""
    return MappingProxyType({Gender.FEMALE: female, Gender.MALE: male})


CATEGORIES: Final[tuple[Category, ...]] = (
    Category("Gender", Side.CONVENTIONAL),
    Category("Age", Side.CONVENTIONAL, by_prevalence=False),
    Category("Handedness", Side.CONVENTIONAL),
    Category("Eye color", Side.CONVENTIONAL),
    Category("Hair color", Side.CONVENTIONAL),
    Category("Blood type", Side.CONVENTIONAL),
    Category("Where you live", Side.CONVENTIONAL),
    Category("Everyday", Side.UNCONVENTIONAL),
    Category("Senses & mind", Side.UNCONVENTIONAL),
    Category("Health", Side.UNCONVENTIONAL),
    Category("Genetic quirks", Side.UNCONVENTIONAL),
    Category("Birth", Side.UNCONVENTIONAL),
    Category("Lifestyle", Side.UNCONVENTIONAL),
    Category("Rare experiences", Side.UNCONVENTIONAL),
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

# (id suffix, label, worldwide, US) age brackets; labels use U+2013 EN DASH.
_DASH: Final = "\u2013"
_AGE_BRACKETS: Final = (
    ("under18", "Under 18", 0.30, 0.22),
    ("18_34", f"18{_DASH}34", 0.26, 0.22),
    ("35_54", f"35{_DASH}54", 0.25, 0.25),
    ("55_64", f"55{_DASH}64", 0.09, 0.13),
    ("65plus", "65 or older", 0.10, 0.18),
)

_WORLD_2026: Final = 8_100_000_000
# Approximate counts of living people, for extremely rare traits.
_HSAM_CASES: Final = 60  # superior autobiographical memory, documented cases
_ANTARCTICA_VISITORS: Final = 1_100_000
_OLYMPIANS: Final = 100_000
_EVEREST_SUMMITERS: Final = 7_300
_SPACE_TRAVELERS: Final = 700
_NOBEL_LAUREATES: Final = 400

TRAITS: Final[tuple[Trait, ...]] = (
    # Gender
    Trait(
        "female",
        "Gender",
        "Female",
        "Female",
        0.496,
        us=0.505,
        group="gender",
        gender=Gender.FEMALE,
        is_phrase="female",
    ),
    Trait(
        "male",
        "Gender",
        "Male",
        "Male",
        0.504,
        us=0.495,
        group="gender",
        gender=Gender.MALE,
        is_phrase="male",
    ),
    # Handedness
    Trait(
        "right",
        "Handedness",
        "Right-handed",
        "Right",
        0.89,
        group="hand",
        is_phrase="right-handed",
    ),
    Trait(
        "left",
        "Handedness",
        "Left-handed",
        "Left",
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
        by_gender=_by_gender(female=0.004, male=0.06),
        by_gender_us=_by_gender(female=0.01, male=0.145),
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
        by_gender=_by_gender(female=0.005, male=0.08),
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
        by_gender=_by_gender(female=0.19, male=0.09),
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
        "on Feb 29",
        1 / 1461,
        is_phrase="a leap-day baby",
    ),
    Trait(
        "xmas",
        "Birth",
        "Born on Dec 25",
        "on Dec 25",
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
    # Age
    *(
        Trait(
            f"age_{key}",
            "Age",
            f"Age {label[0].lower()}{label[1:]}",
            label,
            p,
            us=us,
            group="age",
            is_phrase=f"{label[0].lower()}{label[1:]}",
        )
        for key, label, p, us in _AGE_BRACKETS
    ),
    # Where you live
    Trait(
        "urban",
        "Where you live",
        "Lives in a city or town",
        "City or town",
        0.58,
        us=0.83,
        group="home",
        is_phrase="a city dweller",
    ),
    Trait(
        "rural",
        "Where you live",
        "Lives in a rural area",
        "Rural",
        0.42,
        us=0.17,
        group="home",
        is_phrase="a rural resident",
    ),
    # Everyday (additions)
    Trait(
        "bilingual",
        "Everyday",
        "Speaks two or more languages",
        "Bilingual",
        0.43,
        us=0.22,
        is_phrase="bilingual",
    ),
    # Senses & mind (additions)
    Trait(
        "misoph",
        "Senses & mind",
        "Misophonia",
        "Misophonia",
        0.12,
        has_phrase="misophonia",
    ),
    Trait(
        "lucid",
        "Senses & mind",
        "Lucid dreams monthly",
        "Lucid dreamer",
        0.23,
        is_phrase="a lucid dreamer",
    ),
    # Health (additions)
    Trait(
        "myopia",
        "Health",
        "Nearsighted",
        "Nearsighted",
        0.30,
        us=0.40,
        is_phrase="nearsighted",
    ),
    Trait("adhd", "Health", "ADHD", "ADHD", 0.03, us=0.07, has_phrase="ADHD"),
    Trait(
        "dyslexia",
        "Health",
        "Dyslexia",
        "Dyslexia",
        0.07,
        has_phrase="dyslexia",
    ),
    # Genetic quirks (additions)
    Trait(
        "dryear",
        "Genetic quirks",
        "Dry earwax",
        "Dry earwax",
        0.25,
        us=0.07,
        has_phrase="dry earwax",
    ),
    Trait(
        "lefteye",
        "Genetic quirks",
        "Left-eye dominant",
        "Left-eye dominant",
        0.30,
        is_phrase="left-eye dominant",
    ),
    # Birth (additions)
    Trait(
        "preterm",
        "Birth",
        "Born premature",
        "Premature",
        0.10,
        is_phrase="a preemie",
    ),
    Trait(
        "homebirth",
        "Birth",
        "Born at home",
        "At home",
        0.17,
        us=0.015,
        is_phrase="born at home",
    ),
    # Lifestyle
    Trait(
        "veg",
        "Lifestyle",
        "Vegetarian",
        "Vegetarian",
        0.08,
        us=0.05,
        is_phrase="vegetarian",
    ),
    Trait(
        "nodrink",
        "Lifestyle",
        "Doesn't drink alcohol",
        "Non-drinker",
        0.55,
        us=0.38,
        is_phrase="a non-drinker",
    ),
    Trait(
        "smoker",
        "Lifestyle",
        "Smokes tobacco",
        "Smoker",
        0.20,
        us=0.115,
        is_phrase="a smoker",
    ),
    Trait(
        "morning",
        "Lifestyle",
        "Morning person",
        "Morning person",
        0.25,
        is_phrase="a morning person",
    ),
    Trait(
        "meditate",
        "Lifestyle",
        "Meditates regularly",
        "Meditates",
        0.10,
        us=0.17,
        is_phrase="a regular meditator",
    ),
    Trait(
        "marathon",
        "Lifestyle",
        "Has finished a marathon",
        "Marathoner",
        0.002,
        us=0.005,
        is_phrase="a marathon finisher",
    ),
    # Rare experiences
    Trait(
        "lightning",
        "Rare experiences",
        "Struck by lightning",
        "Struck by lightning",
        1 / 15_300,
        has_phrase="been struck by lightning",
    ),
    Trait(
        "antarctica",
        "Rare experiences",
        "Visited Antarctica",
        "Antarctica",
        _ANTARCTICA_VISITORS / _WORLD_2026,
        has_phrase="visited Antarctica",
    ),
    Trait(
        "olympian",
        "Rare experiences",
        "Olympian",
        "Olympian",
        _OLYMPIANS / _WORLD_2026,
        is_phrase="an Olympian",
    ),
    Trait(
        "everest",
        "Rare experiences",
        "Summited Everest",
        "Everest summit",
        _EVEREST_SUMMITERS / _WORLD_2026,
        has_phrase="summited Everest",
    ),
    Trait(
        "space",
        "Rare experiences",
        "Been to space",
        "Space",
        _SPACE_TRAVELERS / _WORLD_2026,
        has_phrase="been to space",
    ),
    Trait(
        "nobel",
        "Rare experiences",
        "Nobel laureate",
        "Nobel laureate",
        _NOBEL_LAUREATES / _WORLD_2026,
        is_phrase="a Nobel laureate",
    ),
    # Senses & mind (further additions)
    Trait(
        "hyperph",
        "Senses & mind",
        "Hyperphantasia",
        "Hyperphantasia",
        0.03,
        has_phrase="hyperphantasia",
    ),
    Trait(
        "faceblind",
        "Senses & mind",
        "Face blindness (prosopagnosia)",
        "Face blindness",
        0.025,
        is_phrase="face-blind",
    ),
    Trait(
        "anosmia",
        "Senses & mind",
        "No sense of smell (anosmia)",
        "No sense of smell",
        0.05,
        has_phrase="no sense of smell",
    ),
    Trait(
        "hyperac",
        "Senses & mind",
        "Sound sensitivity (hyperacusis)",
        "Hyperacusis",
        0.08,
        has_phrase="hyperacusis",
    ),
    Trait(
        "motion",
        "Senses & mind",
        "Prone to motion sickness",
        "Motion sickness",
        0.30,
        is_phrase="prone to motion sickness",
    ),
    Trait(
        "mirror",
        "Senses & mind",
        "Mirror-touch synesthesia",
        "Mirror-touch",
        0.016,
        has_phrase="mirror-touch synesthesia",
    ),
    Trait(
        "dyscalc",
        "Senses & mind",
        "Dyscalculia",
        "Dyscalculia",
        0.05,
        has_phrase="dyscalculia",
    ),
    # Health (further additions)
    Trait(
        "t2d",
        "Health",
        "Type 2 diabetes",
        "Type 2 diabetes",
        0.06,
        us=0.11,
        has_phrase="type 2 diabetes",
    ),
    Trait(
        "hbp",
        "Health",
        "High blood pressure",
        "High blood pressure",
        0.25,
        us=0.30,
        has_phrase="high blood pressure",
    ),
    Trait(
        "eczema",
        "Health",
        "Eczema",
        "Eczema",
        0.07,
        us=0.10,
        has_phrase="eczema",
    ),
    Trait(
        "psoriasis",
        "Health",
        "Psoriasis",
        "Psoriasis",
        0.02,
        us=0.03,
        has_phrase="psoriasis",
    ),
    Trait(
        "autism",
        "Health",
        "Autism",
        "Autism",
        0.01,
        us=0.028,
        is_phrase="autistic",
    ),
    Trait(
        "epilepsy",
        "Health",
        "Epilepsy",
        "Epilepsy",
        0.006,
        us=0.012,
        has_phrase="epilepsy",
    ),
    Trait(
        "tinnitus",
        "Health",
        "Chronic tinnitus",
        "Tinnitus",
        0.14,
        us=0.15,
        has_phrase="tinnitus",
    ),
    Trait(
        "shellfish",
        "Health",
        "Shellfish allergy",
        "Shellfish allergy",
        0.02,
        us=0.03,
        has_phrase="a shellfish allergy",
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
