"""Parse Vietnamese legal documents into article-level JSONL chunks.

The parser deliberately follows legal structure (Chương -> Mục -> Điều) rather
than splitting by arbitrary character windows. It accepts clean UTF-8 text and
DOCX files from the official Công báo.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET

import yaml


CHUONG_RE = re.compile(r"^Chương\s+([IVXLCDM]+|\d+)\s*\.?\s*(.*)$", re.IGNORECASE)
MUC_RE = re.compile(r"^Mục\s+(\d+[A-Za-zĐđ]?)\s*\.?\s*(.*)$", re.IGNORECASE)
DIEU_RE = re.compile(r"^Điều\s+(\d+)([A-Za-zĐđ]?)\s*\.\s*(.*)$", re.IGNORECASE)
CLAUSE_RE = re.compile(r"^\d+\.\s+")
POINT_RE = re.compile(r"^[a-zđ]\)\s+", re.IGNORECASE)
REFERENCE_RE = re.compile(
    r"(?:(?:điểm\s+([a-zđ])\s+)?(?:khoản\s+(\d+)\s+)?)?Điều\s+(\d+)([a-zđ]?)",
    re.IGNORECASE,
)
DOCUMENT_BEFORE_RE = re.compile(
    r"((?:Bộ luật|Luật|Nghị định|Thông tư)(?:\s+số)?\s+.{1,160}?)"
    r"(?=\s+(?:tại|theo)\s+(?:điểm|khoản|Điều)|[,.;:\n]|$)",
    re.IGNORECASE,
)
DOCUMENT_SCOPE_RE = re.compile(
    r"(?:các\s+điều(?:,\s*khoản)?\s+sau\s+đây\s+của)\s+"
    r"((?:Bộ luật|Luật|Nghị định|Thông tư).{1,120}?):",
    re.IGNORECASE,
)
DOCUMENT_AFTER_GROUP_RE = re.compile(
    r"\bcủa\s+((?:Bộ luật|Luật|Nghị định|Thông tư)(?:\s+số)?\s+[^,.;:\n]{1,180})",
    re.IGNORECASE,
)

DROP_LINE_RES = (
    re.compile(r"^Người ký:", re.IGNORECASE),
    re.compile(r"^Email:", re.IGNORECASE),
    re.compile(r"^Cơ quan:", re.IGNORECASE),
    re.compile(r"^Thời gian ký:", re.IGNORECASE),
    re.compile(r"^CÔNG BÁO/Số .*/Ngày", re.IGNORECASE),
    re.compile(r"^\d+\s+CÔNG BÁO/Số", re.IGNORECASE),
    re.compile(r"^CÔNG BÁO/Số .*\s+\d+$", re.IGNORECASE),
    re.compile(r"^\d+$"),
)


@dataclass(slots=True)
class LegalReference:
    relation: str
    target_doc_id: str | None
    target_document: str | None
    target_article: str
    target_clause: str | None
    target_point: str | None
    target_chunk_id: str | None
    resolved: bool
    raw_text: str


@dataclass(slots=True)
class LegalChunk:
    chunk_id: str
    doc_id: str
    doc_title: str
    doc_type: str
    hierarchy_level: int
    chuong: str | None
    chuong_title: str | None
    muc: str | None
    muc_title: str | None
    dieu_number: int
    dieu_label: str
    dieu_title: str
    breadcrumb: str
    effective_from: str
    effective_to: str | None
    status: str
    references: list[LegalReference]
    text: str
    text_for_embedding: str
    source_url: str
    source_file: str


@dataclass(slots=True)
class _Article:
    number: int
    suffix: str
    title: str
    chuong: str | None
    chuong_title: str | None
    muc: str | None
    muc_title: str | None
    lines: list[str]

    @property
    def label(self) -> str:
        return f"{self.number}{self.suffix.lower()}"


def _docx_text(path: Path) -> str:
    """Extract paragraphs and tables from a DOCX without a heavyweight dependency."""
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    body = root.find("w:body", ns)
    if body is None:
        return ""

    def paragraph_text(node: ET.Element) -> str:
        parts: list[str] = []
        for item in node.iter():
            local = item.tag.rsplit("}", 1)[-1]
            if local == "t" and item.text:
                parts.append(item.text)
            elif local == "tab":
                parts.append("\t")
            elif local in {"br", "cr"}:
                parts.append("\n")
        return "".join(parts).strip()

    lines: list[str] = []
    for child in body:
        local = child.tag.rsplit("}", 1)[-1]
        if local == "p":
            lines.append(paragraph_text(child))
        elif local == "tbl":
            for row in child.findall("w:tr", ns):
                cells = [paragraph_text(cell) for cell in row.findall("w:tc", ns)]
                lines.append(" | ".join(cell for cell in cells if cell))
    return "\n".join(lines)


def read_source(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        return _docx_text(path)
    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8-sig")
    raise ValueError(f"Unsupported input format: {path.suffix} ({path})")


def _clean_line(line: str) -> str:
    line = unicodedata.normalize("NFC", line.replace("\u00a0", " "))
    line = re.sub(r"[ \t]+", " ", line).strip()
    if any(pattern.search(line) for pattern in DROP_LINE_RES):
        return ""
    return line


def _heading_title(lines: list[str], index: int, inline: str) -> tuple[str | None, int]:
    parts = [inline.strip()] if inline.strip() else []
    consumed = index
    cursor = index + 1
    while cursor < len(lines):
        candidate = _clean_line(lines[cursor])
        if not candidate:
            if parts:
                break
            cursor += 1
            continue
        if DIEU_RE.match(candidate) or CHUONG_RE.match(candidate) or MUC_RE.match(candidate):
            break
        if not _looks_like_heading_title(candidate):
            break
        parts.append(candidate)
        consumed = cursor
        cursor += 1
    return (" ".join(parts) or None), consumed


def _looks_like_heading_title(value: str | None) -> bool:
    if not value:
        return False
    letters = "".join(char for char in value if char.isalpha())
    return len(letters) >= 3 and letters == letters.upper()


def _is_next_article(current: _Article | None, number: int, suffix: str) -> bool:
    suffix = suffix.lower()
    if current is None:
        return number == 1 and not suffix
    if number == current.number and suffix and not current.suffix:
        return True
    return number == current.number + 1 and not suffix


def parse_articles(text: str, expected_articles: int | None = None) -> list[_Article]:
    """Return the first monotonically numbered article sequence in a document."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    articles: list[_Article] = []
    current: _Article | None = None
    chuong = chuong_title = muc = muc_title = None
    index = 0

    while index < len(lines):
        line = _clean_line(lines[index])
        chapter_match = CHUONG_RE.match(line)
        section_match = MUC_RE.match(line)
        article_match = DIEU_RE.match(line)

        if chapter_match:
            candidate_title, consumed = _heading_title(lines, index, chapter_match.group(2))
            if _looks_like_heading_title(candidate_title):
                chuong = chapter_match.group(1).upper()
                chuong_title = candidate_title
                muc = muc_title = None
                index = consumed + 1
                continue
        if section_match:
            candidate_title, consumed = _heading_title(lines, index, section_match.group(2))
            if _looks_like_heading_title(candidate_title):
                muc = section_match.group(1)
                muc_title = candidate_title
                index = consumed + 1
                continue
        if article_match:
            number = int(article_match.group(1))
            suffix = article_match.group(2).lower()
            if _is_next_article(current, number, suffix):
                if current is not None:
                    articles.append(current)
                    if expected_articles and len(articles) >= expected_articles:
                        break
                current = _Article(
                    number=number,
                    suffix=suffix,
                    title=article_match.group(3).strip(),
                    chuong=chuong,
                    chuong_title=chuong_title,
                    muc=muc,
                    muc_title=muc_title,
                    lines=[],
                )
                index += 1
                continue
        if current is not None:
            current.lines.append(line)
        index += 1

    if current is not None and (not expected_articles or len(articles) < expected_articles):
        articles.append(current)
    return articles


def _normalise_body(lines: Iterable[str]) -> str:
    paragraphs: list[str] = []
    current = ""
    for raw in lines:
        line = _clean_line(raw)
        if not line:
            if current:
                paragraphs.append(current)
                current = ""
            continue
        starts_structure = bool(CLAUSE_RE.match(line) or POINT_RE.match(line))
        if starts_structure and current:
            paragraphs.append(current)
            current = line
        elif not current:
            current = line
        else:
            current += " " + line
    if current:
        paragraphs.append(current)
    return "\n".join(paragraphs).strip()


def _slug_doc_id(doc_id: str) -> str:
    doc_id = doc_id.replace("Đ", "D").replace("đ", "d")
    slug = unicodedata.normalize("NFKD", doc_id).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9]+", "-", slug).strip("-")


def _extract_references(
    text: str, doc_id: str, self_label: str, valid_labels: set[str] | None = None
) -> list[LegalReference]:
    prefix = _slug_doc_id(doc_id)
    refs: list[LegalReference] = []
    seen: set[tuple[str, str | None, str | None, str, str | None, str | None]] = set()
    scope_match = DOCUMENT_SCOPE_RE.search(text)
    scoped_document = scope_match.group(1).strip() if scope_match else None
    for match in REFERENCE_RE.finditer(text):
        label = f"{match.group(3)}{match.group(4).lower()}"
        clause = match.group(2)
        point = match.group(1).lower() if match.group(1) else None
        before = text[max(0, match.start() - 300) : match.start()]
        tail = text[match.end() : match.end() + 100]

        if re.search(r"(?:trừ|ngoại trừ)(?:\s+trường hợp)?(?:\s+quy định)?(?:\s+tại)?\s*$", before, re.I):
            relation = "exception"
        elif re.search(r"không\s+áp\s+dụng(?:\s+đối\s+với)?(?:\s+trường hợp)?(?:\s+quy định)?(?:\s+tại)?\s*$", before, re.I):
            relation = "exclusion"
        elif re.search(r"(?:bãi bỏ|hủy bỏ)(?:\s+quy định)?(?:\s+tại)?\s*$", before, re.I):
            relation = "repeal"
        elif re.search(r"sửa đổi(?:,\s*bổ sung)?(?:\s+quy định)?(?:\s+tại)?\s*$", before, re.I):
            relation = "amendment"
        else:
            relation = "applies"

        internal_marker = re.match(
            r"^\s+(?:của\s+)?(?:Bộ luật|Luật|Nghị định|Thông tư|văn bản)\s+này\b",
            tail,
            re.IGNORECASE,
        )
        external_match = None if internal_marker else re.match(
            r"^\s+(?:của\s+)?((?:Bộ luật|Luật|Nghị định|Thông tư)"
            r"(?:\s+số)?\s+.{1,100}?)"
            r"(?=\s+(?:và|hoặc)\s+(?:điểm|khoản|Điều)|[,.;:\n]|$)",
            tail,
            re.IGNORECASE,
        )
        paragraph_end = text.find("\n", match.end())
        if paragraph_end == -1:
            paragraph_end = len(text)
        group_document_match = DOCUMENT_AFTER_GROUP_RE.search(text[match.end() : paragraph_end])
        following_document = (
            group_document_match.group(1).strip() if group_document_match else None
        )
        before_documents = list(DOCUMENT_BEFORE_RE.finditer(before))
        preceding_document = before_documents[-1].group(1).strip() if before_documents else None
        target_document = None if internal_marker else (
            external_match.group(1).strip()
            if external_match
            else following_document or preceding_document or scoped_document
        )
        if target_document and re.fullmatch(
            r"(?:Bộ luật|Luật|Nghị định|Thông tư|văn bản)\s+này",
            target_document,
            re.IGNORECASE,
        ):
            target_document = None
        is_internal = target_document is None
        is_resolved = bool(is_internal and (valid_labels is None or label in valid_labels))
        target_chunk_id = f"{prefix}__dieu_{label}" if is_resolved else None
        target_doc_id = doc_id if is_internal else None

        if is_internal and label == self_label:
            continue
        key = (relation, target_doc_id, target_document, label, clause, point)
        if key in seen:
            continue
        same_target = [
            reference
            for reference in refs
            if reference.relation == relation
            and reference.target_doc_id == target_doc_id
            and reference.target_document == target_document
            and reference.target_article == label
        ]
        if same_target and clause is None and point is None:
            # A general repeat adds nothing after a more precise Khoản/Điểm link.
            continue
        if clause is not None:
            refs = [
                reference
                for reference in refs
                if not (
                    reference.relation == relation
                    and reference.target_doc_id == target_doc_id
                    and reference.target_document == target_document
                    and reference.target_article == label
                    and reference.target_clause is None
                    and reference.target_point is None
                )
            ]
        seen.add(key)
        raw_end = match.end() + (external_match.end() if external_match else 0)
        refs.append(
            LegalReference(
                relation=relation,
                target_doc_id=target_doc_id,
                target_document=target_document,
                target_article=label,
                target_clause=clause,
                target_point=point,
                target_chunk_id=target_chunk_id,
                resolved=is_resolved,
                raw_text=text[match.start() : raw_end].strip(),
            )
        )
    return refs


def _split_long_article(text: str, max_chars: int = 8_000) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    clauses = re.split(r"(?m)(?=^\d+\.\s+)", text)
    if len(clauses) == 1:
        return [text[index : index + max_chars] for index in range(0, len(text), max_chars)]
    parts: list[str] = []
    current = ""
    for clause in clauses:
        if current and len(current) + len(clause) + 1 > max_chars:
            parts.append(current.strip())
            current = clause
        else:
            current = f"{current}\n{clause}" if current else clause
    if current.strip():
        parts.append(current.strip())
    return parts


def parse_document(meta: dict[str, Any], source_path: Path) -> list[LegalChunk]:
    articles = parse_articles(read_source(source_path), meta.get("expected_articles"))
    valid_labels = {article.label for article in articles}
    chunks: list[LegalChunk] = []
    doc_slug = _slug_doc_id(meta["doc_id"])
    hierarchy_level = {"bo_luat": 1, "luat": 1, "nghi_dinh": 2, "thong_tu": 3}[meta["doc_type"]]

    for article in articles:
        body = _normalise_body(article.lines)
        heading = f"Điều {article.label}." + (f" {article.title}" if article.title else "")
        full_text = f"{heading}\n{body}".strip()
        breadcrumb_parts = [meta["title"]]
        if article.chuong:
            chapter = f"Chương {article.chuong}"
            if article.chuong_title:
                chapter += f". {article.chuong_title}"
            breadcrumb_parts.append(chapter)
        if article.muc:
            section = f"Mục {article.muc}"
            if article.muc_title:
                section += f". {article.muc_title}"
            breadcrumb_parts.append(section)
        breadcrumb_parts.append(heading)
        breadcrumb = " > ".join(breadcrumb_parts)
        references = _extract_references(full_text, meta["doc_id"], article.label, valid_labels)
        parts = _split_long_article(full_text)

        for part_index, part in enumerate(parts, start=1):
            base_id = f"{doc_slug}__dieu_{article.label}"
            chunk_id = base_id if part_index == 1 else f"{base_id}__part_{part_index}"
            part_text = part if part_index == 1 else f"{heading}\n{part}"
            chunks.append(
                LegalChunk(
                    chunk_id=chunk_id,
                    doc_id=meta["doc_id"],
                    doc_title=meta["title"],
                    doc_type=meta["doc_type"],
                    hierarchy_level=hierarchy_level,
                    chuong=article.chuong,
                    chuong_title=article.chuong_title,
                    muc=article.muc,
                    muc_title=article.muc_title,
                    dieu_number=article.number,
                    dieu_label=article.label,
                    dieu_title=article.title,
                    breadcrumb=breadcrumb,
                    effective_from=meta["effective_from"],
                    effective_to=meta.get("effective_to"),
                    status=meta["status"],
                    references=references,
                    text=part_text,
                    text_for_embedding=f"{breadcrumb}\n\n{part_text}",
                    source_url=meta["source_url"],
                    source_file=str(source_path.as_posix()),
                )
            )
    return chunks


def build_corpus(manifest_path: Path, output_path: Path) -> list[LegalChunk]:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8-sig"))
    data_root = manifest_path.parent
    chunks: list[LegalChunk] = []
    for document in manifest["documents"]:
        source_path = data_root / document["parser_input"]
        if not source_path.exists():
            raise FileNotFoundError(f"Missing parser input for {document['doc_id']}: {source_path}")
        chunks.extend(parse_document(document, source_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for chunk in chunks:
            handle.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("data/manifest.yaml"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/chunks.jsonl"))
    args = parser.parse_args()
    chunks = build_corpus(args.manifest, args.output)
    article_count = len({(chunk.doc_id, chunk.dieu_label) for chunk in chunks})
    print(f"Wrote {len(chunks)} chunks for {article_count} articles to {args.output}")


if __name__ == "__main__":
    main()
