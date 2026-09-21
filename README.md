# LawAgent

Trợ lý tra cứu pháp luật lao động Việt Nam có trích dẫn và lọc hiệu lực theo
thời gian. Tuần 1 (corpus và parser pháp lý) đã hoàn thành.

## Chạy pipeline dữ liệu tuần 1

Yêu cầu: Python 3.11 và [uv](https://docs.astral.sh/uv/).

```powershell
uv sync --extra dev
uv run python -m lawagent.parser
uv run python scripts/validate_parser.py
uv run pytest -q -p no:cacheprovider
```

Đầu ra chính:

- `data/processed/chunks.jsonl`: 702 Điều, 724 chunks từ 8 phiên bản văn bản;
- `data/processed/validation_report.json`: đối chiếu số Điều theo từng văn bản;
- `data/processed/spot_check.md`: mẫu kiểm tra thủ công 10 chunks;
- `data/manifest.yaml`: nguồn, phiên bản và khoảng hiệu lực.

Dẫn chiếu pháp lý được lưu kèm quan hệ, Điều/Khoản/Điểm đích. Hàm
`expand_reference_context()` trong `src/lawagent/references.py` lấy đúng nội dung
ngoại lệ thay vì đưa mù toàn bộ Điều vào context.

Thiết kế và phạm vi chi tiết nằm trong [`docs/README.md`](docs/README.md). Công cụ
chỉ phục vụ tra cứu/học tập, không thay thế tư vấn pháp lý.
