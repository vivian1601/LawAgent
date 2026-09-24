"""Hybrid retrieval using dense search, BM25 and RRF."""

import argparse
import sys
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Sequence

from lawagent.dense import DenseResult, DenseRetriever
from lawagent.sparse import (
    BM25Index,
    SparseResult,
    extract_article_label,
    load_chunks,
    normalize_text,
)
from lawagent.temporal_filter import filter_effective_chunks


RRF_K = 60
RETRIEVAL_LIMIT = 10


@dataclass(frozen=True)
class HybridResult:
    rank: int
    rrf_score: float
    chunk: dict
    sources: tuple[str, ...]
    dense_score: float | None
    sparse_score: float | None


def reciprocal_rank_fusion(
    query: str,
    dense_results: Iterable[DenseResult],
    sparse_results: Iterable[SparseResult],
    limit: int = 5,
    k: int = RRF_K,
) -> list[HybridResult]:
    if limit < 1:
        raise ValueError("Limit must be positive")

    if k < 1:
        raise ValueError("RRF k must be positive")

    entries: dict[str, dict] = {}

    # Sparse được xử lý trước để tie ổn định ưu tiên lexical match.
    ranked_sources = (
        ("sparse", sparse_results),
        ("dense", dense_results),
    )

    for source, results in ranked_sources:
        for result in results:
            chunk_id = result.chunk.get("chunk_id")

            if not chunk_id:
                raise ValueError(
                    f"{source} result has no chunk_id"
                )

            entry = entries.setdefault(
                chunk_id,
                {
                    "chunk": result.chunk,
                    "rrf_score": 0.0,
                    "sources": set(),
                    "dense_score": None,
                    "sparse_score": None,
                },
            )

            entry["rrf_score"] += 1.0 / (k + result.rank)
            entry["sources"].add(source)

            if source == "dense":
                entry["dense_score"] = result.score
            else:
                entry["sparse_score"] = result.score

    article_label = extract_article_label(query)

    def sort_key(entry: dict) -> tuple:
        chunk = entry["chunk"]

        exact_article = (
            article_label is not None
            and str(chunk.get("dieu_label", "")).casefold()
            == article_label.casefold()
        )
        exact_title = (
            normalize_text(query)
            == normalize_text(str(chunk.get("dieu_title", "")))
        )

        document_priority = {
            "hien_phap": 4,
            "bo_luat": 3,
            "luat": 2,
            "nghi_dinh": 1,
        }.get(str(chunk.get("doc_type", "")), 0)

        hierarchy_priority = (
            -int(chunk.get("hierarchy_level", 999))
            if exact_article
            else 0
        )

        return (
            exact_article,
            exact_title,
            document_priority if exact_article else 0,
            hierarchy_priority,
            entry["rrf_score"],
        )

    ranked = sorted(
        entries.values(),
        key=sort_key,
        reverse=True,
    )

    return [
        HybridResult(
            rank=rank,
            rrf_score=entry["rrf_score"],
            chunk=entry["chunk"],
            sources=tuple(sorted(entry["sources"])),
            dense_score=entry["dense_score"],
            sparse_score=entry["sparse_score"],
        )
        for rank, entry in enumerate(
            ranked[:limit],
            start=1,
        )
    ]


class HybridSearcher:
    def __init__(
        self,
        dense_retriever: DenseRetriever | None = None,
        chunks: list[dict] | None = None,
    ) -> None:
        self.dense = dense_retriever or DenseRetriever()
        self.chunks = chunks if chunks is not None else load_chunks()

    def search(
        self,
        query: str,
        as_of: date,
        limit: int = 5,
        retrieval_limit: int = RETRIEVAL_LIMIT,
    ) -> list[HybridResult]:
        query = query.strip()

        if not query:
            raise ValueError("Query must not be empty")

        effective_chunks = filter_effective_chunks(
            self.chunks,
            as_of,
        )

        if not effective_chunks:
            return []

        sparse_results = BM25Index(
            effective_chunks
        ).search(
            query,
            limit=retrieval_limit,
        )

        dense_results = self.dense.search(
            query,
            as_of=as_of,
            limit=retrieval_limit,
        )

        return reciprocal_rank_fusion(
            query=query,
            dense_results=dense_results,
            sparse_results=sparse_results,
            limit=limit,
        )


def parse_as_of(value: str) -> date:
    """Parse an ISO date for the command-line interface."""

    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "--as-of must use YYYY-MM-DD format"
        ) from error


def format_result(result: HybridResult) -> str:
    """Render one hybrid result without dumping the full legal text."""

    chunk = result.chunk
    dense_score = (
        f"{result.dense_score:.4f}"
        if result.dense_score is not None
        else "-"
    )
    sparse_score = (
        f"{result.sparse_score:.4f}"
        if result.sparse_score is not None
        else "-"
    )
    effective_to = chunk.get("effective_to") or "open"

    return "\n".join(
        [
            (
                f"{result.rank}. rrf={result.rrf_score:.6f} "
                f"sources={','.join(result.sources)} "
                f"dense={dense_score} sparse={sparse_score}"
            ),
            f"   {chunk['chunk_id']}",
            f"   {chunk.get('breadcrumb', '-')}",
            (
                "   effective="
                f"{chunk.get('effective_from', '?')}..{effective_to}"
            ),
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search the LawAgent corpus using dense + BM25 + RRF"
    )
    parser.add_argument("query", help="Vietnamese legal search query")
    parser.add_argument(
        "--as-of",
        type=parse_as_of,
        default=date.today(),
        help="effective date in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument(
        "--retrieval-limit",
        type=int,
        default=RETRIEVAL_LIMIT,
        help="candidates retrieved from each dense/sparse branch",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = build_parser().parse_args(argv)

    if args.limit < 1:
        raise SystemExit("--limit must be positive")
    if args.retrieval_limit < args.limit:
        raise SystemExit("--retrieval-limit must be at least --limit")

    results = HybridSearcher().search(
        query=args.query,
        as_of=args.as_of,
        limit=args.limit,
        retrieval_limit=args.retrieval_limit,
    )

    print(f"Query: {args.query}")
    print(f"As of: {args.as_of.isoformat()}")

    if not results:
        print("No effective chunks found.")
        return 0

    for result in results:
        print(format_result(result))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
