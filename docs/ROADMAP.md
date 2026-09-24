# ROADMAP — Kế hoạch 6 giai đoạn

Mỗi giai đoạn dự kiến cần **8–10 giờ** và có một "Definition of Done" cụ thể. Nếu
một giai đoạn trượt, cắt phần "Nếu còn thời gian" của giai đoạn sau, **không** kéo
dài timeline tổng thể.

---

## Giai đoạn 1 — Dữ liệu & Parser

Đây là giai đoạn quyết định chất lượng cả dự án. Đừng vội viết agent.

- [x] Chốt 4 nhóm/8 phiên bản văn bản, điền `data/manifest.yaml`
- [x] Tải bản gốc và bản Công báo có lớp text về `data/raw/`, làm sạch header/footer
- [x] Viết `src/lawagent/parser.py`: tách Chương → Mục → Điều, sinh breadcrumb
- [x] Viết `scripts/validate_parser.py`: đếm số Điều parse được vs số thực tế
- [x] Trích `references` bằng regex dẫn chiếu

**Kết quả:** `chunks.jsonl` có **702 Điều / 724 chunks** cho đủ 8 phiên bản; toàn bộ
đếm Điều đều khớp manifest, không có dẫn chiếu nội bộ bị treo. Mẫu 10 chunks cố định
nằm tại `data/processed/spot_check.md`.

⚠️ Cạm bẫy: parser sẽ vỡ ở những chỗ bất thường (Điều có phụ lục, bảng biểu, Điều
được bổ sung dạng "Điều 24a"). Xử lý ngoại lệ thủ công nếu chỉ vài trường hợp —
đừng cố làm regex hoàn hảo.

---

## Giai đoạn 2 — Index & Retrieval

- [x] Chạy Qdrant bằng Docker, tạo collection + payload index
- [x] Embed bằng OpenAI Embeddings API (`text-embedding-3-large`, 1024 chiều),
  ingest toàn bộ chunk
- [x] Viết `src/lawagent/sparse.py`: BM25 + ưu tiên truy vấn số Điều
- [x] Viết module search: dense search + RRF với kết quả BM25
- [x] Viết module temporal filter
- [x] Script CLI: nhập truy vấn → in ra top-5 chunk kèm điểm

**Trạng thái:** hoàn thành. Hạ tầng Qdrant chứa 724 vector; dense retrieval, BM25,
RRF, temporal filter và CLI hybrid đã chạy end-to-end. Bộ 24 test đều đạt và
baseline 10 truy vấn đạt 10/10 top-1.

**Done khi:** gõ "thời gian thử việc" trả về đúng Điều về thử việc ở vị trí top-1,
và gõ "Điều 35" trả về đúng Điều 35 (chứng minh sparse search hoạt động).

**Phần mở rộng đã hoàn thành:** 10 truy vấn thử và top-5 đã được lưu tại
`data/processed/retrieval_baseline.json` làm baseline để so sánh về sau.

---

## Giai đoạn 3 — Pipeline agent

- [ ] Định nghĩa `AgentState`
- [ ] Node Planner gọi OpenAI Responses API, dùng Structured Outputs để parse
  kết quả vào Pydantic model
- [ ] Node Retriever (gọi lại code Giai đoạn 2) + mở rộng dẫn chiếu 1 tầng
- [ ] Node Synthesis gọi OpenAI Responses API, chỉ nhận context đã retrieve
- [ ] Lắp LangGraph, chạy end-to-end

**Done khi:** chạy 5 câu hỏi Loại A, nhận được câu trả lời có citation (dù citation
có thể còn sai — Giai đoạn 4 sẽ xử lý).

---

## Giai đoạn 4 — Verifier & xử lý thời gian

- [ ] Node Citation Verifier + vòng retry
- [ ] Kiểm thử riêng nhánh temporal: hỏi về lương tối thiểu ở 2 mốc thời gian khác
  nhau, xác nhận trả về 2 nghị định khác nhau
- [ ] Logging `retrieval_trace` đầy đủ
- [ ] Xử lý các case lỗi: LLM trả JSON hỏng, Qdrant không có kết quả, câu hỏi
  ngoài phạm vi

**Done khi:** câu hỏi Loại C cho kết quả đúng, và không có citation bịa nào lọt ra
trong 20 lần chạy thử.

Đây là milestone quan trọng nhất — hai tính năng ở giai đoạn này chính là điểm bán
của dự án trên CV.

---

## Giai đoạn 5 — Đánh giá

- [ ] Xây bộ 30 câu hỏi eval (chi tiết ở `docs/EVALUATION.md`), tự soạn đáp án chuẩn
  kèm Điều/Khoản đúng
- [ ] Viết `eval.py`: chạy cả bộ, tính Citation Precision/Recall
- [ ] Chạy RAGAS: faithfulness, answer relevancy, context precision
- [ ] **Chạy ablation**: tắt hybrid (chỉ dense), tắt mở rộng dẫn chiếu, tắt temporal
  filter — đo lại từng trường hợp
- [ ] Ghi bảng kết quả vào `docs/EVALUATION.md`

**Done khi:** có bảng số liệu so sánh baseline vs full system.

Ablation là thứ phân biệt dự án này với hàng nghìn "RAG chatbot" trên GitHub. Nó
chứng minh mỗi thành phần bạn thêm vào đều có lý do đo được.

---

## Giai đoạn 6 — UI, tài liệu, hoàn thiện

- [ ] Streamlit UI 3 phần như mô tả trong `docs/ARCHITECTURE.md`
- [ ] README: mô tả vấn đề, kiến trúc (kèm sơ đồ), kết quả đo, **Limitations**
- [ ] GIF demo ngắn (khoảng 30 giây) nhúng vào README
- [ ] Dọn code, bổ sung định dạng phân phối dependency nếu cần và hoàn thiện hướng dẫn chạy
- [ ] Đẩy lên GitHub, repo public

**Done khi:** người lạ clone về, đọc README, chạy được trong 10 phút.

**Nếu còn thời gian:** thêm cross-encoder rerank và đo xem có cải thiện không.
Kết quả âm tính cũng là kết quả đáng ghi.

---

## Quản lý rủi ro

| Rủi ro                                   | Dấu hiệu                                    | Ứng phó                                                                                                                             |
| ----------------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Parser kéo dài sang Giai đoạn 2 | Kết thúc Giai đoạn 1 mà chưa parse xong 2 văn bản | Giảm corpus xuống 2 văn bản. Chất lượng > số lượng. |
| Embedding tiếng Việt cho kết quả kém | Top-5 toàn chunk không liên quan | Thử tăng số chiều của `text-embedding-3-large`, so sánh với `bge-m3`, và tăng trọng số BM25 trong RRF. |
| Chi phí OpenAI API | Chạy eval 30 câu × nhiều lần | Cache response theo hash của model + prompt. Dùng `gpt-5.4-mini` cho Planner, `gpt-5.5` cho Synthesis và theo dõi token usage. |
| Sa đà vào UI                           | Giai đoạn 6 dùng hết thời gian chỉnh CSS | UI xấu không sao. README và số liệu mới là thứ nhà tuyển dụng đọc.                                                       |

## Nguyên tắc commit

Commit nhỏ, message rõ, **push sau mỗi giai đoạn**. Lịch sử đóng góp đều đặn xuyên
suốt dự án tự nó là một tín hiệu tốt trên GitHub.
