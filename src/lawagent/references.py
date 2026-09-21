"""Resolve structured legal references and extract their precise locator text."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any


CLAUSE_START = re.compile(r"(?m)^(\d+)\.\s+")
POINT_START = re.compile(r"(?m)^([a-zđ])\)\s+", re.IGNORECASE)


def extract_locator_text(
    article_text: str,
    clause: str | None = None,
    point: str | None = None,
) -> str:
    """Extract a referenced Khoản/Điểm, falling back to the complete article.

    The input is the normalized article text emitted by ``lawagent.parser``.
    A missing locator never produces an empty context: the complete article is
    returned so the synthesis layer can still reason conservatively.
    """
    selected = article_text.strip()
    if clause:
        matches = list(CLAUSE_START.finditer(selected))
        wanted = next((index for index, match in enumerate(matches) if match.group(1) == clause), None)
        if wanted is not None:
            start = matches[wanted].start()
            end = matches[wanted + 1].start() if wanted + 1 < len(matches) else len(selected)
            selected = selected[start:end].strip()
    if point:
        matches = list(POINT_START.finditer(selected))
        wanted = next(
            (index for index, match in enumerate(matches) if match.group(1).lower() == point.lower()),
            None,
        )
        if wanted is not None:
            start = matches[wanted].start()
            end = matches[wanted + 1].start() if wanted + 1 < len(matches) else len(selected)
            selected = selected[start:end].strip()
    return selected or article_text.strip()


def _complete_article_text(target_id: str, chunk_index: Mapping[str, Mapping[str, Any]]) -> str:
    """Rejoin an article that was split into ``__part_N`` chunks."""
    candidates = [
        (chunk_id, chunk)
        for chunk_id, chunk in chunk_index.items()
        if chunk_id == target_id or chunk_id.startswith(f"{target_id}__part_")
    ]
    candidates.sort(key=lambda item: (0 if item[0] == target_id else int(item[0].rsplit("_", 1)[-1])))
    if not candidates:
        return ""
    texts: list[str] = []
    heading = candidates[0][1]["text"].split("\n", 1)[0]
    for _, chunk in candidates:
        text = chunk["text"].strip()
        if texts and text.startswith(heading):
            text = text[len(heading) :].lstrip()
        texts.append(text)
    return "\n".join(texts).strip()


def expand_reference_context(
    chunk: Mapping[str, Any],
    chunk_index: Mapping[str, Mapping[str, Any]],
    relations: Iterable[str] = ("exception", "exclusion", "applies"),
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Resolve one level of references and return locator-specific context.

    Cross-document references remain unresolved until the temporal resolver can
    select the correct document version for the query's ``as_of`` date.
    """
    allowed = set(relations)
    expanded: list[dict[str, Any]] = []
    for reference in chunk.get("references", []):
        if reference.get("relation") not in allowed:
            continue
        target_id = reference.get("target_chunk_id")
        if not target_id:
            continue
        article_text = _complete_article_text(target_id, chunk_index)
        if not article_text:
            continue
        expanded.append(
            {
                "source_chunk_id": chunk["chunk_id"],
                "target_chunk_id": target_id,
                "relation": reference["relation"],
                "locator": {
                    "article": reference["target_article"],
                    "clause": reference.get("target_clause"),
                    "point": reference.get("target_point"),
                },
                "text": extract_locator_text(
                    article_text,
                    clause=reference.get("target_clause"),
                    point=reference.get("target_point"),
                ),
            }
        )
        if len(expanded) >= limit:
            break
    return expanded
