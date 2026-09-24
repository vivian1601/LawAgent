"""Generate a reproducible hybrid-retrieval baseline."""

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Sequence

from lawagent.search import HybridSearcher


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "retrieval_baseline.json"


@dataclass(frozen=True)
class BaselineCase:
    query: str
    as_of: date
    expected_top1: str


BASELINE_CASES = (
    BaselineCase(
        "thời gian thử việc",
        date(2026, 9, 22),
        "18-VBHN-VPQH__dieu_25",
    ),
    BaselineCase(
        "Điều 35",
        date(2026, 9, 22),
        "18-VBHN-VPQH__dieu_35",
    ),
    BaselineCase(
        "thời gian thử việc",
        date(2023, 1, 1),
        "45-2019-QH14__dieu_25",
    ),
    BaselineCase(
        "tiền lương thử việc",
        date(2026, 9, 22),
        "18-VBHN-VPQH__dieu_26",
    ),
    BaselineCase(
        "thời giờ làm việc bình thường",
        date(2026, 9, 22),
        "18-VBHN-VPQH__dieu_105",
    ),
    BaselineCase(
        "làm thêm giờ",
        date(2026, 9, 22),
        "18-VBHN-VPQH__dieu_107",
    ),
    BaselineCase(
        "nghỉ hằng năm",
        date(2026, 9, 22),
        "18-VBHN-VPQH__dieu_113",
    ),
    BaselineCase(
        "nguyên tắc xử lý kỷ luật lao động",
        date(2026, 9, 22),
        "18-VBHN-VPQH__dieu_122",
    ),
    BaselineCase(
        "lao động chưa thành niên",
        date(2026, 9, 22),
        "18-VBHN-VPQH__dieu_143",
    ),
    BaselineCase(
        "Điều 90",
        date(2026, 9, 22),
        "18-VBHN-VPQH__dieu_90",
    ),
)


def run_baseline(
    output_path: Path = DEFAULT_OUTPUT,
    limit: int = 5,
) -> tuple[int, int]:
    searcher = HybridSearcher()
    records = []
    passed = 0

    for case in BASELINE_CASES:
        results = searcher.search(
            case.query,
            as_of=case.as_of,
            limit=limit,
        )
        actual_top1 = (
            results[0].chunk["chunk_id"] if results else None
        )
        case_passed = actual_top1 == case.expected_top1
        passed += int(case_passed)

        records.append(
            {
                "query": case.query,
                "as_of": case.as_of.isoformat(),
                "expected_top1": case.expected_top1,
                "actual_top1": actual_top1,
                "passed": case_passed,
                "results": [
                    {
                        "rank": result.rank,
                        "chunk_id": result.chunk["chunk_id"],
                        "breadcrumb": result.chunk.get("breadcrumb"),
                        "rrf_score": result.rrf_score,
                        "sources": list(result.sources),
                        "dense_score": result.dense_score,
                        "sparse_score": result.sparse_score,
                    }
                    for result in results
                ],
            }
        )

        marker = "PASS" if case_passed else "FAIL"
        print(
            f"[{marker}] {case.query!r} @ {case.as_of}: "
            f"{actual_top1}"
        )

    report = {
        "retriever": "dense+bm25+rrf",
        "rrf_k": 60,
        "top_k": limit,
        "summary": {
            "passed": passed,
            "total": len(BASELINE_CASES),
        },
        "cases": records,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Saved baseline: {output_path}")
    return passed, len(BASELINE_CASES)


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Run the 10-query LawAgent retrieval baseline"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args(argv)

    if args.limit < 1:
        raise SystemExit("--limit must be positive")

    passed, total = run_baseline(args.output, args.limit)
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
