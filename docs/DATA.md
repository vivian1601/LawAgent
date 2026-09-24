# DATA — Nguồn dữ liệu, Ingest Pipeline & Metadata Schema

## 1. Nguồn dữ liệu

| Nguồn | URL | Dùng cho | Ghi chú |
|---|---|---|---|
| CSDL quốc gia về văn bản pháp luật | vbpl.vn | **Nguồn chính** | Cơ quan nhà nước vận hành. Có mục "Văn bản hợp nhất" và thông tin hiệu lực, văn bản sửa đổi/thay thế. |
| Thư viện pháp luật | thuvienphapluat.vn | Đối chiếu | Dịch vụ thương mại — đọc kỹ điều khoản sử dụng trước khi tải hàng loạt. Chỉ dùng để kiểm tra chéo thủ công. |
| Công báo | congbao.chinhphu.vn | Bản PDF gốc | Dùng khi cần xác minh nội dung nghi ngờ. |

**Ưu tiên bản "Văn bản hợp nhất"** khi có. Bản hợp nhất đã gộp sẵn các lần sửa đổi,
giúp bạn tránh phải tự xử lý logic "điều này đã bị sửa bởi văn bản kia".

### Về việc tải dữ liệu

Corpus MVP có 8 phiên bản văn bản → **tải thủ công**. Đừng viết crawler. Mở trang, copy phần nội
dung, lưu thành `.txt` (hoặc `.docx` nếu có) trong `data/raw/` để làm đầu vào cho parser. Có thể giữ
PDF/HTML gốc trong cùng thư mục để đối chiếu. Việc này mất khoảng 1 giờ và
tiết kiệm cho bạn nhiều ngày debug parser HTML.

## 2. Chốt danh sách văn bản (hoàn thành trong Giai đoạn 1)

Các nghị định lao động thay đổi thường xuyên, nên tự xác minh thay vì tin vào số
hiệu ghi sẵn ở đâu đó:

1. Vào vbpl.vn, tìm "Bộ luật Lao động" → chọn bản đang có hiệu lực.
2. Ở trang chi tiết, xem mục **"Văn bản hướng dẫn"** hoặc **"Văn bản liên quan"** →
   đây là danh sách nghị định/thông tư hướng dẫn chính thức.
3. Dùng danh sách đã chốt tại `docs/LEGAL_SOURCES.md`; kiểm tra lại trạng thái trước khi tải.
4. Với mỗi văn bản, ghi lại vào `data/manifest.yaml`: số hiệu, ngày ban hành, ngày
   có hiệu lực, trạng thái, văn bản bị thay thế (nếu có).

Với nghị định lương tối thiểu vùng, cố ý lấy **cả bản cũ đã hết hiệu lực** — đây là
nguyên liệu cho tính năng xử lý hiệu lực theo thời gian ở giai đoạn sau (câu hỏi Loại C).

## 3. Cấu trúc thư mục

```
data/
├── manifest.yaml          # metadata cấp văn bản, tự điền tay
├── raw/                   # file tải về, giữ nguyên
│   ├── blld-2019.txt
│   └── ...
└── processed/
    └── chunks.jsonl       # đầu ra hiện tại: 724 chunk của 702 Điều
```

## 4. Parser — chunking theo cấu trúc pháp lý

Đây là phần kỹ thuật cốt lõi. **Không dùng `RecursiveCharacterTextSplitter`.**

### Cấu trúc phân cấp cần nhận diện

```
Phần  →  Chương  →  Mục  →  Điều  →  Khoản  →  Điểm
                              ▲
                         đơn vị chunk
```

### Quy tắc chunk

- **Mặc định một chunk = trọn một Điều.**
- Khi Điều dài hơn 8.000 ký tự, parser tách ưu tiên theo Khoản; nếu không tách được theo Khoản thì
  tách theo cửa sổ ký tự. Mỗi phần sau phần đầu đều lặp lại tiêu đề Điều.
- Mỗi chunk mang breadcrumb đầy đủ để LLM biết ngữ cảnh phân cấp.

### Regex nhận diện (gợi ý khởi điểm)

```python
PATTERNS = {
    "chuong": r"^Chương\s+([IVXLC]+)\s*\n?\s*(.*)$",
    "muc":    r"^Mục\s+(\d+)\s*\n?\s*(.*)$",
    "dieu":   r"^Điều\s+(\d+)\.\s*(.*)$",
    "khoan":  r"^(\d+)\.\s+",
    "diem":   r"^([a-zđ])\)\s+",
}

# Dẫn chiếu tới điều khoản khác
REFERENCE = r"(?:khoản\s+(\d+)\s+)?Điều\s+(\d+)(?:\s+của\s+(.+?))?(?=[,.;)]|\s+thì|\s+được|$)"
```

> Regex sẽ không đúng 100% ngay lần đầu. Dùng `scripts/validate_parser.py` để đếm số
> Điều parse được và so với số Điều thực tế của văn bản (Bộ luật Lao động 2019 có
> 220 Điều). Lặp cho tới khi khớp.

## 5. Metadata Schema (thiết kế dữ liệu)

Đoạn Pydantic dưới đây là schema mục tiêu để diễn giải metadata, không phải mã đang được thực thi;
parser hiện dùng dataclass `LegalChunk`.

Chốt schema này trước khi ingest — sửa sau sẽ phải reindex toàn bộ.

```python
from datetime import date
from typing import Literal
from pydantic import BaseModel

class LegalChunk(BaseModel):
    # --- Định danh ---
    chunk_id: str              # "45-2019-QH14__dieu_24"
    doc_id: str                # "45/2019/QH14"
    doc_title: str             # "Bộ luật Lao động"

    # --- Thứ bậc pháp lý: dùng để giải quyết xung đột ---
    doc_type: Literal["bo_luat", "luat", "nghi_dinh", "thong_tu"]
    hierarchy_level: int       # 1=Luật/Bộ luật, 2=Nghị định, 3=Thông tư

    # --- Vị trí trong văn bản ---
    chuong: str | None         # "III"
    chuong_title: str | None   # "Hợp đồng lao động"
    muc: str | None
    dieu_number: int           # 24
    dieu_title: str            # "Thử việc"
    breadcrumb: str            # "Bộ luật Lao động 2019 > Chương III > Mục 2 > Điều 24. Thử việc"

    # --- Hiệu lực theo thời gian ---
    effective_from: date
    effective_to: date | None  # None = còn hiệu lực
    status: Literal["con_hieu_luc", "het_hieu_luc_mot_phan", "het_hieu_luc", "chua_co_hieu_luc"]

    # --- Dẫn chiếu ---
    references: list[LegalReference]

    # --- Nội dung ---
    text: str                  # nội dung Điều, đã làm sạch
    text_for_embedding: str    # breadcrumb + "\n\n" + text
```

`LegalReference` giữ cả ý nghĩa pháp lý và vị trí chính xác, thay vì chỉ giữ ID
của Điều:

```python
class LegalReference(BaseModel):
    relation: Literal["applies", "exception", "exclusion", "amendment", "repeal"]
    target_doc_id: str | None
    target_document: str | None       # tên văn bản khi cần resolver theo thời gian
    target_article: str
    target_clause: str | None
    target_point: str | None
    target_chunk_id: str | None       # chỉ có khi phân giải nội bộ được
    resolved: bool
    raw_text: str
```

Ví dụ `trừ trường hợp quy định tại điểm a khoản 2 Điều 35` được lưu với
`relation="exception"`, `target_clause="2"`, `target_point="a"`. Retriever phải
lấy thêm đúng Điểm/Khoản đích; không được trả lời quy tắc chính mà bỏ qua ngoại lệ.
Dẫn chiếu sang văn bản khác giữ `target_document` để một temporal resolver trong tương lai có thể
chọn phiên bản theo ngày hỏi, tránh nối cứng vào một bản đã hết hiệu lực. Parser hiện chỉ phân giải
dẫn chiếu nội bộ tới chunk có trong cùng văn bản; dẫn chiếu liên văn bản được giữ là chưa phân giải.

### Trạng thái metadata hiện có

Parser hiện ghi JSONL từ dataclass `LegalChunk` trong `src/lawagent/parser.py`. Ngoài các trường nêu
trên, bản ghi thực tế còn có `muc_title`, `dieu_label`, `source_url` và `source_file`. Báo cáo
`data/processed/validation_report.json` xác nhận 8 văn bản, 702 Điều và 724 chunk; các kiểm tra cũng
xác nhận không có `chunk_id` trùng hoặc dẫn chiếu nội bộ bị treo.

`effective_from`, `effective_to` và `status` hiện được sao chép từ metadata cấp văn bản trong
`data/manifest.yaml` vào từng chunk. Mã chưa hỗ trợ ghi đè hiệu lực theo từng chunk và chưa áp dụng
`patch_documents` để thay đổi hiệu lực của các Điều bị sửa đổi.

### Ba lưu ý quan trọng

1. **Embed `text_for_embedding`, không phải `text`.** Nhúng breadcrumb vào giúp
   truy vấn "quy định về hợp đồng lao động" khớp được với các Điều thuộc Chương
   Hợp đồng lao động, kể cả khi thân Điều không nhắc lại cụm từ đó.

2. **`hierarchy_level` là bắt buộc.** Đây là dữ liệu cần có để một bước tổng hợp sau này áp dụng
nguyên tắc: văn bản cấp cao hơn thắng; cùng cấp thì ban hành sau thắng. Chưa có Synthesis Agent
thực hiện quy tắc này trong mã hiện tại.

3. **`effective_to` nên có ở cấp chunk, không chỉ cấp văn bản.** Một nghị định có thể chỉ bị
bãi bỏ một phần. Đây là hướng mở rộng cần thiết; hiện tại parser mới kế thừa giá trị cấp văn bản.

## 6. Ingest Qdrant và embedding (đã có mã)

`src/lawagent/index.py` hiện có `ensure_collection()`: nếu collection chưa tồn tại, hàm tạo vector
Cosine với `EMBEDDING_DIMENSIONS` và tạo payload index cho `status`, `doc_id`, `hierarchy_level`,
`effective_from` và `effective_to`. Collection đã tồn tại chỉ được kiểm tra/tạo payload index còn
thiếu; mã không di trú kích thước vector của collection đó.

`src/lawagent/ingest.py` hiện có pipeline ingest: đọc `data/processed/chunks.jsonl`, tạo ID UUID5 ổn
định từ `chunk_id`, bỏ qua điểm đã có, gửi các batch tối đa 32 `text_for_embedding` tới OpenAI
Embeddings API, rồi upsert vector và payload vào Qdrant. Payload đổi hai trường ngày sang RFC 3339 và
ghi lại model cùng số chiều embedding.

Việc ingest phụ thuộc Qdrant đang chạy và `OPENAI_API_KEY`; kho mã chỉ chứng minh pipeline đã được
cài đặt, không chứng minh một Qdrant instance cụ thể đã chứa corpus. Giữ `OPENAI_EMBEDDING_MODEL` và
`EMBEDDING_DIMENSIONS` tương thích với nhau. Khi đổi số chiều, dùng collection mới hoặc có kế hoạch
di trú/reindex, vì collection có sẵn không được thay đổi kích thước tự động.

### Lọc theo thời điểm

Các trường thời gian và payload index được dùng trực tiếp bởi
`src/lawagent/temporal_filter.py`. Nhánh BM25 lọc corpus cục bộ bằng
`filter_effective_chunks()`; nhánh dense dùng `build_temporal_filter()` để áp dụng
cùng điều kiện tại Qdrant: `effective_from <= as_of` và `effective_to` rỗng hoặc
`effective_to >= as_of`.

## 7. BM25 sparse retrieval (đã có mã)

`src/lawagent/sparse.py` xây dựng `BM25Index` trên `text_for_embedding` của `chunks.jsonl` bằng
`rank_bm25`. Nó chuẩn hóa Unicode NFC, chuyển về chữ thường và token hóa truy vấn; với truy vấn dạng
`Điều <số>`, kết quả đúng `dieu_label` được ưu tiên, sau đó ưu tiên văn bản có `hierarchy_level` cao
hơn trước điểm BM25. Các kiểm thử trong `tests/test_sparse.py` kiểm tra token hóa tiếng Việt, truy
vấn Điều 35 và truy vấn về thời gian thử việc.

Chạy BM25 độc lập từ thư mục gốc dự án:

```powershell
uv run python -m lawagent.sparse "Điều 35"
```

## 8. Tích hợp truy vấn hybrid

`src/lawagent/dense.py` tạo embedding truy vấn và tìm Qdrant; `src/lawagent/search.py`
hợp nhất dense/BM25 bằng RRF (`k=60`) sau khi lọc thời gian. CLI `lawagent-search`
trả top-5 kèm điểm và nguồn. `src/lawagent/baseline.py` chạy 10 truy vấn hồi quy;
snapshot tại `data/processed/retrieval_baseline.json` hiện đạt 10/10 top-1.

`src/lawagent/references.py` đã có tiện ích lấy đúng Khoản/Điểm cho dẫn chiếu nội
bộ, nhưng chưa được nối vào `HybridSearcher`. Mở rộng dẫn chiếu, cross-encoder
rerank và đánh giá trả lời/citation thuộc các giai đoạn sau.
