from datetime import date

from jobs.build_cost_index import recency_weight, units_from


def test_units_from_permit_descriptions():
    assert units_from("SPR 2019 CBC ERECT 3-STORY, 4-DWELLING UNITS RESIDENCE WITH BASEMENT") == 4
    assert units_from("PROPOSED 2 STORY/3 UNIT RESIDENCE W/BASEMENT AND 3 SPACE PARKING PAD") == 3
    assert units_from("NEW 3 STORY MIXED USE BUILDING, RETAIL AND 3 DWELLING UNITS") is None
    assert units_from("ERECT NEW COACH HOUSE, 1 DWELLING UNIT") is None
    assert units_from("ERECT NEW 4 STORY 12 DWELLING UNIT BUILDING") is None


def test_recency_weights_by_quarter():
    today = date(2026, 10, 1)
    assert recency_weight(date(2026, 9, 1), today) == 1.0
    assert recency_weight(date(2026, 3, 1), today) == 0.56
    assert round(recency_weight(date(2025, 6, 1), today), 3) == round(0.42 * 0.75**2, 3)
