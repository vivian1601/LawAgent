<!-- generated-by: gsd-doc-writer -->
# Phát triển LawAgent

Tài liệu này dành cho người phát triển corpus pháp luật lao động Việt Nam và các lớp truy xuất của LawAgent: BM25, dense retrieval qua Qdrant/OpenAI, Reciprocal Rank Fusion (RRF), lọc hiệu lực theo thời điểm, và baseline hồi quy. Dự án chưa có dịch vụ hỏi–đáp, giao diện web hoặc pipeline agent chạy được.

## Thiết lập cục bộ

Cần có Python `>=3.11`, [uv](https://docs.astral.sh/uv/) và Docker Desktop để chạy Qdrant. Cài dependency chạy và dependency phát triển, rồi tạo cấu hình cục bộ nếu chưa có:

```powershell
uv sync --extra dev
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Các bước parser, validation, BM25 và pytest chỉ dùng dữ liệu đã có trong repository. Để ingest, truy vấn hybrid hoặc chạy baseline, điền `OPENAI_API_KEY` riêng vào `.env`, sau đó khởi động Qdrant và bảo đảm collection/index đã tồn tại:

```powershell
docker compose up -d qdrant
uv run python -m lawagent.index
```

Không đưa `OPENAI_API_KEY` vào mã, tài liệu, commit hoặc log. Tệp `.env` đã được Git bỏ qua; xem [CONFIGURATION.md](CONFIGURATION.md) để biết biến cấu hình và giá trị mặc định.

## Lệnh hiện có

LawAgent không định nghĩa pipeline build artifact riêng. Ba entry point được khai báo trong `pyproject.toml` là:

| Lệnh | Mô tả |
| --- | --- |
| `uv run lawagent-parse` | Chạy parser với manifest và đường dẫn output mặc định. |
| `uv run lawagent-search "<truy vấn>" --as-of YYYY-MM-DD` | Tra cứu hybrid dense + BM25 + RRF tại ngày hiệu lực chỉ định; cần Qdrant đã ingest và khóa OpenAI hợp lệ. |
| `uv run lawagent-baseline` | Chạy 10 truy vấn hồi quy, ghi top-5 vào `data/processed/retrieval_baseline.json`, và trả mã lỗi nếu một kết quả top-1 không khớp. |

Các lệnh vận hành và kiểm tra bổ sung:

| Lệnh | Mô tả |
| --- | --- |
| `uv run python -m lawagent.parser` | Cách gọi module tương đương entry point parser. |
| `uv run python scripts/validate_parser.py` | Đối chiếu `chunks.jsonl` với manifest; ghi validation report và mẫu spot-check. |
| `uv run pytest -q -p no:cacheprovider` | Chạy toàn bộ test trong `tests/`. |
| `docker compose up -d qdrant` | Khởi động Qdrant cục bộ trên loopback để dùng với index, ingest và truy xuất hybrid. |
| `uv run python -m lawagent.index` | Tạo hoặc kiểm tra Qdrant collection và các payload index; có thể chạy lặp lại an toàn. |
| `uv run python -m lawagent.ingest` | Tạo embedding OpenAI và upsert các chunk chưa có theo batch; cần Qdrant và khóa OpenAI hợp lệ. |
| `uv run python -m lawagent.sparse "Điều 35" --limit 5` | Chạy BM25 cục bộ, không cần Qdrant hay khóa OpenAI. |

`lawagent-search` nhận `--limit` (mặc định `5`) và `--retrieval-limit` (mặc định `10`); retrieval limit phải không nhỏ hơn limit. Nếu không truyền `--as-of`, CLI dùng ngày hiện tại. `lawagent-baseline` nhận `--output` và `--limit` để đổi report hoặc số kết quả lưu cho mỗi case.

Repository không có script lint, format, type-check, build, watch hay coverage riêng.

## Phân chia module

| Vị trí | Trách nhiệm |
| --- | --- |
| `src/lawagent/parser.py` | Đọc văn bản `.txt`/`.docx`, tách Chương/Mục/Điều, tạo `LegalChunk` và dẫn chiếu có cấu trúc. |
| `src/lawagent/references.py` | Lấy đúng nội dung Khoản/Điểm và mở rộng một tầng dẫn chiếu nội bộ. |
| `src/lawagent/sparse.py` | Chuẩn hóa token tiếng Việt, lập chỉ mục BM25 trong bộ nhớ và CLI sparse search. |
| `src/lawagent/temporal_filter.py` | Lọc chunk còn hiệu lực ở một ngày cho nhánh sparse và tạo bộ lọc Qdrant tương đương cho nhánh dense. |
| `src/lawagent/dense.py` | Tạo embedding truy vấn bằng OpenAI và truy xuất vector Qdrant với temporal filter. |
| `src/lawagent/search.py` | Hợp nhất dense/BM25 bằng RRF, áp dụng quy tắc ưu tiên pháp lý và cung cấp CLI `lawagent-search`. |
| `src/lawagent/baseline.py` | Chạy bộ 10 truy vấn kỳ vọng và ghi report hồi quy JSON qua CLI `lawagent-baseline`. |
| `src/lawagent/config.py` | Nạp cấu hình Qdrant và embedding từ môi trường. |
| `src/lawagent/index.py` | Tạo collection Qdrant và payload index. |
| `src/lawagent/ingest.py` | Tạo embedding theo batch và upsert payload vào Qdrant. |
| `scripts/validate_parser.py` | Xác thực số Điều, `chunk_id`, breadcrumb và dẫn chiếu nội bộ sau khi parse. |
| `tests/` | Test unit cho parser, dẫn chiếu, BM25, temporal filter, dense retrieval và hybrid search. |

Thay đổi schema chunk hoặc metadata trong `src/lawagent/parser.py` cần được kiểm tra cùng `src/lawagent/references.py`, `src/lawagent/sparse.py`, `src/lawagent/temporal_filter.py`, `src/lawagent/dense.py`, `src/lawagent/ingest.py`, validation script và các test liên quan.

## Luồng phát triển CLI và truy xuất

Đối với thay đổi parser hoặc corpus, chạy parser, validation và toàn bộ test trước khi bàn giao:

```powershell
uv run lawagent-parse
uv run python scripts/validate_parser.py
uv run pytest -q -p no:cacheprovider
```

Đối với thay đổi dense retrieval, temporal filter, fusion hoặc CLI, chuẩn bị Qdrant/`.env`, ingest corpus khi dữ liệu hay embedding thay đổi, rồi kiểm tra truy vấn tại một mốc hiệu lực rõ ràng:

```powershell
docker compose up -d qdrant
uv run python -m lawagent.index
uv run python -m lawagent.ingest
uv run lawagent-search "Điều 35" --as-of 2026-09-22
```

Ingest và truy vấn hybrid gọi OpenAI API; không chạy chúng chỉ để kiểm tra thay đổi parser thuần túy. Sau thay đổi có thể ảnh hưởng thứ hạng, chạy baseline để cập nhật report và xác nhận không có hồi quy:

```powershell
uv run lawagent-baseline
```

Kết quả đã được kiểm chứng hiện tại là **24** test pytest đạt và baseline **10/10** top-1, lưu tại `data/processed/retrieval_baseline.json`. Baseline yêu cầu corpus đã được ingest vào Qdrant và có thể phát sinh chi phí embedding cho các truy vấn.

### Quy tắc xếp hạng cần bảo toàn

`reciprocal_rank_fusion()` trong `src/lawagent/search.py` dùng `RRF_K = 60`. Sau khi hợp nhất ứng viên từ hai nhánh, thứ tự ưu tiên là: trùng chính xác số Điều trong truy vấn, trùng chính xác tiêu đề Điều sau chuẩn hóa Unicode NFC/casefold, loại văn bản (Hiến pháp, Bộ luật, Luật, Nghị định) và cấp hierarchy khi đang trùng Điều, rồi mới đến điểm RRF.

Vì vậy, truy vấn như `Điều 35` phải ưu tiên chunk có `dieu_label` là `35` hơn kết quả ngữ nghĩa có điểm RRF cao hơn. Khi truy vấn đúng toàn bộ `dieu_title`, kết quả tiêu đề trùng chính xác phải vượt kết quả liên quan có RRF cao hơn. Ở nhánh BM25, các kết quả trùng Điều cũng được đưa lên trước; trong nhóm đó, `hierarchy_level` nhỏ hơn được ưu tiên trước điểm BM25. Những quy tắc này được bảo vệ trong `tests/test_sparse.py` và `tests/test_search.py`.

## Phong cách mã nguồn

Repository hiện không có cấu hình cho Ruff, Black, isort, Flake8, mypy, Prettier, ESLint, Biome hay `.editorconfig`; `pyproject.toml` cũng không khai báo lệnh lint hoặc format. Vì vậy, không có công cụ định dạng hoặc lint bắt buộc được ghi nhận.

Hãy giữ cách viết nhất quán với module đang sửa: type hint cho API công khai, docstring ngắn cho module/hàm có hành vi không hiển nhiên, và định dạng Python dễ đọc. Đừng thêm một công cụ lint/format hay cấu hình mới chỉ để đáp ứng thay đổi nhỏ nếu chưa có quyết định của dự án.

## Nhánh và pull request

Không có quy ước đặt tên nhánh, hướng dẫn đóng góp riêng, pull-request template, issue template hoặc workflow CI được ghi nhận trong repository. Nhánh đang được checkout khi tạo tài liệu là `master`, nhưng đó không phải quy tắc đặt tên nhánh được công bố.

Do chưa có checklist PR hay CI, hãy kèm theo mô tả thay đổi, test đã chạy, trạng thái baseline nếu thay đổi truy xuất, và mọi ảnh hưởng tới dữ liệu hoặc cấu hình khi gửi review. Đây là khuyến nghị làm việc cục bộ, không phải quy trình PR chính thức của dự án.
