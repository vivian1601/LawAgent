# ROADMAP — Kế hoạch 6 tuần

Giả định **8–10 giờ/tuần**. Mỗi tuần có một "Definition of Done" cụ thể. Nếu tuần
nào trượt, cắt phần "Nếu còn thời gian" của tuần sau, **không** kéo dài timeline.

---

## Tuần 1 — Dữ liệu & Parser

Đây là tuần quyết định chất lượng cả dự án. Đừng vội viết agent.

- [x] Chốt 4 nhóm/8 phiên bản văn bản, điền `data/manifest.yaml`
- [x] Tải bản gốc và bản Công báo có lớp text về `data/raw/`, làm sạch header/footer
- [x] Viết `parser.py`: tách Chương → Mục → Điều, sinh breadcrumb
- [x] Viết `validate_parser.py`: đếm số Điều parse được vs số thực tế
- [x] Trích `references` bằng regex dẫn chiếu

**Kết quả:** `chunks.jsonl` có **702 Điều / 724 chunks** cho đủ 8 phiên bản; toàn bộ
đếm Điều đều khớp manifest, không có dẫn chiếu nội bộ bị treo. Mẫu 10 chunks cố định
nằm tại `data/processed/spot_check.md`.

⚠️ Cạm bẫy: parser sẽ vỡ ở những chỗ bất thường (Điều có phụ lục, bảng biểu, Điều
được bổ sung dạng "Điều 24a"). Xử lý ngoại lệ thủ công nếu chỉ vài trường hợp —
đừng cố làm regex hoàn hảo.

---

## Tuần 2 — Index & Retrieval

- [ ] Chạy Qdrant bằng Docker, tạo collection + payload index
- [ ] Embed bằng OpenAI Embeddings API (`text-embedding-3-large`, 1024 chiều),
      ingest toàn bộ chunk
- [ ] Viết `search.py`: dense + BM25 + RRF
- [ ] Viết `temporal_filter.py`
- [ ] Script CLI: nhập truy vấn → in ra top-5 chunk kèm điểm

**Done khi:** gõ "thời gian thử việc" trả về đúng Điều về thử việc ở vị trí top-1,
và gõ "Điều 35" trả về đúng Điều 35 (chứng minh sparse search hoạt động).

**Nếu còn thời gian:** viết 10 truy vấn thử, ghi lại top-5 làm baseline để so sánh
về sau.

---

## Tuần 3 — Pipeline agent

- [ ] Định nghĩa `AgentState`
- [ ] Node Planner gọi OpenAI Responses API, dùng Structured Outputs để parse
      kết quả vào Pydantic model
- [ ] Node Retriever (gọi lại code Tuần 2) + mở rộng dẫn chiếu 1 tầng
- [ ] Node Synthesis gọi OpenAI Responses API, chỉ nhận context đã retrieve
- [ ] Lắp LangGraph, chạy end-to-end

**Done khi:** chạy 5 câu hỏi Loại A, nhận được câu trả lời có citation (dù citation
có thể còn sai — Tuần 4 sẽ xử lý).

---

## Tuần 4 — Verifier & xử lý thời gian

- [ ] Node Citation Verifier + vòng retry
- [ ] Kiểm thử riêng nhánh temporal: hỏi về lương tối thiểu ở 2 mốc thời gian khác
      nhau, xác nhận trả về 2 nghị định khác nhau
- [ ] Logging `retrieval_trace` đầy đủ
- [ ] Xử lý các case lỗi: LLM trả JSON hỏng, Qdrant không có kết quả, câu hỏi
      ngoài phạm vi

**Done khi:** câu hỏi Loại C cho kết quả đúng, và không có citation bịa nào lọt ra
trong 20 lần chạy thử.

Đây là milestone quan trọng nhất — hai tính năng ở tuần này chính là điểm bán của
dự án trên CV.

---

## Tuần 5 — Đánh giá

- [ ] Xây bộ 30 câu hỏi eval (chi tiết ở `EVALUATION.md`), tự soạn đáp án chuẩn
      kèm Điều/Khoản đúng
- [ ] Viết `eval.py`: chạy cả bộ, tính Citation Precision/Recall
- [ ] Chạy RAGAS: faithfulness, answer relevancy, context precision
- [ ] **Chạy ablation**: tắt hybrid (chỉ dense), tắt mở rộng dẫn chiếu, tắt temporal
      filter — đo lại từng trường hợp
- [ ] Ghi bảng kết quả vào `EVALUATION.md`

**Done khi:** có bảng số liệu so sánh baseline vs full system.

Ablation là thứ phân biệt dự án này với hàng nghìn "RAG chatbot" trên GitHub. Nó
chứng minh mỗi thành phần bạn thêm vào đều có lý do đo được.

---

## Tuần 6 — UI, tài liệu, hoàn thiện

- [ ] Streamlit UI 3 phần như mô tả trong `ARCHITECTURE.md`
- [ ] README: mô tả vấn đề, kiến trúc (kèm sơ đồ), kết quả đo, **Limitations**
- [ ] GIF demo ngắn (khoảng 30 giây) nhúng vào README
- [ ] Dọn code, viết `requirements.txt`, hướng dẫn chạy
- [ ] Đẩy lên GitHub, repo public

**Done khi:** người lạ clone về, đọc README, chạy được trong 10 phút.

**Nếu còn thời gian:** thêm cross-encoder rerank và đo xem có cải thiện không.
Kết quả âm tính cũng là kết quả đáng ghi.

---

## Quản lý rủi ro

| Rủi ro | Dấu hiệu | Ứng phó |
|---|---|---|
| Parser ngốn hết Tuần 1–2 | Hết Tuần 1 mà chưa parse xong 2 văn bản | Giảm corpus xuống 2 văn bản. Chất lượng > số lượng. |
| Embedding tiếng Việt cho kết quả kém | Top-5 toàn chunk không liên quan | Thử tăng số chiều của `text-embedding-3-large`, so sánh với `bge-m3`, và tăng trọng số BM25 trong RRF. |
| Chi phí OpenAI API | Chạy eval 30 câu × nhiều lần | Cache response theo hash của model + prompt. Dùng `gpt-5.4-mini` cho Planner, `gpt-5.5` cho Synthesis và theo dõi token usage. |
| Sa đà vào UI | Tuần 6 dùng hết thời gian chỉnh CSS | UI xấu không sao. README và số liệu mới là thứ nhà tuyển dụng đọc. |

## Nguyên tắc commit

Commit nhỏ, message rõ, **push đều mỗi tuần**. Biểu đồ đóng góp đều đặn trong 6
tuần tự nó là một tín hiệu tốt trên GitHub.
