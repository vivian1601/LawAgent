<!-- generated-by: gsd-doc-writer -->
# Kiểm thử

LawAgent dùng pytest để kiểm thử parser, dẫn chiếu, BM25, dense retrieval, temporal
filter, RRF và CLI hybrid. Cấu hình pytest nằm trong `pyproject.toml`: mã nguồn
được nạp từ `src` và pytest chỉ tìm test trong `tests`.

## Thiết lập

Dự án yêu cầu Python `>=3.11`. Pytest là dependency phát triển với ràng buộc `pytest>=8.3`.

```powershell
uv sync --extra dev
```

Các test cục bộ không cần Docker, Qdrant hay `OPENAI_API_KEY`. Các test sparse dùng corpus đã có tại `data/processed/chunks.jsonl`.

## Chạy kiểm thử

Chạy toàn bộ suite:

```powershell
uv run pytest
```

Dùng lệnh sau nếu bạn không muốn pytest tạo hoặc dùng cache:

```powershell
uv run pytest -q -p no:cacheprovider
```

Chạy một tệp test:

```powershell
uv run pytest tests/test_sparse.py
```

Chạy một test cụ thể:

```powershell
uv run pytest tests/test_sparse.py::test_exact_article_search
```

Các lệnh trên chạy unit test và corpus-backed test hiện có; chúng không khởi tạo Qdrant, không ingest embedding và không gọi OpenAI.

## Phạm vi suite hiện tại

| Tệp | Phạm vi | Loại test |
| --- | --- | --- |
| `tests/test_parser.py` | Cấu trúc Chương/Mục/Điều, nhãn Điều có hậu tố, trích xuất và phân loại dẫn chiếu | Unit |
| `tests/test_references.py` | Trích chính xác Khoản/Điểm và mở rộng ngữ cảnh ngoại lệ | Unit |
| `tests/test_sparse.py` | Token hóa tiếng Việt, ưu tiên khớp số Điều và tìm quy định thử việc | Unit; hai test tìm kiếm đọc corpus JSONL |
| `tests/test_temporal_filter.py` | Khoảng hiệu lực bao gồm hai biên và cấu trúc filter Qdrant | Unit |
| `tests/test_dense.py` | Embedding query, số chiều và ánh xạ kết quả Qdrant | Unit với client giả |
| `tests/test_search.py` | RRF, ưu tiên số Điều/tiêu đề, lọc ngày và định dạng CLI | Unit với dense retriever giả |

`tests/test_sparse.py` gọi `load_chunks()`, nên cần giữ `data/processed/chunks.jsonl` trong repository hoặc tạo lại nó trước khi chạy. Nếu corpus bị thiếu hoặc bạn vừa thay đổi dữ liệu thô, chạy:

```powershell
uv run lawagent-parse
uv run python scripts/validate_parser.py
```

Suite hiện có **24 test**. Các test dense/hybrid không gọi dịch vụ ngoài mà dùng
client giả. Suite chưa kiểm thử tích hợp tạo collection, ingest/OpenAI thật,
pipeline agent, citation verifier hoặc UI.

## Nghiệm thu retrieval thật

Sau khi Qdrant đã ingest và `.env` có khóa OpenAI, chạy:

```powershell
uv run lawagent-search "thời gian thử việc" --as-of 2026-09-22 --limit 1
uv run lawagent-search "Điều 35" --as-of 2026-09-22 --limit 1
uv run lawagent-search "thời gian thử việc" --as-of 2023-01-01 --limit 1
uv run lawagent-baseline
```

Kết quả đã xác minh lần gần nhất lần lượt là Điều 25 bản hợp nhất 2026, Điều 35
bản hợp nhất 2026 và Điều 25 Bộ luật 2019. Baseline đạt 10/10 top-1 và ghi top-5
vào `data/processed/retrieval_baseline.json`. Đây là integration/acceptance check
có gọi OpenAI, không phải một phần của pytest.

## Viết test mới

Tuân theo các quy ước đang dùng:

- Đặt tệp trong `tests/` với tên `test_<chủ_đề>.py`.
- Đặt hàm pytest dạng `test_<hành_vi>()`; suite hiện không dùng class test hay fixture dùng chung.
- Dùng dữ liệu chuỗi/dict nhỏ, độc lập cho unit test parser và references.
- Chỉ dùng corpus thực khi hành vi cần kiểm tra truy xuất từ `chunks.jsonl`. Khi đó, assert theo thuộc tính ổn định như `dieu_label`, `chunk_id` hoặc thứ bậc, thay vì điểm BM25 chính xác.
- Thêm test vào tệp phù hợp với module được thay đổi: parser, references, sparse,
  temporal, dense hoặc hybrid search.

Ví dụ cho hành vi BM25 mới:

```python
def test_search_returns_expected_article() -> None:
    index = BM25Index(load_chunks())

    results = index.search("Điều 35", limit=5)

    assert results[0].chunk["dieu_label"] == "35"
```

## Coverage

Không có ngưỡng coverage được cấu hình. Repository không khai báo công cụ đo
coverage hoặc mục coverage trong `pyproject.toml`. Vì vậy, không có tỷ lệ
lines/branches/functions/statements bắt buộc được pytest kiểm tra.

## CI

Không phát hiện thư mục `.github/workflows/` hay workflow CI trong repository hiện tại. Test chưa được cấu hình để chạy tự động khi push hoặc mở pull request; chạy các lệnh trong tài liệu này trước khi gửi thay đổi.

## Bước tiếp theo

- Xem [DEVELOPMENT.md](DEVELOPMENT.md) để biết lệnh phát triển.
- Xem [GETTING-STARTED.md](GETTING-STARTED.md) để chuẩn bị môi trường cục bộ.
- Xem [ARCHITECTURE.md](ARCHITECTURE.md) để biết giới hạn giữa các thành phần đã hiện thực và phần thiết kế dự kiến.
