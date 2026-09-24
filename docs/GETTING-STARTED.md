<!-- generated-by: gsd-doc-writer -->
# Bắt đầu với LawAgent

Hướng dẫn này giúp bạn tạo corpus, ingest Qdrant và chạy tìm kiếm hybrid dense +
BM25 + RRF có lọc hiệu lực theo thời gian. Ứng dụng hỏi–đáp/agent chưa được hiện thực.

## Điều kiện tiên quyết

- Python `>=3.11` (khai báo trong `pyproject.toml`).
- [uv](https://docs.astral.sh/uv/) để tạo môi trường và cài dependency.
- Git để clone repository.
- Docker Desktop có Docker Compose nếu bạn muốn chạy Qdrant cục bộ hoặc ingest embedding.

BM25 chạy cục bộ từ `data/processed/chunks.jsonl`; không cần Docker hay khóa OpenAI.

## Cài đặt

1. Clone repository và chuyển vào thư mục dự án:

   ```powershell
   git clone https://github.com/vivian1601/LawAgent.git
   cd LawAgent
   ```

2. Cài dependency ứng dụng và dependency phát triển:

   ```powershell
   uv sync --extra dev
   ```

3. Tạo tệp cấu hình cục bộ từ mẫu:

   ```powershell
   Copy-Item .env.example .env
   ```

   Không dán hoặc chia sẻ khóa OpenAI trong terminal, tài liệu, commit hay ảnh chụp màn hình. Tệp `.env` đã nằm trong `.gitignore`. Điền `OPENAI_API_KEY` để ingest hoặc chạy tìm kiếm hybrid/baseline.

4. Kiểm tra corpus và BM25:

   ```powershell
   uv run python -m lawagent.sparse "Điều 35"
   ```

   Kết quả in các chunk có điểm BM25; truy vấn số Điều ưu tiên kết quả khớp chính xác nhãn Điều.

## Lần chạy đầu không dùng dịch vụ ngoài

Corpus đã có tại `data/processed/chunks.jsonl`. Để tạo lại từ dữ liệu thô và kiểm tra kết quả, chạy:

```powershell
uv run lawagent-parse
uv run python scripts/validate_parser.py
uv run pytest -q -p no:cacheprovider
uv run python -m lawagent.sparse "thời gian thử việc" --limit 5
```

Lệnh cuối là smoke test cho sparse retrieval. Nó đọc JSONL cục bộ và không tạo vector, không gọi OpenAI, cũng không chạy dense retrieval.

## Qdrant cục bộ

Cần Docker Desktop đang chạy. Khởi động Qdrant và xác nhận container:

```powershell
docker compose up -d qdrant
docker compose ps
```

Compose chỉ bind Qdrant vào `127.0.0.1` tại cổng 6333 và 6334. Khởi tạo collection cùng các payload index:

```powershell
uv run python -m lawagent.index
```

Mặc định collection là `lexagent`, dùng cosine distance với vector 1024 chiều. Lệnh có thể chạy lại: nó chỉ tạo collection hoặc index còn thiếu. Qdrant và collection là trạng thái cục bộ bên ngoài repository; lệnh trên mới tạo chúng trên máy của bạn.

## Tạo embedding và ingest (có chi phí)

Chỉ thực hiện bước này khi bạn muốn gửi corpus tới OpenAI Embeddings API. Mở `.env`, điền khóa của riêng bạn cho `OPENAI_API_KEY`, giữ kín tệp đó, rồi bảo đảm Qdrant đang chạy:

```powershell
docker compose up -d qdrant
uv run python -m lawagent.ingest
```

Ingest đọc `text_for_embedding` từ mỗi chunk, gọi model `text-embedding-3-large` với 1024 chiều theo mặc định, rồi upsert các điểm còn thiếu vào Qdrant theo lô. API embeddings có thể phát sinh chi phí theo tài khoản OpenAI của bạn.

Sau khi ingest, chạy tìm kiếm hybrid tại một ngày áp dụng:

```powershell
uv run lawagent-search "thời gian thử việc" --as-of 2026-09-22
uv run lawagent-search "Điều 35" --as-of 2026-09-22
```

CLI mặc định in top-5, lấy 10 ứng viên từ mỗi nhánh và hiển thị điểm RRF, nguồn
dense/sparse, breadcrumb cùng khoảng hiệu lực. Dùng `--limit` và
`--retrieval-limit` để đổi các giới hạn; retrieval limit phải không nhỏ hơn limit.

Chạy baseline hồi quy 10 truy vấn và lưu top-5:

```powershell
uv run lawagent-baseline
```

Snapshot hiện tại nằm tại `data/processed/retrieval_baseline.json` và đạt 10/10
top-1. Lệnh tìm kiếm và baseline đều gọi OpenAI Embeddings API.

## Sự cố thiết lập thường gặp

### `uv` hoặc Python không đúng phiên bản

Nếu `uv sync` không tìm được Python phù hợp, cài Python 3.11 hoặc mới hơn rồi kiểm tra:

```powershell
python --version
uv --version
```

Sau đó chạy lại `uv sync --extra dev`.

### Docker/Qdrant không khởi động được

Mở Docker Desktop và chờ Docker engine sẵn sàng, rồi chạy lại:

```powershell
docker compose up -d qdrant
docker compose ps
```

Nếu cổng 6333 đang được tiến trình khác dùng, dừng tiến trình đó hoặc thay đổi đồng thời ánh xạ cổng trong `docker-compose.yml` và `QDRANT_URL` trong `.env`.

### Ingest hoặc search báo lỗi xác thực OpenAI

`lawagent.ingest`, `lawagent-search` và `lawagent-baseline` cần khóa OpenAI. Kiểm tra `.env` có `OPENAI_API_KEY` không rỗng, không có dấu ngoặc hoặc khoảng trắng thừa, và không commit tệp này. Bạn vẫn có thể dùng `python -m lawagent.sparse` mà không cần dịch vụ ngoài.

### Lỗi kích thước vector sau khi đổi cấu hình

`EMBEDDING_DIMENSIONS` phải là số nguyên và phải khớp vector của model. Collection đã tồn tại không được mã tự thay đổi cấu hình vector. Khi đổi model hoặc số chiều, dùng một `QDRANT_COLLECTION` mới rồi chạy lại khởi tạo và ingest.

## Bước tiếp theo

- Xem [DEVELOPMENT.md](DEVELOPMENT.md) để biết lệnh phát triển và quy ước mã nguồn.
- Xem [TESTING.md](TESTING.md) để chạy và viết kiểm thử.
- Xem [CONFIGURATION.md](CONFIGURATION.md) để biết toàn bộ biến môi trường và cách bảo vệ bí mật.
- Xem [ARCHITECTURE.md](ARCHITECTURE.md) để phân biệt rõ các thành phần đã có và thiết kế retrieval/agent còn dự kiến.
