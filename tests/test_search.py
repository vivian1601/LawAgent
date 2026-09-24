import argparse
from datetime import date

import pytest

from lawagent.dense import DenseResult
from lawagent.search import (
    HybridResult,
    HybridSearcher,
    format_result,
    main,
    parse_as_of,
    reciprocal_rank_fusion,
)
from lawagent.sparse import SparseResult


def chunk(
    chunk_id: str,
    dieu_label: str,
    hierarchy_level: int = 1,
    dieu_title: str | None = None,
) -> dict:
    return {
        "chunk_id": chunk_id,
        "dieu_label": dieu_label,
        "dieu_title": dieu_title,
        "doc_type": "bo_luat",
        "hierarchy_level": hierarchy_level,
        "text_for_embedding": f"Điều {dieu_label}",
        "effective_from": "2021-01-01",
        "effective_to": None,
    }


def test_rrf_rewards_result_from_both_sources() -> None:
    a = chunk("a", "10")
    b = chunk("b", "20")
    c = chunk("c", "30")

    dense = [
        DenseResult(rank=1, score=0.9, chunk=a),
        DenseResult(rank=2, score=0.8, chunk=b),
    ]
    sparse = [
        SparseResult(
            rank=1,
            score=5.0,
            chunk=b,
            exact_article=False,
        ),
        SparseResult(
            rank=2,
            score=4.0,
            chunk=c,
            exact_article=False,
        ),
    ]

    results = reciprocal_rank_fusion(
        query="quyền người lao động",
        dense_results=dense,
        sparse_results=sparse,
    )

    assert results[0].chunk["chunk_id"] == "b"
    assert results[0].sources == ("dense", "sparse")
    assert results[0].dense_score == 0.8
    assert results[0].sparse_score == 5.0


def test_exact_article_wins_rrf_tie() -> None:
    semantic = chunk(
        "semantic",
        "10",
        hierarchy_level=2,
    )
    exact = chunk(
        "exact",
        "35",
        hierarchy_level=1,
    )

    results = reciprocal_rank_fusion(
        query="Điều 35",
        dense_results=[
            DenseResult(
                rank=1,
                score=0.9,
                chunk=semantic,
            )
        ],
        sparse_results=[
            SparseResult(
                rank=1,
                score=5.0,
                chunk=exact,
                exact_article=True,
            )
        ],
    )

    assert results[0].chunk["chunk_id"] == "exact"


def test_exact_title_wins_over_higher_rrf_score() -> None:
    exact_title = chunk(
        "article-25",
        "25",
        dieu_title="Thời gian thử việc",
    )
    related = chunk(
        "article-27",
        "27",
        dieu_title="Kết thúc thời gian thử việc",
    )

    results = reciprocal_rank_fusion(
        query="thời gian thử việc",
        dense_results=[
            DenseResult(rank=1, score=0.9, chunk=related),
            DenseResult(rank=2, score=0.8, chunk=exact_title),
        ],
        sparse_results=[
            SparseResult(
                rank=1,
                score=5.0,
                chunk=related,
                exact_article=False,
            ),
            SparseResult(
                rank=2,
                score=4.0,
                chunk=exact_title,
                exact_article=False,
            ),
        ],
    )

    assert results[0].chunk["chunk_id"] == "article-25"


class FakeDenseRetriever:
    def search(
        self,
        query: str,
        as_of: date,
        limit: int,
    ) -> list[DenseResult]:
        return []


def test_hybrid_search_filters_sparse_by_date() -> None:
    historical = {
        **chunk("historical", "35"),
        "effective_from": "2021-01-01",
        "effective_to": "2025-12-31",
    }
    current = {
        **chunk("current", "35"),
        "effective_from": "2026-07-01",
        "effective_to": None,
    }

    searcher = HybridSearcher(
        dense_retriever=FakeDenseRetriever(),
        chunks=[historical, current],
    )

    results = searcher.search(
        "Điều 35",
        as_of=date(2026, 9, 22),
    )

    assert len(results) == 1
    assert results[0].chunk["chunk_id"] == "current"
    assert results[0].sources == ("sparse",)


def test_parse_as_of_accepts_iso_date() -> None:
    assert parse_as_of("2026-09-22") == date(2026, 9, 22)


def test_parse_as_of_rejects_invalid_date() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        parse_as_of("22-09-2026")


def test_format_result_includes_scores_and_effective_range() -> None:
    result = HybridResult(
        rank=1,
        rrf_score=0.03,
        chunk={
            **chunk("current", "35"),
            "breadcrumb": "Bộ luật Lao động > Điều 35",
            "effective_to": None,
        },
        sources=("dense", "sparse"),
        dense_score=0.8,
        sparse_score=5.0,
    )

    rendered = format_result(result)

    assert "rrf=0.030000" in rendered
    assert "sources=dense,sparse" in rendered
    assert "effective=2021-01-01..open" in rendered


def test_cli_prints_hybrid_results(monkeypatch, capsys) -> None:
    class FakeHybridSearcher:
        def search(self, **kwargs) -> list[HybridResult]:
            assert kwargs["query"] == "Điều 35"
            assert kwargs["as_of"] == date(2026, 9, 22)
            return [
                HybridResult(
                    rank=1,
                    rrf_score=0.03,
                    chunk={
                        **chunk("current", "35"),
                        "breadcrumb": "Bộ luật Lao động > Điều 35",
                    },
                    sources=("dense", "sparse"),
                    dense_score=0.8,
                    sparse_score=5.0,
                )
            ]

    monkeypatch.setattr(
        "lawagent.search.HybridSearcher",
        FakeHybridSearcher,
    )

    assert main(["Điều 35", "--as-of", "2026-09-22"]) == 0
    output = capsys.readouterr().out
    assert "Query: Điều 35" in output
    assert "As of: 2026-09-22" in output
    assert "current" in output
