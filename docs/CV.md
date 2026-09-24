# CV — Cách trình bày dự án & chuẩn bị phỏng vấn

> **Trạng thái hiện tại:** Giai đoạn 1 và Giai đoạn 2 đã hoàn thành. Qdrant chứa
> 724 vector; dense search, BM25, RRF, temporal filter và CLI end-to-end đã được
> kiểm chứng bằng 24 test và baseline retrieval 10/10 top-1. Các đoạn có dấu `__`
> bên dưới vẫn chỉ được dùng sau khi có số liệu đánh giá trả lời/citation.

## 1. Mục dự án trong CV

Giữ 3–4 dòng. Nhấn vào **quyết định kỹ thuật** và **số liệu**, không phải danh sách
công nghệ.

### Mẫu mục tiêu (chỉ dùng sau khi chạy eval)

> **LexAgent — Multi-Agent RAG cho pháp luật lao động Việt Nam**
> *Python, LangGraph, Qdrant, OpenAI Responses API · [github.com/...]*
> Xây dựng hệ thống hỏi đáp pháp luật với pipeline 3 agent, giải quyết hai vấn đề
> đặc thù của domain: chunking theo cấu trúc phân cấp Chương–Điều–Khoản thay vì cắt
> theo độ dài, và lọc theo thời điểm hiệu lực của văn bản. Thiết kế lớp citation
> verifier bằng code xác định, đưa tỷ lệ trích dẫn bịa từ __% xuống 0%. Đánh giá
> bằng ablation study trên bộ 30 câu hỏi tự xây, Citation F1 đạt __.

### Tránh viết

- ❌ "Sử dụng LangChain, OpenAI, Pinecone để xây chatbot RAG" — ai cũng viết được
- ❌ "Ứng dụng AI vào lĩnh vực pháp lý" — mơ hồ
- ❌ Liệt kê 15 công nghệ — loãng

## 2. Cấu trúc README trên GitHub

README là thứ nhà tuyển dụng thực sự đọc. Thứ tự:

1. **Một dòng mô tả** + GIF demo ngay đầu
2. **Vấn đề** — nêu con số từ ablation cấu hình 1 (LLM thuần bịa citation bao nhiêu %)
3. **Kiến trúc** — sơ đồ ASCII hoặc Mermaid
4. **Quyết định thiết kế** — 3 mục, mỗi mục: vấn đề → giải pháp → kết quả đo
5. **Kết quả** — bảng ablation
6. **Error Analysis** — bảng phân loại lỗi
7. **Limitations & Future Work** — trung thực
8. **Cách chạy**

Mục 4 và 7 là hai mục ít người viết nhất, và là hai mục tạo ấn tượng mạnh nhất.

## 3. Câu hỏi phỏng vấn thường gặp & hướng trả lời

**"Tại sao không dùng chunking mặc định?"**
→ Văn bản pháp luật có cấu trúc phân cấp mang ý nghĩa ngữ nghĩa. Cắt theo ký tự sẽ
tách Khoản khỏi Điều, khiến câu trả lời trích dẫn sai đơn vị. Đo được: cấu hình 2
vs 3 trong ablation cho thấy Citation F1 chênh __.

**"Tại sao chỉ 3 agent, không phải 5–6?"**
→ Kiểm tra hiệu lực văn bản và truy vết dẫn chiếu là logic xác định, giải quyết bằng
metadata filter và tra cứu index. Dùng LLM cho việc này chỉ thêm độ trễ, chi phí, và
một chỗ nữa để sai. Nguyên tắc tôi áp dụng: chỉ dùng LLM ở chỗ cần phán đoán ngôn ngữ.

**"Làm sao chống hallucination?"**
→ Ba lớp: prompt ràng buộc chỉ dùng context; citation verifier bằng code đối chiếu
mọi mã trích dẫn với corpus; vòng retry một lần khi phát hiện sai. Lớp thứ hai là
quan trọng nhất vì nó xác định, không phụ thuộc vào việc LLM có "nghe lời" không.

**"Hệ thống sai ở đâu?"**
→ Dẫn chiếu sâu quá một tầng bị bỏ sót. Corpus nhỏ nên chưa xử lý xung đột giữa hai
văn bản cùng cấp. Trạng thái hiệu lực chốt tại thời điểm ingest, không tự cập nhật.
(Trả lời được câu này tốt hơn là giả vờ hệ thống hoàn hảo.)

**"Nếu scale lên toàn bộ pháp luật Việt Nam thì sao?"**
→ Ba thứ phải đổi: cần routing theo lĩnh vực trước khi retrieve; cần knowledge graph
đầy đủ cho dẫn chiếu thay vì mở rộng 1 tầng; cần pipeline cập nhật tự động theo dõi
văn bản mới trên vbpl.vn. Và cần chuyên gia pháp lý review bộ eval.

## 4. Chuẩn bị demo 3 phút

Kịch bản:

1. (20s) Nêu vấn đề: hỏi ChatGPT/Claude thuần một câu luật lao động → cho thấy nó
   trích dẫn số điều không tồn tại
2. (40s) Hỏi cùng câu trên LexAgent → chỉ vào citation, click mở xem nguyên văn Điều
3. (60s) Hỏi câu Loại C với hai mốc thời gian khác nhau → cho thấy hệ thống trả về
   hai nghị định khác nhau. **Đây là khoảnh khắc ấn tượng nhất, đừng bỏ qua.**
4. (30s) Mở expander "Chi tiết truy vấn" → cho thấy hệ thống minh bạch
5. (30s) Mở bảng ablation trên README

## 5. Lưu ý

- Repo phải **public** và chạy được. Nhà tuyển dụng có thể thử clone.
- Đừng commit API key. Dùng `.env` và commit `.env.example`.
- Nếu bị hỏi "ai làm phần nào" — đây là dự án cá nhân, nói rõ bạn làm toàn bộ, và
  nói rõ phần nào bạn tham khảo tài liệu/AI hỗ trợ. Trung thực về điều này an toàn
  hơn nhiều so với bị phát hiện.
