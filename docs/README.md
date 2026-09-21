# LexAgent — Trợ lý tra cứu pháp luật lao động Việt Nam (Multi-Agent RAG)

> Dự án cá nhân. Mục tiêu: xây dựng hệ thống RAG nhiều agent trả lời câu hỏi về
> pháp luật lao động Việt Nam, **luôn kèm trích dẫn Điều/Khoản** và **có ý thức về
> thời điểm hiệu lực** của văn bản.

---

## 1. Vấn đề

Người lao động và nhân sự HR thường xuyên phải tra cứu quy định về hợp đồng, thời
giờ làm việc, sa thải, trợ cấp thôi việc... Việc tra cứu thủ công có ba khó khăn:

1. Quy định nằm rải ở nhiều tầng văn bản (Luật → Nghị định → Thông tư).
2. Văn bản bị sửa đổi, bổ sung, bãi bỏ theo thời gian — dễ trích dẫn nhầm bản cũ.
3. Các điều khoản dẫn chiếu chéo lẫn nhau.

Một chatbot LLM thuần không giải quyết được: nó bịa số hiệu văn bản và số điều khoản.

## 2. Giải pháp

Pipeline RAG có cấu trúc, điều phối bởi 3 agent trong LangGraph:

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
| Trích dẫn sai / bịa | Verifier bằng code đối chiếu mọi citation với corpus, drop nếu không khớp |
| Hiệu lực theo thời gian | Metadata `effective_from` / `effective_to`, filter tại tầng vector DB |
| Dẫn chiếu chéo | Trích pattern dẫn chiếu khi ingest, lưu thành field `references`, mở rộng 1 tầng khi retrieve |

## 4. Tech stack

- **Python 3.11**
- **LangGraph** — điều phối agent (state machine)
- **Qdrant** (Docker local) — vector DB, hỗ trợ metadata filter tốt
- **OpenAI Embeddings API** (`text-embedding-3-large`, 1024 chiều) — dense embedding
  đa ngôn ngữ cho tiếng Việt
- **OpenAI Responses API** — `gpt-5.4-mini` cho Planner và `gpt-5.5` cho
  Synthesis; tên model được cấu hình bằng biến môi trường
- **Streamlit** — UI demo
- **RAGAS + bộ eval tự xây** — đo chất lượng

## 5. Trạng thái triển khai

Tuần 1 đã hoàn thành: 8 phiên bản văn bản chính thức được chuẩn hóa thành **702
Điều / 724 chunks**, có breadcrumb Chương/Mục/Điều, metadata hiệu lực và 1.127 dẫn
chiếu có cấu trúc. Trong đó 537 dẫn chiếu nội bộ đã phân giải, 590 dẫn chiếu chéo
văn bản chờ resolver theo thời gian và 24 quan hệ ngoại lệ đã được nhận diện. Báo
cáo kiểm định không có sai lệch số Điều hoặc dẫn chiếu nội bộ bị treo.

```powershell
uv sync --extra dev
uv run python -m lawagent.parser
uv run python scripts/validate_parser.py
uv run pytest -q -p no:cacheprovider
```

## 6. Bộ tài liệu này

| File | Nội dung |
|---|---|
| `SCOPE.md` | Phạm vi làm / **không làm**. Đọc file này trước tiên. |
| `LEGAL_SOURCES.md` | Danh mục corpus đã xác minh, nguồn chính thức và lộ trình mở rộng |
| `DATA.md` | Nguồn dữ liệu, quy trình ingest, schema metadata |
| `ARCHITECTURE.md` | Thiết kế 3 agent, state, prompt |
| `ROADMAP.md` | Kế hoạch 6 tuần, chia theo milestone |
| `EVALUATION.md` | Bộ test, chỉ số đo, cách báo cáo kết quả |
| `CV.md` | Cách viết dự án này vào CV và trả lời phỏng vấn |

## 7. Miễn trừ trách nhiệm

Đây là công cụ tra cứu tham khảo phục vụ mục đích học tập. Kết quả **không phải là
tư vấn pháp lý** và không thay thế ý kiến của luật sư hoặc cơ quan có thẩm quyền.
Câu này phải hiển thị cố định trên UI.
