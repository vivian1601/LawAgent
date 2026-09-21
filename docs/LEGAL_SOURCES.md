# LEGAL SOURCES — Corpus pháp luật lao động

> Chốt nguồn ngày **18/09/2026**. Đây là danh mục phục vụ xây dựng và đánh giá
> LawAgent, không phải tư vấn pháp lý.

## 1. Quyết định phạm vi

MVP trả lời câu hỏi của **người lao động làm việc theo hợp đồng tại Việt Nam**,
theo hành trình: nhận việc → làm việc → nghỉ việc → tranh chấp. Phạm vi này đủ gần
với nhu cầu cá nhân để hữu ích, nhưng vẫn đủ hẹp cho dự án 6 tuần.

Không đưa toàn bộ BHXH, BHTN, công đoàn và an toàn lao động vào cùng MVP. Mỗi
lĩnh vực có hệ thống điều kiện hưởng, hồ sơ, thời hạn và văn bản hướng dẫn riêng;
thêm chúng ngay sẽ làm bộ eval loãng và khó chứng minh độ chính xác.

## 2. Corpus MVP bắt buộc

| ID | Văn bản | Hiệu lực cần mô hình hóa | Dùng để trả lời | Nguồn chính thức |
|---|---|---|---|---|
| `45/2019/QH14` | Bộ luật Lao động (bản gốc) | Phiên bản lịch sử 01/01/2021–31/12/2025 trong corpus | Tra cứu lịch sử | [Công báo](https://congbao.chinhphu.vn/van-ban/nghi-quyet-so-45-2019-qh14-30232.htm) |
| `18/VBHN-VPQH` | Bộ luật Lao động (hợp nhất 2026) | Bản dùng cho tra cứu hiện hành | Toàn bộ quyền và nghĩa vụ nền tảng | [Cổng Chính phủ](https://vanban.chinhphu.vn/?classid=0&docid=217002&pageid=27160) |
| `145/2020/NĐ-CP` | Hướng dẫn điều kiện lao động và quan hệ lao động | Từ 01/02/2021; đã bị sửa đổi/bãi bỏ một phần | Hợp đồng, trợ cấp, thời giờ nghỉ, lao động nữ, quấy rối, kỷ luật, tranh chấp | [VBPL](https://vbpl.vn/TW/Pages/ivbpq-thuoctinh.aspx?ItemID=152668) |
| `38/2022/NĐ-CP` | Lương tối thiểu | 01/07/2022–30/06/2024 | Câu hỏi lịch sử năm 2022–2024 | [VBPL](https://vbpl.vn/TW/Pages/vbpq-thuoctinh.aspx?ItemID=154245) |
| `74/2024/NĐ-CP` | Lương tối thiểu | 01/07/2024–31/12/2025 | Câu hỏi lịch sử năm 2024–2025 | [VBPL](https://vbpl.vn/TW/Pages/ivbpq-thuoctinh.aspx?ItemID=168670) |
| `293/2025/NĐ-CP` | Lương tối thiểu | Từ 01/01/2026 | Mức lương tối thiểu hiện hành | [VBPL](https://vbpl.vn/TW/Pages/vbpq-thuoctinh.aspx?ItemID=183939) |
| `12/2022/NĐ-CP` | Xử phạt vi phạm hành chính về lao động | 17/01/2022–09/09/2026 | Tra cứu chế tài lịch sử | [Công báo](https://congbao.chinhphu.vn/van-ban/nghi-dinh-so-12-2022-nd-cp-36716.htm) |
| `283/2026/NĐ-CP` | Xử phạt vi phạm hành chính về lao động | Từ 10/09/2026 | Chế tài hiện hành; thay NĐ 12/2022 | [Cổng Chính phủ](https://vanban.chinhphu.vn/?classid=1&docid=218871&pageid=27160&typegroupid=4) |

### Patch bắt buộc cho Nghị định 145/2020/NĐ-CP

CSDL VBPL xác định Nghị định 145 đã bị tác động bởi:

- `35/2022/NĐ-CP` — quản lý khu công nghiệp và khu kinh tế;
- `10/2024/NĐ-CP` — khu công nghệ cao;
- `129/2025/NĐ-CP` — phân định thẩm quyền chính quyền địa phương hai cấp.

Ba văn bản này chủ yếu đổi thẩm quyền và thủ tục quản lý. Không cần embed toàn văn
vào corpus hỏi đáp quyền lợi cá nhân; cần ingest các điều sửa đổi như **patch** để
đóng/mở hiệu lực đúng ở cấp chunk. Nếu chưa cài patch, phải loại các chunk bị tác
động khỏi câu trả lời hiện hành.

## 3. Các chủ đề MVP phải trả lời được

| Chủ đề | Ví dụ câu hỏi |
|---|---|
| Hợp đồng và thử việc | “Công ty được thử việc tôi tối đa bao lâu và phải trả ít nhất bao nhiêu phần trăm lương?” |
| Tiền lương | “Công ty chậm trả lương thì tôi có được nhận thêm tiền không?” |
| Làm thêm và làm đêm | “Làm Chủ nhật và ban đêm được tính lương thế nào?” |
| Nghỉ ngơi | “Tôi làm đủ 12 tháng thì có bao nhiêu ngày phép năm?” |
| Bình đẳng và quấy rối | “Nội quy công ty phải quy định gì về quấy rối tình dục tại nơi làm việc?” |
| Kỷ luật | “Công ty có được phạt tiền hoặc cắt lương thay cho kỷ luật không?” |
| Chấm dứt hợp đồng | “Tôi muốn nghỉ việc thì phải báo trước bao lâu?” |
| Quyền lợi khi nghỉ | “Khi nghỉ việc, công ty phải thanh toán và trả giấy tờ trong bao lâu?” |
| Tranh chấp | “Tranh chấp sa thải có bắt buộc qua hòa giải trước khi kiện không?” |
| Hiệu lực theo thời gian | “Lương tối thiểu vùng I tháng 3/2023 khác tháng 3/2026 thế nào?” |

### Ngoài phạm vi phải từ chối rõ

- Tính chính xác số tiền được hưởng khi thiếu lương, vùng, lịch làm việc hoặc thâm niên.
- Kết luận ai đúng/sai trong một vụ việc cụ thể hoặc đề xuất chiến thuật kiện tụng.
- Công chức, viên chức; lao động nước ngoài; đi làm việc ở nước ngoài; thuế TNCN.
- BHXH, BHYT, BHTN, tai nạn lao động và công đoàn trong bản MVP.

## 4. Corpus mở rộng sau MVP

Chỉ mở rộng khi bộ eval MVP đã ổn định:

1. **Quyền lợi bảo hiểm xã hội:** Luật BHXH `41/2024/QH15` và Nghị định
   `158/2025/NĐ-CP` về BHXH bắt buộc ([Luật](https://vanban.chinhphu.vn/?docid=211199&pageid=27160),
   [Nghị định](https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=178757)).
2. **Bảo hiểm thất nghiệp và hỗ trợ việc làm:** Luật Việc làm `74/2025/QH15`,
   hiệu lực 01/01/2026 ([VBPL](https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=179273)).
3. **Tai nạn lao động, bệnh nghề nghiệp:** Luật An toàn, vệ sinh lao động
   `84/2015/QH13` ([VBPL](https://vbpl.vn/TW/Pages/vbpq-thuoctinh.aspx?ItemID=70811)).
4. **Đại diện và bảo vệ tập thể:** Luật Công đoàn `50/2024/QH15`, hiệu lực
   01/07/2025 ([VBPL](https://vbpl.vn/TW/Pages/vbpq-toanvan.aspx?ItemID=172553)).

Mỗi nhóm mở rộng nên là một collection hoặc namespace riêng và có bộ câu hỏi eval
riêng; router chọn lĩnh vực trước khi retrieval.

## 5. Quy tắc xác minh nguồn

1. Nguồn ưu tiên: `vbpl.vn` → `vanban.chinhphu.vn`/Công báo → nguồn đối chiếu.
2. Lưu cả file gốc, URL trang thuộc tính, ngày tải và SHA-256 của file.
3. Không suy ra hiệu lực chỉ từ nhãn trạng thái. Đọc mục lịch sử và điều khoản
   hiệu lực của chính văn bản thay thế/sửa đổi.
4. Với văn bản “hết hiệu lực một phần”, metadata phải ở cấp Điều/chunk; không gán
   `effective_to` cho toàn bộ tài liệu.
5. Ghi `verified_at: 2026-09-18`; UI phải hiển thị ngày chốt dữ liệu.

### Trường hợp kiểm thử chất lượng metadata

CSDL VBPL có lúc hiển thị Luật BHXH `41/2024/QH15` như bị Luật Việc làm
`74/2025/QH15` thay thế toàn bộ. Tuy nhiên Điều 54 Luật Việc làm chỉ quy định
Luật Việc làm `38/2013/QH13` (đã được Luật BHXH sửa đổi một phần) hết hiệu lực.
Đây là ví dụ tốt để thêm test: parser quan hệ pháp lý không được đồng nhất
“văn bản A sửa văn bản B” với “A là chính B”.

## 6. Checklist tải dữ liệu

- [ ] Tải bản `.doc`/`.docx` nếu có để lấy text; giữ PDF ký số làm bản đối chiếu.
- [ ] Đặt tên `doc_id__issued_date.ext`, không đặt tên chỉ theo tiêu đề.
- [ ] Điền đủ sáu văn bản vào `data/manifest.yaml`.
- [ ] Tạo patch record cho các điều của Nghị định 145 bị tác động.
- [ ] Đối chiếu số Điều parse được với mục lục của văn bản.
- [ ] Lấy mẫu 10 Điều có Khoản/Điểm phức tạp để kiểm tra thủ công.
- [ ] Chạy câu hỏi cùng nội dung ở ba mốc 2023, 2025 và 2026.
