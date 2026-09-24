"""Temporal filtering shared by sparse and dense retrieval."""

from datetime import date, datetime, time, timezone
from typing import Iterable

from qdrant_client import models


def parse_payload_date(value: str | date) -> date:
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    # Chấp nhận cả YYYY-MM-DD và RFC 3339 từ payload Qdrant.
    return date.fromisoformat(value[:10])


def is_effective(chunk: dict, as_of: date) -> bool:
    effective_from = parse_payload_date(chunk["effective_from"])
    effective_to_value = chunk.get("effective_to")

    if effective_from > as_of:
        return False

    if effective_to_value is None:
        return True

    effective_to = parse_payload_date(effective_to_value)
    return as_of <= effective_to


def filter_effective_chunks(
    chunks: Iterable[dict],
    as_of: date,
) -> list[dict]:
    return [
        chunk
        for chunk in chunks
        if is_effective(chunk, as_of)
    ]


def build_temporal_filter(as_of: date) -> models.Filter:
    """Build the equivalent server-side Qdrant filter."""

    instant = datetime.combine(
        as_of,
        time.min,
        tzinfo=timezone.utc,
    )

    return models.Filter(
        must=[
            models.FieldCondition(
                key="effective_from",
                range=models.DatetimeRange(lte=instant),
            )
        ],
        min_should=models.MinShould(
            conditions=[
                models.IsNullCondition(
                    is_null=models.PayloadField(
                        key="effective_to"
                    )
                ),
                models.FieldCondition(
                    key="effective_to",
                    range=models.DatetimeRange(gte=instant),
                ),
            ],
            min_count=1,
        ),
    )