<!-- generated-by: gsd-doc-writer -->
# Cấu hình

LawAgent đọc cấu hình môi trường khi nạp `lawagent.config`. Tệp `.env` (nếu có) được nạp bằng `python-dotenv`; các biến này điều khiển kết nối Qdrant và quá trình tạo embedding OpenAI cho ingest, tìm kiếm hybrid và baseline.

## Biến môi trường

Tạo tệp cấu hình cục bộ từ mẫu:

```powershell
Copy-Item .env.example .env
```

| Biến | Bắt buộc | Mặc định | Mô tả |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | Có khi chạy ingest, `lawagent-search` hoặc `lawagent-baseline` | Không có | Khóa mà OpenAI client dùng để gọi API tạo embedding. Mã không tự kiểm tra biến này khi nạp cấu hình, nhưng các lệnh này đều khởi tạo OpenAI client để tạo embedding. |
| `QDRANT_URL` | Không | `http://localhost:6333` | URL của máy chủ Qdrant được cả bước tạo collection và ingest sử dụng. |
| `QDRANT_COLLECTION` | Không | `lexagent` | Tên collection Qdrant lưu vector và payload của các đoạn văn bản. |
| `OPENAI_EMBEDDING_MODEL` | Không | `text-embedding-3-large` | Model được truyền vào yêu cầu tạo embedding; tên model cũng được lưu trong payload của từng điểm. |
| `EMBEDDING_DIMENSIONS` | Không | `1024` | Số nguyên là kích thước vector: dùng khi tạo collection và khi yêu cầu OpenAI trả embedding. |

Ví dụ `.env` tối thiểu cho môi trường phát triển cục bộ:

```dotenv
OPENAI_API_KEY=<openai-api-key-cua-ban>
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=lexagent
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIMENSIONS=1024
```

## Định dạng và nguồn cấu hình

Tệp cấu hình duy nhất được mã ứng dụng nạp là `.env` theo định dạng `KEY=value`. Các biến môi trường đã được thiết lập cho tiến trình cũng có thể được dùng thay cho tệp này. Không có tệp `.env.development`, `.env.test` hay `.env.production` trong dự án, và `docker-compose.yml` không truyền các biến cấu hình của LawAgent vào container.

Các hằng số được xác định trong [`src/lawagent/config.py`](../src/lawagent/config.py):

```python
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "lexagent")
OPENAI_EMBEDDING_MODEL = os.getenv(
    "OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"
)
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))
```

## Cài đặt bắt buộc và giá trị mặc định

`OPENAI_API_KEY` cần cho ingest và các lệnh hybrid retrieval, vì [`src/lawagent/ingest.py`](../src/lawagent/ingest.py) và [`src/lawagent/dense.py`](../src/lawagent/dense.py) đều khởi tạo `OpenAI()` và gọi API embeddings. `lawagent-search` và `lawagent-baseline` dùng `DenseRetriever`, nên cũng cần khóa này cùng với một Qdrant có thể truy cập qua `QDRANT_URL`. Bước tạo hoặc kiểm tra collection trong [`src/lawagent/index.py`](../src/lawagent/index.py) không dùng OpenAI.

Các biến Qdrant và embedding có giá trị mặc định như bảng trên. `EMBEDDING_DIMENSIONS` phải là một số nguyên hợp lệ; giá trị không phải số sẽ khiến việc nạp `lawagent.config` thất bại. Khi đổi model hoặc số chiều, hãy giữ `OPENAI_EMBEDDING_MODEL` và `EMBEDDING_DIMENSIONS` tương thích với nhau. Đặc biệt, mã chỉ tạo collection khi nó chưa tồn tại; collection có sẵn không được thay đổi cấu hình vector. Dùng một `QDRANT_COLLECTION` mới khi cần thay đổi số chiều của vector.

## Qdrant cục bộ với Docker

Khởi động Qdrant cục bộ bằng:

```powershell
docker compose up -d qdrant
```

`docker-compose.yml` ánh xạ hai cổng Qdrant chỉ tới loopback của máy chủ:

| Host | Container | Ý nghĩa trong dự án |
| --- | --- | --- |
| `127.0.0.1:6333` | `6333` | Cổng mặc định phù hợp với `QDRANT_URL=http://localhost:6333`. |
| `127.0.0.1:6334` | `6334` | Cổng được Compose công khai trên loopback. |

Dữ liệu Qdrant được giữ trong named volume `qdrant_storage`, gắn vào `/qdrant/storage` của container. Vì các cổng dùng địa chỉ `127.0.0.1`, chúng không được bind tới giao diện mạng ngoài của máy chủ.

## Tùy chọn CLI cho tìm kiếm và baseline

Sau khi `.env` có `OPENAI_API_KEY` và Qdrant đã chứa corpus, chạy tìm kiếm hybrid với một ngày hiệu lực xác định:

```powershell
uv run lawagent-search "thời gian thử việc" --as-of 2026-09-22 --limit 5 --retrieval-limit 10
```

`lawagent-search` nhận các tùy chọn sau:

| Tùy chọn | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `--as-of YYYY-MM-DD` | Ngày hiện tại | Ngày hiệu lực dùng để lọc cả chunks BM25 và điểm Qdrant. Giá trị phải theo định dạng ISO `YYYY-MM-DD`. |
| `--limit N` | `5` | Số kết quả cuối cùng sau Reciprocal Rank Fusion. `N` phải lớn hơn `0`. |
| `--retrieval-limit N` | `10` | Số ứng viên được lấy từ mỗi nhánh dense và BM25 trước khi fusion. `N` phải lớn hơn hoặc bằng `--limit`. |

Ngày `--as-of` quyết định phiên bản văn bản pháp luật có hiệu lực trong kết quả; nếu không truyền, lệnh dùng ngày hệ thống. `--retrieval-limit` chỉ thay đổi số ứng viên đầu vào cho fusion, không phải số dòng được in cuối cùng.

Chạy baseline có thể tái lập bằng cùng cấu hình Qdrant và OpenAI:

```powershell
uv run lawagent-baseline --limit 5 --output data/processed/retrieval_baseline.json
```

`lawagent-baseline` chạy 10 truy vấn/ngày hiệu lực cố định. `--limit` phải lớn hơn `0` và đặt số kết quả được ghi cho mỗi ca; `--output` chọn tệp JSON báo cáo. Nếu bỏ `--output`, báo cáo được ghi vào `data/processed/retrieval_baseline.json`. Baseline dùng giá trị `--retrieval-limit` mặc định của `HybridSearcher`; lệnh này không nhận `--as-of` hay `--retrieval-limit` vì các ca baseline đã xác định ngày hiệu lực riêng.

## Ghi đè theo môi trường

Dự án không định nghĩa bộ tệp cấu hình riêng cho development, test hoặc production. Hãy chọn một trong hai cách dưới đây cho từng môi trường:

1. Đặt các giá trị trong `.env` cục bộ theo mẫu `.env.example`.
2. Cung cấp cùng các tên biến môi trường cho tiến trình chạy LawAgent, ví dụ từ secret store hoặc cấu hình runtime của môi trường triển khai.

Với môi trường không dùng Docker cục bộ, đặt `QDRANT_URL` thành URL của dịch vụ Qdrant mà tiến trình có thể truy cập. Không thay đổi `QDRANT_COLLECTION` hoặc số chiều vector của dữ liệu đang dùng mà không có kế hoạch tách hoặc tạo lại collection.

## Bảo vệ bí mật

- Không đưa giá trị thực của `OPENAI_API_KEY` vào tài liệu, mã nguồn, dữ liệu mẫu hoặc nhật ký lệnh.
- Tệp `.env` đã được liệt kê trong `.gitignore`; chỉ theo dõi `.env.example` với giá trị trống hoặc giá trị không nhạy cảm.
- Cấp khóa qua secret manager hay biến môi trường của runtime trong môi trường triển khai; không ghi khóa vào `docker-compose.yml` hiện tại.
- Nếu một khóa bị lộ, thu hồi hoặc xoay vòng khóa đó tại nhà cung cấp trước khi tiếp tục ingest.
