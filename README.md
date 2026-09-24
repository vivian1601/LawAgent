<!-- generated-by: gsd-doc-writer -->
# LawAgent

LawAgent là bộ công cụ tra cứu pháp luật lao động Việt Nam dành cho học tập và nghiên cứu, kết hợp truy xuất dense, BM25, hợp nhất Reciprocal Rank Fusion (RRF) và lọc hiệu lực theo thời điểm.

## Trạng thái triển khai

- **Giai đoạn 1 — hoàn thành:** corpus gồm 8 phiên bản văn bản, được chuẩn hóa thành **702 Điều / 724 chunks** với breadcrumb, metadata hiệu lực và dẫn chiếu có cấu trúc.
- **Giai đoạn 2 — hoàn thành:** Qdrant có **724 vectors**; truy xuất dense bằng OpenAI Embeddings và BM25 được hợp nhất bằng RRF (`k=60`); cả hai nhánh đều lọc theo ngày hiệu lực. Hai CLI `lawagent-search` và `lawagent-baseline` đã sẵn sàng.
- **Kiểm chứng hiện tại:** toàn bộ **24** bài kiểm thử pytest đều đạt; baseline 10 truy vấn đạt **10/10** top-1. Báo cáo nằm tại [`data/processed/retrieval_baseline.json`](data/processed/retrieval_baseline.json).
- **Các giai đoạn tiếp theo:** pipeline agent, citation verifier, đánh giá, UI và hoàn thiện tài liệu vẫn theo kế hoạch tại [`docs/ROADMAP.md`](docs/ROADMAP.md).

> Công cụ chỉ hỗ trợ tra cứu/học tập và không thay thế tư vấn pháp lý.

## Cài đặt

Yêu cầu: Python `>=3.11`, [uv](https://docs.astral.sh/uv/), Docker Desktop (để chạy Qdrant), và `OPENAI_API_KEY` hợp lệ để ingest hoặc truy vấn dense.

```powershell
uv sync --extra dev
Copy-Item .env.example .env
```

Điền `OPENAI_API_KEY` của bạn vào `.env`. Các giá trị mặc định cho Qdrant và embedding đã có trong [`.env.example`](.env.example).

## Bắt đầu nhanh

1. Cài dependencies và cấu hình `.env` như phần trên.

2. Khởi động Qdrant cục bộ, rồi tạo collection và payload index:

   ```powershell
   docker compose up -d qdrant
   uv run python -m lawagent.index
   ```

3. Tạo embedding và ingest 724 chunks vào Qdrant:

   ```powershell
   uv run python -m lawagent.ingest
   ```

4. Chạy tìm kiếm hybrid tại một mốc hiệu lực:

   ```powershell
   uv run lawagent-search "thời gian thử việc" --as-of 2026-09-22
   ```

Lệnh in tối đa năm chunks, gồm điểm RRF, nguồn `dense`/`sparse`, breadcrumb và khoảng hiệu lực.

## Sử dụng

### Tìm Điều theo số

```powershell
uv run lawagent-search "Điều 35" --as-of 2026-09-22
```

Kết quả ưu tiên chunk trùng số Điều, sau đó xếp hạng theo tiêu đề, loại văn bản và RRF.

### So sánh quy định ở các thời điểm

```powershell
uv run lawagent-search "thời gian thử việc" --as-of 2023-01-01
uv run lawagent-search "thời gian thử việc" --as-of 2026-09-22
```

Mỗi truy vấn chỉ xem các chunks có hiệu lực tại ngày được chỉ định.

### Chạy baseline truy xuất

```powershell
uv run lawagent-baseline
```

Lệnh chạy 10 truy vấn trên Qdrant đã ingest, ghi kết quả top-5 vào `data/processed/retrieval_baseline.json`, và trả mã lỗi nếu bất kỳ top-1 kỳ vọng nào không khớp.

### Chạy pipeline corpus và kiểm thử

```powershell
uv run lawagent-parse
uv run python scripts/validate_parser.py
uv run pytest -q -p no:cacheprovider
```

Đầu ra corpus chính là `data/processed/chunks.jsonl`; validation report và mẫu kiểm tra nằm trong `data/processed/`.

## Tài liệu

- [Tổng quan tài liệu](docs/README.md)
- [Kiến trúc](docs/ARCHITECTURE.md)
- [Cấu hình](docs/CONFIGURATION.md)
- [Hướng dẫn bắt đầu](docs/GETTING-STARTED.md)
- [Kiểm thử](docs/TESTING.md)
- [Lộ trình](docs/ROADMAP.md)
