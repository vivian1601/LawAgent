<!-- generated-by: gsd-doc-writer -->
# ARCHITECTURE — Thiết kế hệ thống

## Tổng quan hệ thống

LawAgent là bộ công cụ truy xuất corpus pháp luật lao động Việt Nam theo Điều và theo thời điểm áp dụng. Hệ thống có kiến trúc pipeline: văn bản và metadata được parser chuẩn hóa thành `LegalChunk`; mỗi chunk được lập chỉ mục cho hai nhánh dense và BM25; `HybridSearcher` lọc theo ngày, hợp nhất kết quả bằng Reciprocal Rank Fusion (RRF), rồi trả về các chunk kèm điểm và nguồn xếp hạng. Corpus hiện có 702 Điều trong 724 chunks; báo cáo baseline đã lưu ghi nhận 10/10 truy vấn đạt kết quả top-1 kỳ vọng.

## Thành phần và quan hệ

```text
data/raw/ + data/manifest.yaml
              |
              v
        lawagent.parser
              |
              v
 data/processed/chunks.jsonl (724 chunks)
       |                              |
       v                              v
lawagent.sparse                 lawagent.ingest
  BM25Index                           |
       |                              v
       |                    OpenAI Embeddings API
       |                              |
       |                              v
       |                    Qdrant (dense vectors)
       |                              |
       +----------+-------------------+
                  v
       lawagent.search.HybridSearcher
       |-- temporal_filter (sparse + Qdrant)
       |-- DenseRetriever
       |-- BM25Index
       `-- RRF + exact title/article signals
                  |
                  v
         CLI results / baseline report
```

`data/manifest.yaml` là nguồn metadata của từng văn bản, gồm định danh, loại văn bản, ngày hiệu lực/hết hiệu lực, trạng thái và nguồn. Parser đọc `.txt` UTF-8 hoặc `.docx`, tạo một chunk cho mỗi Điều (chỉ chia Điều dài theo Khoản), rồi ghi JSONL. `validation_report.json` xác nhận 702 Điều, 724 chunks, 1.127 dẫn chiếu và không có dẫn chiếu nội bộ treo.

Sau khi ingest, 724 chunks tạo thành tập vector dense trong Qdrant theo trạng thái được ghi nhận của dự án. <!-- VERIFY: Xác nhận collection Qdrant của môi trường đang dùng vẫn chứa đủ 724 vector sau mỗi lần triển khai hoặc ingest lại. -->

## Luồng truy xuất hybrid

1. Người dùng gọi `lawagent-search` hoặc `python -m lawagent.search` với câu hỏi, `--as-of` và giới hạn kết quả. Ngày mặc định là ngày hiện tại; mỗi nhánh mặc định lấy 10 ứng viên và CLI trả về 5 kết quả.
2. `HybridSearcher` lọc corpus cục bộ bằng `filter_effective_chunks()` trước khi lập `BM25Index`; một chunk hợp lệ khi `effective_from <= as_of` và `effective_to` chưa có hoặc `as_of <= effective_to`. Hai biên ngày đều được tính.
3. Nhánh sparse chạy BM25 trên `text_for_embedding` của các chunk còn hiệu lực. Với truy vấn dạng `Điều N`, nhánh này đánh dấu các chunk trùng `dieu_label` và ưu tiên văn bản có cấp bậc pháp lý cao hơn khi cùng số Điều.
4. Nhánh dense dùng `DenseRetriever` để embed truy vấn bằng model cấu hình, sau đó truy vấn Qdrant. `build_temporal_filter()` áp dụng cùng điều kiện hiệu lực ở phía Qdrant, bao gồm `effective_to` rỗng hoặc lớn hơn/bằng ngày hỏi.
5. `reciprocal_rank_fusion()` cộng điểm `1 / (60 + rank)` cho từng nguồn. Kết quả có mặt ở cả dense và sparse được hợp nhất theo `chunk_id`; kết quả chỉ có một nguồn vẫn được giữ lại.
6. Khi sắp xếp, khớp chính xác số Điều được ưu tiên trước, tiếp theo là khớp chính xác `dieu_title`; với khớp Điều, loại văn bản và `hierarchy_level` phá hòa trước điểm RRF. Mỗi `HybridResult` cho biết rank, điểm RRF, nguồn đóng góp và điểm dense/BM25 riêng lẻ.

Ví dụ CLI:

```powershell
uv run lawagent-search "Điều 35" --as-of 2026-09-22
uv run python -m lawagent.search "thời gian thử việc" --as-of 2023-01-01 --limit 5
uv run lawagent-baseline
```

Lệnh baseline chạy 10 truy vấn có ngày áp dụng cố định và ghi `data/processed/retrieval_baseline.json`. Báo cáo hiện có ghi nhận `passed: 10` trên `total: 10` cho retriever `dense+bm25+rrf` với `rrf_k: 60`.

## Các trừu tượng chính

| Thành phần | Vai trò |
| --- | --- |
| `LegalChunk` — `src/lawagent/parser.py` | Đơn vị dữ liệu chung: nội dung Điều, `text_for_embedding`, breadcrumb, cấp bậc, khoảng hiệu lực và dẫn chiếu. |
| `LegalReference` — `src/lawagent/parser.py` | Mô tả dẫn chiếu pháp lý và `target_chunk_id` khi dẫn chiếu nội bộ được phân giải. |
| `BM25Index` / `SparseResult` — `src/lawagent/sparse.py` | Lập chỉ mục BM25 trong bộ nhớ và biểu diễn một kết quả sparse có cờ khớp Điều. |
| `DenseRetriever` / `DenseResult` — `src/lawagent/dense.py` | Tạo embedding truy vấn, tìm Qdrant có bộ lọc thời gian và chuẩn hóa kết quả dense. |
| `is_effective()` / `filter_effective_chunks()` — `src/lawagent/temporal_filter.py` | Kiểm tra và lọc hiệu lực cho dữ liệu cục bộ với khoảng ngày bao gồm hai đầu mút. |
| `build_temporal_filter()` — `src/lawagent/temporal_filter.py` | Tạo bộ lọc Qdrant tương đương điều kiện hiệu lực ở nhánh dense. |
| `HybridSearcher` / `HybridResult` — `src/lawagent/search.py` | Điều phối hai nhánh retrieval và biểu diễn kết quả đã hợp nhất. |
| `reciprocal_rank_fusion()` — `src/lawagent/search.py` | Hợp nhất thứ hạng dense/BM25 với RRF và các tín hiệu khớp chính xác. |
| `BaselineCase` / `run_baseline()` — `src/lawagent/baseline.py` | Định nghĩa bộ truy vấn hồi quy và ghi báo cáo retrieval có thể tái lập. |

## Mô hình dữ liệu và hiệu lực

```text
Manifest document
       |
       v
LegalChunk ── references[] ──> LegalReference
       |                         |
       |                         +--> target_chunk_id (nội bộ, nếu phân giải được)
       |
       +--> text_for_embedding ──> BM25 + OpenAI embeddings
       +--> effective_from/effective_to ──> local filter + Qdrant payload filter
```

`effective_from` là bắt buộc cho lọc hiệu lực. `effective_to` có thể rỗng để biểu thị hiệu lực mở. Hàm `parse_payload_date()` nhận cả ngày ISO và timestamp RFC 3339 từ payload Qdrant. Metadata `status`, `doc_id`, `hierarchy_level`, `effective_from` và `effective_to` cũng có payload index trong collection.

`references.py` vẫn cung cấp `extract_locator_text()` và `expand_reference_context()` để lấy đúng Khoản/Điểm và mở rộng dẫn chiếu nội bộ một tầng. Các hàm này chưa được gọi bởi `HybridSearcher`.

## Thành phần còn được lên kế hoạch

Retriever hiện trả về các chunks và trace điểm số; nó chưa phải một hệ thống trả lời pháp lý hoàn chỉnh. Các phần sau vẫn chưa có module runtime tương ứng:

- Planner phân tích phạm vi, mốc thời gian và các sub-query.
- Pipeline agent điều phối retriever, mở rộng dẫn chiếu một tầng, Synthesis và `AgentState`.
- Citation verifier kiểm tra citation với context đã truy xuất và cơ chế retry có giới hạn.
- Giao diện người dùng hiển thị câu trả lời, ngày áp dụng, citation và retrieval trace.
- Đánh giá đầy đủ, bao gồm citation metrics và ablation cho từng nhánh retrieval.

## Cấu trúc thư mục

```text
src/lawagent/
├── config.py           # biến môi trường Qdrant và embedding
├── parser.py           # parse văn bản, schema chunk và dẫn chiếu
├── references.py       # trích Khoản/Điểm và mở rộng dẫn chiếu
├── index.py            # tạo collection Qdrant và payload indexes
├── ingest.py           # tạo embedding và upsert chunks
├── sparse.py           # BM25 cục bộ
├── temporal_filter.py  # lọc hiệu lực cục bộ và Qdrant
├── dense.py            # dense retrieval qua OpenAI và Qdrant
├── search.py           # hybrid search, RRF và CLI
└── baseline.py         # baseline retrieval 10 truy vấn

data/
├── manifest.yaml       # metadata nguồn và hiệu lực văn bản
├── raw/                # đầu vào pháp lý đã tải
└── processed/          # chunks JSONL, validation và baseline report

tests/                  # 24 kiểm thử parser, references, sparse, dense, temporal và hybrid search
```

Các lệnh phát triển chính là `lawagent-parse`, `lawagent-search` và `lawagent-baseline`, được đăng ký trong `pyproject.toml`. Ingestion và dense search cần Qdrant đang chạy cùng thông tin xác thực OpenAI hợp lệ; kiểm thử đơn vị dùng client giả và chạy cục bộ bằng:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

## Ranh giới hiện tại

LawAgent hiện là công cụ chuẩn bị corpus và truy xuất hybrid theo thời điểm, không phải dịch vụ tư vấn hoặc trả lời pháp lý hoàn chỉnh. Kết quả baseline kiểm tra khả năng tìm đúng chunk, không đánh giá tính đúng đắn của câu trả lời do mô hình ngôn ngữ tạo ra hay thay thế thẩm định pháp lý chuyên môn.
