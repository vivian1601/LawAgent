"""Validate generated legal chunks against manifest article counts."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

import yaml


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.yaml"))
    parser.add_argument("--chunks", type=Path, default=Path("data/processed/chunks.jsonl"))
    parser.add_argument("--report", type=Path, default=Path("data/processed/validation_report.json"))
    parser.add_argument("--spot-check", type=Path, default=Path("data/processed/spot_check.md"))
    args = parser.parse_args()

    manifest = yaml.safe_load(args.manifest.read_text(encoding="utf-8-sig"))
    chunks = [json.loads(line) for line in args.chunks.read_text(encoding="utf-8").splitlines() if line]
    by_doc: dict[str, list[dict]] = defaultdict(list)
    for chunk in chunks:
        by_doc[chunk["doc_id"]].append(chunk)

    errors: list[str] = []
    documents: list[dict] = []
    all_ids = [chunk["chunk_id"] for chunk in chunks]
    duplicate_ids = [key for key, count in Counter(all_ids).items() if count > 1]
    if duplicate_ids:
        errors.append(f"Duplicate chunk_id: {duplicate_ids}")

    for meta in manifest["documents"]:
        doc_chunks = by_doc.get(meta["doc_id"], [])
        labels = list(dict.fromkeys(chunk["dieu_label"] for chunk in doc_chunks))
        expected = int(meta["expected_articles"])
        passed = len(labels) == expected
        if not passed:
            errors.append(f"{meta['doc_id']}: expected {expected} articles, parsed {len(labels)}")
        for chunk in doc_chunks:
            if not chunk["text"].startswith(f"Điều {chunk['dieu_label']}."):
                errors.append(f"{chunk['chunk_id']}: article heading missing")
            if not chunk["breadcrumb"] or not chunk["text_for_embedding"].startswith(chunk["breadcrumb"]):
                errors.append(f"{chunk['chunk_id']}: invalid breadcrumb/embedding text")
        documents.append(
            {
                "doc_id": meta["doc_id"],
                "expected_articles": expected,
                "parsed_articles": len(labels),
                "chunks": len(doc_chunks),
                "first_article": labels[0] if labels else None,
                "last_article": labels[-1] if labels else None,
                "passed": passed,
            }
        )

    target_ids = set(all_ids)
    references = [reference for chunk in chunks for reference in chunk["references"]]
    dangling = sorted(
        {
            (chunk["chunk_id"], reference["target_chunk_id"])
            for chunk in chunks
            for reference in chunk["references"]
            if reference.get("target_chunk_id")
            and reference["target_chunk_id"] not in target_ids
        }
    )
    relation_counts = Counter(reference["relation"] for reference in references)
    unresolved_internal = [
        reference
        for reference in references
        if reference.get("target_doc_id") and not reference.get("resolved")
    ]
    if unresolved_internal:
        errors.append(f"Unresolved internal references: {len(unresolved_internal)}")
    report = {
        "passed": not errors,
        "documents": documents,
        "total_articles": sum(item["parsed_articles"] for item in documents),
        "total_chunks": len(chunks),
        "references": len(references),
        "reference_relations": dict(sorted(relation_counts.items())),
        "resolved_references": sum(bool(reference.get("resolved")) for reference in references),
        "unresolved_cross_document_references": sum(
            bool(reference.get("target_document")) and not reference.get("resolved")
            for reference in references
        ),
        "unresolved_internal_references": len(unresolved_internal),
        "dangling_internal_references": len(dangling),
        "errors": errors,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    random.seed(20260918)
    sample = random.sample(chunks, k=min(10, len(chunks)))
    lines = ["# Spot-check 10 chunks", "", "Mẫu cố định bằng seed `20260918`.", ""]
    for index, chunk in enumerate(sample, start=1):
        preview = chunk["text"][:700].replace("\n", " ")
        reference_labels = [
            f"{reference['relation']} → "
            f"{reference.get('target_chunk_id') or reference.get('target_document') or 'chưa phân giải'}"
            f" (khoản {reference['target_clause']})" if reference.get("target_clause") else
            f"{reference['relation']} → "
            f"{reference.get('target_chunk_id') or reference.get('target_document') or 'chưa phân giải'}"
            for reference in chunk["references"]
        ]
        lines.extend(
            [
                f"## {index}. `{chunk['chunk_id']}`",
                "",
                f"- Breadcrumb: {chunk['breadcrumb']}",
                f"- References: {', '.join(reference_labels) or '(không có)'}",
                "",
                f"> {preview}",
                "",
            ]
        )
    args.spot_check.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
