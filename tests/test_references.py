from lawagent.references import expand_reference_context, extract_locator_text


ARTICLE = """Điều 35. Quy tắc
1. Khoản thứ nhất.
2. Nội dung khoản hai.
a) Ngoại lệ điểm a.
b) Ngoại lệ điểm b.
3. Khoản thứ ba.
"""


def test_extract_exact_clause_and_point() -> None:
    assert extract_locator_text(ARTICLE, clause="2", point="a") == "a) Ngoại lệ điểm a."


def test_expand_exception_context() -> None:
    source = {
        "chunk_id": "doc__dieu_1",
        "references": [
            {
                "relation": "exception",
                "target_article": "35",
                "target_clause": "2",
                "target_point": "a",
                "target_chunk_id": "doc__dieu_35",
            }
        ],
    }
    index = {"doc__dieu_35": {"chunk_id": "doc__dieu_35", "text": ARTICLE}}
    expanded = expand_reference_context(source, index)
    assert expanded[0]["relation"] == "exception"
    assert expanded[0]["text"] == "a) Ngoại lệ điểm a."
