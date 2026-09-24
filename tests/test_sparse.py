from lawagent.sparse import BM25Index, load_chunks, tokenize


def test_tokenize_vietnamese_text() -> None:
    assert tokenize("Điều 35: Người lao động") == [
        "điều",
        "35",
        "người",
        "lao",
        "động",
    ]


def test_exact_article_search() -> None:
    index = BM25Index(load_chunks())

    results = index.search("Điều 35", limit=5)

    assert results
    assert results[0].exact_article is True
    assert results[0].chunk["dieu_label"] == "35"
    assert results[0].chunk["hierarchy_level"] == 1


def test_probation_period_search() -> None:
    index = BM25Index(load_chunks())

    results = index.search("thời gian thử việc", limit=5)
    chunk_ids = {
        result.chunk["chunk_id"]
        for result in results
    }

    assert any(
        chunk_id.endswith("__dieu_25")
        for chunk_id in chunk_ids
    )