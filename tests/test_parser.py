from lawagent.parser import _extract_references, parse_articles


def test_parse_hierarchy_and_article_suffix() -> None:
    text = """Chương I
QUY ĐỊNH CHUNG
Mục 1
HỢP ĐỒNG
Điều 1. Phạm vi
Nội dung Điều 35 không phải là tiêu đề.
Điều 2. Quy tắc
1. Khoản một.
Điều 2a. Quy tắc bổ sung
Nội dung bổ sung.
Điều 3. Hiệu lực
Kết thúc.
"""
    articles = parse_articles(text, expected_articles=4)
    assert [article.label for article in articles] == ["1", "2", "2a", "3"]
    assert articles[0].chuong == "I"
    assert articles[0].chuong_title == "QUY ĐỊNH CHUNG"
    assert articles[0].muc == "1"


def test_reference_extraction_is_deduplicated_and_excludes_self() -> None:
    refs = _extract_references(
        "Theo khoản 2 Điều 35 và Điều 35; không tính Điều 24 của văn bản này.",
        "45/2019/QH14",
        "24",
    )
    assert len(refs) == 1
    assert refs[0].target_chunk_id == "45-2019-QH14__dieu_35"
    assert refs[0].relation == "applies"


def test_reference_extraction_keeps_cross_document_link_unresolved() -> None:
    refs = _extract_references(
        "Áp dụng khoản 1 Điều 2 của Bộ luật Lao động và Điều 3 Nghị định này.",
        "145/2020/NĐ-CP",
        "1",
        {"1", "2", "3"},
    )
    assert len(refs) == 2
    assert refs[0].target_document == "Bộ luật Lao động"
    assert refs[0].target_chunk_id is None
    assert refs[0].resolved is False
    assert refs[1].target_chunk_id == "145-2020-ND-CP__dieu_3"


def test_exception_reference_keeps_clause_and_point() -> None:
    refs = _extract_references(
        "Áp dụng, trừ trường hợp quy định tại điểm a khoản 2 Điều 35 Nghị định này.",
        "145/2020/NĐ-CP",
        "1",
        {"1", "35"},
    )
    assert len(refs) == 1
    assert refs[0].relation == "exception"
    assert refs[0].target_article == "35"
    assert refs[0].target_clause == "2"
    assert refs[0].target_point == "a"
    assert refs[0].target_chunk_id == "145-2020-ND-CP__dieu_35"
