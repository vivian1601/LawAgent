from datetime import date

from lawagent.temporal_filter import (
    build_temporal_filter,
    filter_effective_chunks,
    is_effective,
)


HISTORICAL = {
    "chunk_id": "old",
    "effective_from": "2021-01-01",
    "effective_to": "2025-12-31",
}

CURRENT = {
    "chunk_id": "current",
    "effective_from": "2026-07-01",
    "effective_to": None,
}


def test_effective_range_is_inclusive() -> None:
    assert is_effective(HISTORICAL, date(2021, 1, 1))
    assert is_effective(HISTORICAL, date(2025, 12, 31))


def test_chunk_is_excluded_outside_range() -> None:
    assert not is_effective(HISTORICAL, date(2020, 12, 31))
    assert not is_effective(HISTORICAL, date(2026, 1, 1))


def test_open_ended_chunk_remains_effective() -> None:
    assert is_effective(CURRENT, date(2026, 7, 1))
    assert is_effective(CURRENT, date(2030, 1, 1))


def test_filter_effective_chunks() -> None:
    chunks = [HISTORICAL, CURRENT]

    assert filter_effective_chunks(
        chunks,
        date(2023, 1, 1),
    ) == [HISTORICAL]

    assert filter_effective_chunks(
        chunks,
        date(2026, 9, 22),
    ) == [CURRENT]


def test_build_qdrant_filter() -> None:
    result = build_temporal_filter(date(2026, 9, 22))

    assert result.must
    assert result.min_should is not None
    assert result.min_should.min_count == 1
    assert len(result.min_should.conditions) == 2