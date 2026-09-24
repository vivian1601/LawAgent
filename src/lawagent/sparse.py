"""Sparse legal retrieval using BM25."""

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHUNKS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks.jsonl"

TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
ARTICLE_RE = re.compile(r"\bđiều\s+(\d+[a-z]?)\b", re.IGNORECASE)


def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(normalize_text(text))


def extract_article_label(query: str) -> str | None:
    match = ARTICLE_RE.search(normalize_text(query))
    return match.group(1) if match else None


def load_chunks() -> list[dict]:
    chunks: list[dict] = []

    with CHUNKS_PATH.open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                chunks.append(json.loads(line))

    return chunks


@dataclass(frozen=True)
class SparseResult:
    rank: int
    score: float
    chunk: dict
    exact_article: bool


class BM25Index:
    def __init__(self, chunks: list[dict]) -> None:
        if not chunks:
            raise ValueError("Cannot build BM25 index from an empty corpus")

        self.chunks = chunks
        corpus = [
            tokenize(chunk["text_for_embedding"])
            for chunk in chunks
        ]
        self.model = BM25Okapi(corpus)

    def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[SparseResult]:
        query_tokens = tokenize(query)

        if not query_tokens:
            return []

        scores = self.model.get_scores(query_tokens)
        article_label = extract_article_label(query)

        candidates = []

        for index, score in enumerate(scores):
            chunk = self.chunks[index]
            exact_article = (
                article_label is not None
                and str(chunk.get("dieu_label", "")).casefold()
                == article_label.casefold()
            )

            candidates.append(
                {
                    "score": float(score),
                    "chunk": chunk,
                    "exact_article": exact_article,
                }
            )

        if article_label is not None:
            # Nếu người dùng nhập "Điều 35", ưu tiên đúng số Điều.
            # Trong các kết quả trùng số Điều, ưu tiên Bộ luật/Luật
            # trước Nghị định, rồi mới dùng điểm BM25.
            candidates.sort(
                key=lambda item: (
                    item["exact_article"],
                    (
                        -int(item["chunk"]["hierarchy_level"])
                        if item["exact_article"]
                        else 0
                    ),
                    item["score"],
                ),
                reverse=True,
            )
        else:
            candidates.sort(
                key=lambda item: item["score"],
                reverse=True,
            )

        results = []

        for rank, candidate in enumerate(
            candidates[:limit],
            start=1,
        ):
            results.append(
                SparseResult(
                    rank=rank,
                    score=candidate["score"],
                    chunk=candidate["chunk"],
                    exact_article=candidate["exact_article"],
                )
            )

        return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search the LawAgent corpus using BM25"
    )
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    index = BM25Index(load_chunks())
    results = index.search(args.query, limit=args.limit)

    for result in results:
        chunk = result.chunk
        marker = "exact-article" if result.exact_article else "bm25"

        print(
            f"{result.rank}. "
            f"[{marker}] "
            f"score={result.score:.4f}"
        )
        print(f"   {chunk['chunk_id']}")
        print(f"   {chunk['breadcrumb']}")


if __name__ == "__main__":
    main()