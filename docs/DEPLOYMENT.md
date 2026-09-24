<!-- generated-by: gsd-doc-writer -->
# Chạy runtime và triển khai cục bộ

Repository hiện chỉ định nghĩa runtime cục bộ cho Qdrant. `docker-compose.yml`
không đóng gói hoặc triển khai ứng dụng LawAgent hoàn chỉnh: không có Dockerfile,
web server, API hỏi–đáp hay container cho parser, retrieval hoặc ingest.

## Mục tiêu runtime hiện có

| Thành phần | Cách chạy | Phạm vi |
| --- | --- | --- |
| Qdrant | `docker-compose.yml` | Vector database cục bộ cho index, ingest và dense search. |
| Parser và BM25 | Chạy bằng `uv run` trên máy chủ | Không được Compose container hóa. |
| Ingest embedding | Chạy bằng `uv run` trên máy chủ | Kết nối Qdrant và gọi OpenAI Embeddings API; không được Compose container hóa. |
| Hybrid search/baseline | `lawagent-search`, `lawagent-baseline` trên máy chủ | Kết nối Qdrant, gọi OpenAI Embeddings và lọc hiệu lực theo ngày. |

Compose khai báo duy nhất dịch vụ `qdrant`, dùng image `qdrant/qdrant:latest` và
`restart: unless-stopped`. Cổng `6333` và `6334` chỉ bind vào `127.0.0.1`, nên cấu
hình này phục vụ máy cục bộ chứ không công bố Qdrant ra mạng ngoài.

## Khởi động, kiểm tra và dừng Qdrant

Cần có Docker Compose. Khởi động dịch vụ nền:

```powershell
docker compose up -d qdrant
```

Kiểm tra trạng thái dịch vụ và xem log khi chẩn đoán:

```powershell
docker compose ps qdrant
docker compose logs --tail 100 qdrant
```

Để theo dõi log liên tục, dùng `docker compose logs --follow qdrant` và dừng việc
theo dõi bằng `Ctrl+C`. Lệnh này không dừng container.

Dừng Qdrant cục bộ mà không xóa container hoặc volume:

```powershell
docker compose stop qdrant
```

Khởi động lại bằng lệnh `docker compose up -d qdrant`. Không có hướng dẫn xóa dữ
liệu trong tài liệu này.

## Khởi tạo collection và ingest

Sau khi Qdrant đang chạy, tạo hoặc kiểm tra collection và các payload index:

```powershell
uv run python -m lawagent.index
```

`lawagent.index` dùng URL, tên collection và số chiều vector từ môi trường; thao tác
tạo collection/index có thể chạy lại khi cấu hình không đổi. Theo mặc định, client
kết nối `http://localhost:6333` và dùng collection `lexagent`.

Ingest chạy ngoài Docker Compose, đọc `data/processed/chunks.jsonl`, tạo embedding
theo batch rồi upsert vào Qdrant:

```powershell
uv run python -m lawagent.ingest
```

Lệnh này yêu cầu Qdrant có thể truy cập và thông tin xác thực OpenAI hợp lệ. Không
đưa khóa OpenAI vào lệnh, compose file hoặc log. Xem [CONFIGURATION.md](CONFIGURATION.md)
để cấu hình an toàn các biến môi trường và tránh thay đổi số chiều của collection
đang có.

Sau khi ingest, kiểm tra runtime retrieval:

```powershell
uv run lawagent-search "Điều 35" --as-of 2026-09-22
uv run lawagent-baseline
```

## Dữ liệu bền vững

Compose gắn named volume `qdrant_storage` vào `/qdrant/storage` trong container.
Dữ liệu Qdrant được giữ qua các lần dừng rồi khởi động lại dịch vụ, miễn là volume
vẫn còn. Repository không có cơ chế backup, migration hoặc khôi phục dữ liệu tự động
cho volume này.

## Pipeline triển khai và production

Không có Dockerfile, workflow CI/CD, cấu hình hosting, cấu hình deploy hay script
release trong repository. Vì vậy không có pipeline build/deploy tự động, môi trường
production được định nghĩa sẵn hoặc URL triển khai để ghi nhận ở đây.

Không có HTTP API hay cơ chế xác thực ứng dụng trong mã hiện tại. `docker-compose.yml`
cũng không cấu hình xác thực Qdrant; việc bind cổng vào loopback chỉ giới hạn truy
cập từ mạng ngoài trên máy chạy Compose, không thay thế một thiết kế xác thực cho
một triển khai mạng.

## Phục hồi và giám sát

Không có quy trình rollback tự động, version image được ghim, healthcheck, tích hợp
monitoring hoặc cấu hình cảnh báo. Với lỗi cục bộ, kiểm tra `docker compose ps` và
log Qdrant, sửa cấu hình hoặc môi trường cần thiết, rồi khởi động lại dịch vụ. Đây
chỉ là thao tác phục hồi runtime cục bộ, không phải rollback của một bản triển khai
production.

Ngoài log Docker Compose và thông tin trạng thái/điểm mà `lawagent.index` in ra khi
chạy, repository không tích hợp Sentry, Datadog, OpenTelemetry hay dịch vụ giám sát
khác.
