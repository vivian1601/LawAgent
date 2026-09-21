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
dung, lưu thành `.txt` hoặc `.html` trong `data/raw/`. Việc này mất khoảng 1 giờ và
tiết kiệm cho bạn nhiều ngày debug parser HTML.

## 2. Chốt danh sách văn bản (làm trong Tuần 1)

Các nghị định lao động thay đổi thường xuyên, nên tự xác minh thay vì tin vào số
hiệu ghi sẵn ở đâu đó:

1. Vào vbpl.vn, tìm "Bộ luật Lao động" → chọn bản đang có hiệu lực.
2. Ở trang chi tiết, xem mục **"Văn bản hướng dẫn"** hoặc **"Văn bản liên quan"** →
   đây là danh sách nghị định/thông tư hướng dẫn chính thức.
3. Dùng danh sách đã chốt tại `LEGAL_SOURCES.md`; kiểm tra lại trạng thái trước khi tải.
4. Với mỗi văn bản, ghi lại vào `data/manifest.yaml`: số hiệu, ngày ban hành, ngày
   có hiệu lực, trạng thái, văn bản bị thay thế (nếu có).

Với nghị định lương tối thiểu vùng, cố ý lấy **cả bản cũ đã hết hiệu lực** — đây là
nguyên liệu để demo tính năng xử lý hiệu lực theo thời gian (câu hỏi Loại C).

## 3. Cấu trúc thư mục

```
data/
├── manifest.yaml          # metadata cấp văn bản, tự điền tay
├── raw/                   # file tải về, giữ nguyên
│   ├── blld-2019.txt
│   └── ...
└── processed/
    └── chunks.jsonl       # đầu ra của parser
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

- **Một chunk = trọn một Điều.** Không bao giờ cắt giữa Điều.
- Nếu một Điều quá dài (> 2000 token, hiếm), tách theo Khoản nhưng **lặp lại phần
  tiêu đề Điều** ở đầu mỗi chunk con.
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

> Regex sẽ không đúng 100% ngay lần đầu. Viết một script `validate_parser.py` đếm số
> Điều parse được và so với số Điều thực tế của văn bản (Bộ luật Lao động 2019 có
> 220 Điều). Lặp cho tới khi khớp.

## 5. Metadata Schema

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
Dẫn chiếu sang văn bản khác giữ `target_document` và chờ temporal resolver chọn
đúng phiên bản theo ngày hỏi, tránh nối cứng vào một bản đã hết hiệu lực.

### Ba lưu ý quan trọng

1. **Embed `text_for_embedding`, không phải `text`.** Nhúng breadcrumb vào giúp
   truy vấn "quy định về hợp đồng lao động" khớp được với các Điều thuộc Chương
   Hợp đồng lao động, kể cả khi thân Điều không nhắc lại cụm từ đó.

2. **`hierarchy_level` là bắt buộc.** Đây là cơ sở để Synthesis Agent áp dụng
   nguyên tắc: văn bản cấp cao hơn thắng; cùng cấp thì ban hành sau thắng.

3. **`effective_to` cấp chunk, không chỉ cấp văn bản.** Một nghị định có thể chỉ bị
   bãi bỏ một phần. Mặc định kế thừa từ văn bản, nhưng cho phép ghi đè thủ công cho
   những Điều đặc biệt.

## 6. Cấu hình Qdrant

```python
from qdrant_client.models import VectorParams, Distance, PayloadSchemaType

EMBEDDING_DIMENSIONS = 1024

client.create_collection(
    collection_name="lexagent",
    vectors_config=VectorParams(size=EMBEDDING_DIMENSIONS, distance=Distance.COSINE),
)

# Index cho các field sẽ filter — bắt buộc, nếu không filter sẽ rất chậm
for field, schema in [
    ("status",          PayloadSchemaType.KEYWORD),
    ("doc_id",          PayloadSchemaType.KEYWORD),
    ("hierarchy_level", PayloadSchemaType.INTEGER),
    ("effective_from",  PayloadSchemaType.DATETIME),
    ("effective_to",    PayloadSchemaType.DATETIME),
]:
    client.create_payload_index("lexagent", field, schema)
```

Dense vector được tạo bằng OpenAI Embeddings API. Giữ `dimensions` và kích thước
vector của Qdrant cùng một giá trị; nếu thay đổi phải tạo lại collection và reindex.

```python
import os
from openai import OpenAI

openai_client = OpenAI()

def embed_texts(texts: list[str]) -> list[list[float]]:
    response = openai_client.embeddings.create(
        model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"),
        input=texts,
        dimensions=EMBEDDING_DIMENSIONS,
    )
    return [item.embedding for item in response.data]
```

### Truy vấn có lọc theo thời điểm

```python
def build_temporal_filter(as_of: date) -> Filter:
    """Chỉ lấy chunk có hiệu lực tại thời điểm as_of."""
    return Filter(must=[
        FieldCondition(key="effective_from", range=DatetimeRange(lte=as_of)),
    ], should=[
        IsNullCondition(is_null=PayloadField(key="effective_to")),
        FieldCondition(key="effective_to", range=DatetimeRange(gte=as_of)),
    ], min_should=1)
```

## 7. Hybrid search

Tìm kiếm ngữ nghĩa thuần sẽ trượt khi người dùng gõ đúng số điều ("Điều 35 quy định
gì?"). Kết hợp:

- **Dense**: OpenAI `text-embedding-3-large` (1024 chiều), top-k = 10
- **Sparse**: BM25 trên `text_for_embedding` (dùng `rank_bm25`, corpus nhỏ nên đủ nhanh)
- **Gộp**: Reciprocal Rank Fusion, `score = Σ 1/(60 + rank_i)`
- **Lấy** top 5 sau khi fuse → mở rộng dẫn chiếu 1 tầng → tối đa 8 chunk vào context

Không cần cross-encoder rerank ở giai đoạn này. Nếu còn thời gian ở Tuần 6 thì thêm
và đo xem có cải thiện không — đó là một dòng hay trong phần kết quả.
