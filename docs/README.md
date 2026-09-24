<!-- generated-by: gsd-doc-writer -->
# LawAgent — Trợ lý tra cứu pháp luật lao động Việt Nam (RAG)

> Dự án cá nhân. Mục tiêu: xây dựng hệ thống RAG trả lời câu hỏi về pháp luật lao
> động Việt Nam, kèm trích dẫn Điều/Khoản và xét thời điểm hiệu lực của văn bản.

---

## 1. Vấn đề

Người lao động và nhân sự HR thường xuyên phải tra cứu quy định về hợp đồng, thời
giờ làm việc, sa thải, trợ cấp thôi việc... Việc tra cứu thủ công có ba khó khăn:

1. Quy định nằm rải ở nhiều tầng văn bản (Luật → Nghị định → Thông tư).
2. Văn bản bị sửa đổi, bổ sung, bãi bỏ theo thời gian — dễ trích dẫn nhầm bản cũ.
3. Các điều khoản dẫn chiếu chéo lẫn nhau.

Một chatbot LLM thuần không giải quyết được: nó bịa số hiệu văn bản và số điều khoản.

## 2. Giải pháp dự kiến

Kiến trúc mục tiêu là pipeline RAG có cấu trúc, điều phối bởi 3 agent trong
LangGraph. Các agent, tầng tổng hợp và verifier dưới đây chưa được triển khai trong
mã nguồn hiện tại:

```
Câu hỏi
   │
   ▼
[1] Planner Agent ──► phân rã câu hỏi, trích mốc thời gian áp dụng
   │
   ▼
[2] Retriever Agent ─► hybrid search + lọc theo hiệu lực + đi theo dẫn chiếu (1 tầng)
   │
   ▼
[3] Synthesis Agent ─► soạn câu trả lời, gắn citation
   │
   ▼
[4] Citation Verifier (code thuần, không phải LLM) ─► loại bỏ trích dẫn bịa
   │
   ▼
Câu trả lời + danh sách Điều/Khoản nguồn
```

## 3. Điểm kỹ thuật nổi bật

| Vấn đề | Cách giải quyết trong dự án |
|---|---|
| Chunking phá vỡ cấu trúc pháp lý | Parser riêng theo Chương → Mục → Điều → Khoản; mỗi chunk = trọn một Điều, kèm breadcrumb |
| Trích dẫn sai / bịa | Verifier đối chiếu citation với corpus là hạng mục dự kiến, chưa có trong mã nguồn |
| Hiệu lực theo thời gian | `temporal_filter.py` lọc cùng điều kiện hiệu lực cho corpus BM25 và Qdrant dense theo `--as-of` |
| Dẫn chiếu chéo | Parser lưu field `references`; mã hiện có mở rộng một tầng cho dẫn chiếu nội bộ, còn dẫn chiếu liên văn bản chờ temporal resolver |

## 4. Tech stack

- **Đã dùng:** Python 3.11, Qdrant chạy cục bộ bằng Docker Compose, OpenAI
  Embeddings API (`text-embedding-3-large`, 1024 chiều) và `rank-bm25` cho BM25.
- **Dự kiến:** LangGraph cho điều phối agent, OpenAI Responses API cho Planner và
  Synthesis, Streamlit cho UI, cùng RAGAS và bộ eval tự xây. Những thành phần này
  chưa xuất hiện trong dependencies hoặc mã nguồn hiện tại.

## 5. Trạng thái triển khai

**Giai đoạn 1 hoàn thành:** 8 phiên bản văn bản chính thức được chuẩn hóa thành
**702 Điều / 724 chunks**, có breadcrumb Chương/Mục/Điều, metadata hiệu lực và
1.127 dẫn chiếu có cấu trúc. Trong đó 537 dẫn chiếu nội bộ đã phân giải, 590 dẫn
chiếu chéo văn bản chờ resolver theo thời gian và 24 quan hệ ngoại lệ đã được nhận
diện. Báo cáo kiểm định không có sai lệch số Điều hoặc dẫn chiếu nội bộ bị treo.

**Giai đoạn 2 hoàn thành:** Qdrant được cấu hình qua Docker Compose và chứa 724
vector. `DenseRetriever` và BM25 được hợp nhất bằng RRF; cả hai nhánh áp dụng bộ
lọc hiệu lực theo ngày. CLI `lawagent-search` trả top-5 kèm điểm/nguồn và CLI
`lawagent-baseline` đã ghi snapshot 10 truy vấn với kết quả 10/10 top-1. Toàn bộ
24 test hiện có đều đạt.

```powershell
uv sync --extra dev
uv run python -m lawagent.parser
uv run python scripts/validate_parser.py
uv run pytest -q -p no:cacheprovider
uv run lawagent-search "Điều 35" --as-of 2026-09-22
uv run lawagent-baseline
```

## 6. Bộ tài liệu này

| File | Nội dung |
|---|---|
| [SCOPE.md](SCOPE.md) | Phạm vi làm / **không làm**. Đọc file này trước tiên. |
| [LEGAL_SOURCES.md](LEGAL_SOURCES.md) | Danh mục corpus đã xác minh, nguồn chính thức và lộ trình mở rộng |
| [DATA.md](DATA.md) | Nguồn dữ liệu, quy trình ingest, schema metadata |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Kiến trúc mã nguồn hiện tại và các thành phần dự kiến |
| [CONFIGURATION.md](CONFIGURATION.md) | Biến môi trường và cấu hình Qdrant/OpenAI |
| [GETTING-STARTED.md](GETTING-STARTED.md) | Cài đặt, ingest và chạy tìm kiếm hybrid theo thời điểm |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Quy trình phát triển và trách nhiệm từng module |
| [TESTING.md](TESTING.md) | Cách chạy và bổ sung kiểm thử |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Runtime Qdrant cục bộ bằng Docker Compose |
| [ROADMAP.md](ROADMAP.md) | Lộ trình triển khai theo các giai đoạn |
| [EVALUATION.md](EVALUATION.md) | Bộ test, chỉ số đo, cách báo cáo kết quả |
| [CV.md](CV.md) | Cách viết dự án này vào CV và trả lời phỏng vấn |

## 7. Miễn trừ trách nhiệm

Đây là công cụ tra cứu tham khảo phục vụ mục đích học tập. Kết quả **không phải là
tư vấn pháp lý** và không thay thế ý kiến của luật sư hoặc cơ quan có thẩm quyền.
Câu này phải hiển thị cố định trên UI.
