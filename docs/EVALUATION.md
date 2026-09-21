# EVALUATION — Bộ test & Chỉ số đo

> Đây là phần khiến dự án khác biệt. Rất nhiều dự án RAG cá nhân dừng ở "chạy được".
> Có số liệu đo chứng minh bạn hiểu mình đang xây cái gì.

## 1. Bộ test: 30 câu hỏi

Tự soạn tay. Mỗi câu ghi rõ đáp án chuẩn **và** danh sách Điều/Khoản bắt buộc phải
được trích dẫn. Đây là công việc tốn khoảng 3–4 giờ và không thể tự động hóa.

Phân bổ:

| Loại | Số câu | Kiểm tra điều gì |
|---|---|---|
| A — Tra cứu trực tiếp | 12 | Retrieval cơ bản |
| B — Tổng hợp nhiều điều | 8 | Multi-hop, mở rộng dẫn chiếu |
| C — Có yếu tố thời gian | 5 | Temporal filter |
| D — Ngoài phạm vi | 5 | Hệ thống có biết từ chối không |

Loại D quan trọng: hỏi về thuế, đất đai, hoặc câu vô nghĩa. Hệ thống **phải** trả
lời "ngoài phạm vi", không được bịa.

### Định dạng

```yaml
# eval/questions.yaml
- id: A01
  type: A
  question: "Thời gian thử việc tối đa đối với công việc của người quản lý doanh nghiệp là bao lâu?"
  as_of: null                      # null = hôm nay
  expected_citations: ["45-2019-QH14__dieu_25"]
  expected_answer_contains: ["180 ngày"]
  notes: "Xác minh lại số ngày trên vbpl.vn trước khi chốt"

- id: C02
  type: C
  question: "Mức lương tối thiểu vùng I áp dụng cho hợp đồng ký tháng 3/2023 là bao nhiêu?"
  as_of: "2023-03-01"
  expected_citations: ["<nghị định lương tối thiểu có hiệu lực tại thời điểm đó>"]
  expected_answer_contains: []     # điền sau khi tra cứu

- id: D01
  type: D
  question: "Thuế thu nhập cá nhân bậc 1 là bao nhiêu phần trăm?"
  as_of: null
  expect_out_of_scope: true
```

⚠️ **Tự tra cứu để điền `expected_*`.** Đừng lấy đáp án từ trí nhớ hay từ LLM —
đáp án chuẩn sai thì toàn bộ số liệu eval vô nghĩa.

## 2. Chỉ số

### 2.1 Citation Precision / Recall (chỉ số chính)

Đây là chỉ số quan trọng nhất của dự án, vì nó đo trực tiếp điều người dùng pháp lý
quan tâm: *trích dẫn có đúng không*.

```
Citation Precision = |cited ∩ expected| / |cited|
Citation Recall    = |cited ∩ expected| / |expected|
Citation F1        = harmonic mean
```

### 2.2 Hallucinated Citation Rate

```
= số citation không tồn tại trong corpus / tổng số citation
```

Mục tiêu: **0%** sau khi có Verifier. Đây là con số bạn nên nêu bật.

### 2.3 Out-of-Scope Accuracy

Tỷ lệ câu Loại D bị từ chối đúng cách. Mục tiêu 5/5.

### 2.4 Temporal Accuracy

Tỷ lệ câu Loại C trích đúng phiên bản văn bản theo mốc thời gian. Mục tiêu ≥ 4/5.

### 2.5 RAGAS (bổ trợ)

- `faithfulness` — câu trả lời có bám vào context không
- `answer_relevancy` — có trả lời đúng câu hỏi không
- `context_precision` — chunk lấy về có liên quan không

RAGAS dùng LLM để chấm nên có nhiễu. Dùng làm tham khảo, không phải chỉ số chính.
Chạy 3 lần lấy trung bình nếu muốn báo cáo.

## 3. Ablation Study

Chạy cùng bộ 30 câu qua 5 cấu hình. Đây là phần giá trị nhất để kể trong phỏng vấn.

| # | Cấu hình | Mục đích |
|---|---|---|
| 1 | Baseline: LLM thuần, không RAG | Cho thấy RAG có cần thiết không |
| 2 | RAG đơn giản: chunk 512 ký tự, dense only | Baseline RAG thông thường |
| 3 | + chunking theo cấu trúc pháp lý | Đo giá trị của parser |
| 4 | + hybrid search (BM25 + RRF) | Đo giá trị của sparse |
| 5 | Full: + temporal filter + mở rộng dẫn chiếu + verifier | Hệ thống hoàn chỉnh |

### Bảng kết quả (điền sau Tuần 5)

| Cấu hình | Cit. P | Cit. R | Cit. F1 | Halluc. | OOS | Temporal |
|---|---|---|---|---|---|---|
| 1. LLM thuần | | | | | | |
| 2. RAG đơn giản | | | | | | |
| 3. + legal chunking | | | | | | |
| 4. + hybrid | | | | | | |
| 5. Full | | | | | | |

Cấu hình 1 dự kiến có Hallucinated Citation Rate rất cao — đó chính là luận điểm
mở đầu cho README của bạn.

## 4. Phân tích lỗi

Sau khi chạy eval, đọc **tất cả** các câu sai, phân loại nguyên nhân:

| Nhóm lỗi | Ví dụ |
|---|---|
| Retrieval miss | Điều đúng không nằm trong top-8 |
| Parser lỗi | Chunk bị cắt sai nên thiếu nội dung |
| Dẫn chiếu sâu | Cần 2 tầng mà hệ thống chỉ mở rộng 1 |
| Tổng hợp sai | Có đủ context nhưng LLM diễn giải nhầm |
| Đáp án chuẩn sai | Bạn ghi sai khi soạn bộ test — sửa lại |

Viết mục "Error Analysis" trong README với bảng phân bố này. Nó cho thấy bạn làm
việc có phương pháp, và cung cấp sẵn nội dung để nói khi được hỏi "nếu có thêm
thời gian, bạn sẽ cải thiện gì?".

## 5. Kiểm soát chi phí khi chạy eval

- Cache response theo `hash(model + prompt)`, lưu `eval/cache/`
- 5 cấu hình × 30 câu × 2 lần gọi LLM = 300 request. Cache sẽ cứu bạn khi phải
  chạy lại nhiều lần.
- Planner dùng `gpt-5.4-mini`, Synthesis dùng `gpt-5.5`; cả hai gọi qua OpenAI
  Responses API và cho phép ghi đè tên model bằng biến môi trường.
