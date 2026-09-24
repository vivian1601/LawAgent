# SCOPE — Phạm vi dự án

> Mỗi khi muốn thêm tính năng, đọc lại mục “Không làm” trước.

## 1. Nguyên tắc

Dự án cá nhân, ước tính **8–10 giờ/tuần trong 6 tuần**. Mục tiêu không phải phủ
toàn bộ pháp luật Việt Nam mà là một lát cắt hẹp được làm kỹ, có demo chạy được,
có số liệu đánh giá và có README trung thực về giới hạn.

## 2. Phạm vi dữ liệu

Chỉ **quyền của người lao động làm việc theo hợp đồng tại Việt Nam**. Corpus MVP
gồm 4 nhóm tài liệu, tương ứng 8 phiên bản văn bản:

| Nhóm | Văn bản | Vai trò |
|---|---|---|
| Luật nền | Bộ luật Lao động 45/2019/QH14 và VBHN 18/VBHN-VPQH | Bản lịch sử và bản hợp nhất hiện hành về hợp đồng, lương, nghỉ, kỷ luật, chấm dứt và tranh chấp |
| Hướng dẫn | Nghị định 145/2020/NĐ-CP | Cách áp dụng quyền và nghĩa vụ trong quan hệ lao động |
| Lương tối thiểu | Nghị định 38/2022/NĐ-CP, 74/2024/NĐ-CP và 293/2025/NĐ-CP | Ba phiên bản nối tiếp để kiểm thử truy vấn theo thời gian |
| Chế tài | Nghị định 12/2022/NĐ-CP và 283/2026/NĐ-CP | Chế tài theo mốc trước/sau 10/09/2026 |

Danh sách được chốt ngày **18/09/2026**. Nguồn chính thức, trạng thái hiệu lực,
văn bản sửa đổi và hướng dẫn ingest nằm tại `docs/LEGAL_SOURCES.md`.

Nghị định 145/2020/NĐ-CP đã bị sửa đổi/bãi bỏ một phần. Pipeline không được coi
toàn bộ bản gốc là pháp luật hiện hành mà phải áp dụng patch được ghi trong
manifest. Quy mô thực tế 724 chunk, đủ nhỏ để chạy local nhưng vẫn có độ khó
retrieval thực tế.

## 3. Phạm vi câu hỏi hỗ trợ

### Hành trình quyền lợi được ưu tiên

1. Trước khi nhận việc: tuyển dụng, thử việc, nội dung phải có trong hợp đồng.
2. Trong khi làm việc: lương tối thiểu, kỳ hạn trả lương, làm thêm/ban đêm, nghỉ
   hằng tuần, nghỉ lễ và nghỉ phép năm.
3. Bảo vệ tại nơi làm việc: bình đẳng, quấy rối tình dục, lao động nữ, kỷ luật và
   trách nhiệm vật chất.
4. Khi nghỉ việc hoặc bị cho nghỉ: quyền đơn phương chấm dứt, thời hạn báo trước,
   trợ cấp thôi việc/mất việc, thanh toán và trả giấy tờ.
5. Khi có tranh chấp: thời hiệu, hòa giải, trọng tài/Tòa án và chế tài hành chính.

### Ba loại câu hỏi

- **Loại A — Tra cứu trực tiếp.** “Thời gian thử việc tối đa với vị trí quản lý là
  bao lâu?” → một Điều trả lời được.
- **Loại B — Tổng hợp nhiều điều.** “Người sử dụng lao động được đơn phương chấm
  dứt hợp đồng khi nào và phải báo trước bao lâu?” → cần gộp 2–3 Điều.
- **Loại C — Có yếu tố thời gian.** “Mức lương tối thiểu vùng I áp dụng tháng
  3/2023 là bao nhiêu?” → phải chọn đúng phiên bản nghị định.

Với câu hỏi phụ thuộc địa bàn, loại hợp đồng, thâm niên hoặc diễn biến sự việc mà
người dùng chưa cung cấp, hệ thống phải hỏi lại dữ kiện thay vì tự suy đoán.

## 4. Không làm

- Không mở rộng sang thuế, đất đai, doanh nghiệp hoặc pháp luật hình sự.
- Không trả lời trong MVP về BHXH, BHYT, BHTN, công đoàn, an toàn vệ sinh lao
  động hoặc người lao động Việt Nam đi làm việc ở nước ngoài. Đây là corpus mở
rộng sau MVP, xem `docs/LEGAL_SOURCES.md`.
- Không tích hợp án lệ/bản án hoặc xử lý văn bản scan/OCR.
- Không tự động crawl định kỳ; ingest thủ công và chốt ngày dữ liệu.
- Không xây knowledge graph đầy đủ; chỉ mở rộng dẫn chiếu một tầng.
- Không làm agent “tư vấn” hoặc đề xuất chiến thuật pháp lý; chỉ trình bày quy định.
- Không fine-tune model, deploy production, làm auth/multi-user, mobile app hoặc
  public API.

## 5. Giới hạn đã biết

1. Corpus chỉ có 4 nhóm/8 phiên bản văn bản; câu hỏi ngoài phạm vi phải trả lời
   “không tìm thấy căn cứ trong corpus”. Đây là hành vi cố ý.
2. Chưa xử lý đầy đủ xung đột giữa hai văn bản cùng cấp.
3. Dẫn chiếu sâu quá một tầng có thể bị bỏ sót.
4. Trạng thái hiệu lực được chốt tại thời điểm ingest, không tự cập nhật.
5. Kết quả không phải tư vấn pháp lý.

## 6. Định nghĩa “xong”

- [x] Ingest được 8 phiên bản văn bản; parser giữ đúng cấu trúc Điều/Khoản.
- [x] Tạo collection Qdrant, sinh 724 vector và triển khai BM25 cho truy vấn từ
      khóa/số Điều.
- [x] Hoàn thiện dense search, RRF, temporal filter và CLI top-5 của Giai đoạn 2.
- [ ] Pipeline 3 agent chạy end-to-end trên LangGraph; Planner và Synthesis gọi
      OpenAI Responses API.
- [ ] Citation verifier không để lọt trích dẫn bịa.
- [ ] Bộ 30 câu hỏi eval có kết quả đo được trong `docs/EVALUATION.md`.
- [ ] README có kiến trúc, số liệu, ngày chốt corpus và mục Limitations.

Không cần UI đẹp, Docker Compose hoàn hảo hoặc test coverage 80%.
