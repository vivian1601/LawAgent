# EVALUATION — Bộ test & Chỉ số đo

> Đây là phần khiến dự án khác biệt. Rất nhiều dự án RAG cá nhân dừng ở "chạy được".
> Có số liệu đo chứng minh bạn hiểu mình đang xây cái gì.

> **Trạng thái hiện tại:** đây là kế hoạch đánh giá, chưa phải bộ eval đã chạy. Kho mã chưa có thư mục
> eval hoặc bộ câu hỏi YAML, harness chấm điểm, kết quả đo hay tích hợp RAGAS. Các kiểm thử hiện có
> gồm 24 unit/corpus-backed test cho parser, dẫn chiếu, BM25, dense retrieval,
> temporal filter và hybrid search. Ngoài ra đã có baseline retrieval 10 truy vấn
> đạt 10/10 top-1; đây chưa phải bộ eval trả lời/citation 30 câu.

## 1. Bộ test đề xuất: 30 câu hỏi

Khi xây bộ eval, tự soạn tay từng câu. Mỗi câu cần ghi rõ đáp án chuẩn **và** danh sách Điều/Khoản bắt
buộc phải được trích dẫn. Bộ 30 câu và tệp dưới đây chưa tồn tại trong kho mã.

Phân bổ:

| Loại | Số câu | Kiểm tra điều gì |
|---|---|---|
| A — Tra cứu trực tiếp | 12 | Retrieval cơ bản |
| B — Tổng hợp nhiều điều | 8 | Multi-hop, mở rộng dẫn chiếu |
| C — Có yếu tố thời gian | 5 | Temporal filter |
| D — Ngoài phạm vi | 5 | Hệ thống có biết từ chối không |

Loại D quan trọng: hỏi về thuế, đất đai, hoặc câu vô nghĩa. Hệ thống **phải** trả
lời "ngoài phạm vi", không được bịa.

### Định dạng dự kiến

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
đáp án chuẩn sai thì toàn bộ số liệu eval vô nghĩa. Không coi các giá trị ví dụ trong phần này là đáp án
đã được xác minh hoặc kết quả của một lần chạy eval.

## 2. Chỉ số đề xuất

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

Mục tiêu khi có Verifier: **0%**. Verifier chưa được triển khai, do đó chưa có tỷ lệ thực tế để báo cáo.

### 2.3 Out-of-Scope Accuracy

Tỷ lệ câu Loại D bị từ chối đúng cách. Mục tiêu 5/5.

### 2.4 Temporal Accuracy

Tỷ lệ câu Loại C trích đúng phiên bản văn bản theo mốc thời gian. Mục tiêu ≥ 4/5.

### 2.5 RAGAS (bổ trợ, chưa tích hợp)

- `faithfulness` — câu trả lời có bám vào context không
- `answer_relevancy` — có trả lời đúng câu hỏi không
- `context_precision` — chunk lấy về có liên quan không

RAGAS dùng LLM để chấm nên có nhiễu. Dùng làm tham khảo, không phải chỉ số chính. Thư viện này chưa
có trong dependencies và chưa có mã chạy RAGAS; nếu tích hợp, nên chạy nhiều lần rồi lấy trung bình.

## 3. Ablation Study (kế hoạch)

Chạy cùng bộ 30 câu qua 5 cấu hình sau khi có pipeline và bộ eval. Parser, ingest
Qdrant, dense retrieval, BM25, RRF và lọc thời gian đã có mã; Verifier và harness
đánh giá trả lời/citation vẫn chưa được triển khai. Baseline retrieval top-5 hiện
được lưu tại `data/processed/retrieval_baseline.json` để phát hiện hồi quy thứ hạng.

| # | Cấu hình | Mục đích |
|---|---|---|
| 1 | Baseline: LLM thuần, không RAG | Cho thấy RAG có cần thiết không |
| 2 | RAG đơn giản: chunk 512 ký tự, dense only | Baseline RAG thông thường |
| 3 | + chunking theo cấu trúc pháp lý | Đo giá trị của parser |
| 4 | + hybrid search (BM25 + RRF) | Đo giá trị của sparse |
| 5 | Full: + temporal filter + mở rộng dẫn chiếu + verifier | Hệ thống hoàn chỉnh |

### Bảng kết quả (chỉ điền sau khi triển khai và chạy eval)

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

Khi có eval, đọc **tất cả** các câu sai và phân loại nguyên nhân:

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

## 5. Kiểm soát chi phí khi chạy eval (kế hoạch)

- Khi tạo harness, cache response theo một khóa gồm model và prompt, tại một thư mục không theo dõi
  như `eval/cache/`.
- Chỉ ước lượng số request sau khi chốt số cấu hình, số câu và số lần gọi cho từng câu; hiện chưa có
  pipeline nào trong kho mã thực hiện các lời gọi này.
- Chọn model và cơ chế gọi API trong cấu hình của harness khi nó được xây dựng. Mã hiện tại chỉ dùng
  OpenAI Embeddings cho ingest, không có Planner, Synthesis hay lời gọi OpenAI Responses API.
