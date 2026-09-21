# ARCHITECTURE — Thiết kế hệ thống

## 1. Tổng quan

Hai node dùng OpenAI API và hai node chạy bằng code thuần, điều phối bởi LangGraph.
Planner và Synthesis gọi **OpenAI Responses API**; dense retrieval gọi **OpenAI
Embeddings API**. Model được chọn qua biến môi trường thay vì hard-code trong logic.

```
                    ┌──────────────┐
   câu hỏi  ───────►│   PLANNER    │  OpenAI · Structured Outputs
                    └──────┬───────┘
                           │ sub_queries, as_of_date, in_scope?
                    ┌──────▼───────┐
              ┌────►│  RETRIEVER   │  code · hybrid search + temporal filter
              │     └──────┬───────┘
              │            │ chunks
              │     ┌──────▼───────┐
              │     │  SYNTHESIS   │  OpenAI · soạn câu trả lời + citation
              │     └──────┬───────┘
              │            │
              │     ┌──────▼───────┐
              │     │   VERIFIER   │  code · đối chiếu citation với corpus
              │     └──────┬───────┘
              │            │
              └────────────┤ retry tối đa 1 lần nếu có citation sai
                           ▼
                       câu trả lời
```

Lý do chỉ 3 agent (không phải 5 như thiết kế ban đầu): với corpus nhỏ, các
agent "Legal Validity" và "Cross-Reference" không cần LLM riêng — chúng là **logic
xác định**, xử lý bằng metadata filter và tra cứu graph. Dùng LLM cho việc này chỉ
làm chậm, tốn tiền, và thêm chỗ để sai. Đây là một quyết định thiết kế đáng nói
trong phỏng vấn.

## 2. State

```python
from typing import TypedDict
from datetime import date

class AgentState(TypedDict):
    # input
    question: str

    # planner output
    sub_queries: list[str]
    as_of_date: date          # mặc định = hôm nay
    in_scope: bool
    scope_reason: str | None

    # retriever output
    chunks: list[LegalChunk]
    retrieval_trace: list[dict]   # log để debug & hiển thị trên UI

    # synthesis output
    answer: str
    citations: list[str]          # danh sách chunk_id

    # verifier output
    invalid_citations: list[str]
    retry_count: int
```

## 3. Node 1 — Planner Agent

**Nhiệm vụ:** ba việc, làm trong một lần gọi LLM.

1. Xác định câu hỏi có nằm trong phạm vi pháp luật lao động không.
2. Trích mốc thời gian nếu có ("hợp đồng ký tháng 3/2023" → `2023-03-01`).
3. Phân rã thành 1–3 sub-query để tăng recall.

**Output:** object có schema cố định. Dùng Structured Outputs của OpenAI Responses
API để SDK kiểm tra schema và parse thẳng vào Pydantic model, thay vì yêu cầu JSON
bằng prompt rồi tự `json.loads`.

```python
import os
from datetime import date
from openai import OpenAI
from pydantic import BaseModel, Field

openai_client = OpenAI()

class PlannerOutput(BaseModel):
    in_scope: bool
    scope_reason: str | None
    as_of_date: date
    sub_queries: list[str] = Field(min_length=1, max_length=3)

def planner(state: AgentState) -> AgentState:
    response = openai_client.responses.parse(
        model=os.getenv("OPENAI_PLANNER_MODEL", "gpt-5.4-mini"),
        instructions=PLANNER_PROMPT.format(today=date.today().isoformat()),
        input=state["question"],
        text_format=PlannerOutput,
    )
    plan = response.output_parsed
    if plan is None:
        raise ValueError("OpenAI không trả về PlannerOutput hợp lệ")
    return {**state, **plan.model_dump()}
```

```
Bạn là bộ phân tích câu hỏi cho hệ thống tra cứu pháp luật lao động Việt Nam.

Cơ sở dữ liệu chỉ chứa: Bộ luật Lao động và các nghị định hướng dẫn về
điều kiện lao động, quan hệ lao động, lương tối thiểu vùng, và xử phạt vi phạm
hành chính trong lĩnh vực lao động.

Hôm nay là {today}. Hãy xác định phạm vi, thời điểm áp dụng và tạo 1–3 truy vấn
tra cứu tiếng Việt. Kết quả phải tuân theo schema PlannerOutput do ứng dụng cung cấp.

Quy tắc:
- Nếu câu hỏi không nhắc tới mốc thời gian nào, as_of_date = hôm nay.
- Nếu nhắc tới sự việc trong quá khứ, dùng mốc đó.
- sub_queries nên dùng thuật ngữ pháp lý chuẩn, không dùng từ khẩu ngữ.
  Ví dụ: "bị đuổi việc" → "đơn phương chấm dứt hợp đồng lao động"

```

`question` được truyền qua trường `input` của Responses API, không nội suy trực
tiếp vào developer instructions. Cách tách phần hướng dẫn ổn định khỏi dữ liệu động
cũng giúp tăng khả năng tận dụng prompt caching.

**Nếu `in_scope == false`:** đi thẳng tới END với thông báo lịch sự nêu rõ phạm vi
hệ thống hỗ trợ. Không cố trả lời.

## 4. Node 2 — Retriever (code, không LLM)

```python
def retrieve(state: AgentState) -> AgentState:
    temporal = build_temporal_filter(state["as_of_date"])
    pool: dict[str, LegalChunk] = {}

    for sq in state["sub_queries"]:
        dense  = qdrant_search(sq, filter=temporal, limit=10)
        sparse = bm25_search(sq, limit=10)
        for c in rrf_fuse(dense, sparse)[:5]:
            pool[c.chunk_id] = c

    # mở rộng dẫn chiếu — CHỈ 1 TẦNG
    for c in list(pool.values()):
        for reference in c.references[:3]:       # giới hạn 3 ref/chunk
            ref_id = reference.target_chunk_id
            if not ref_id:
                # Dẫn chiếu chéo văn bản: temporal resolver phải chọn đúng phiên bản.
                continue
            if ref_id not in pool:
                ref = fetch_by_id(ref_id)
                if ref and is_effective(ref, state["as_of_date"]):
                    ref.locator_text = extract_locator_text(
                        ref.text,
                        clause=reference.target_clause,
                        point=reference.target_point,
                    )
                    ref.reference_relation = reference.relation
                    pool[ref_id] = ref

    chunks = sorted(pool.values(), key=lambda c: (c.hierarchy_level, c.dieu_number))
    return {**state, "chunks": chunks[:8]}
```

Sắp xếp theo `hierarchy_level` trước để Luật xuất hiện trên Nghị định trong context
— vị trí trong prompt ảnh hưởng tới cách LLM ưu tiên.

Với `relation` là `exception` hoặc `exclusion`, Retriever phải coi chunk đích là
bắt buộc, không phải context bổ sung tùy chọn. Nếu không phân giải được văn bản
đích tại `as_of_date`, pipeline phải cảnh báo thiếu căn cứ thay vì kết luận theo
quy tắc chính. Synthesis phải trích dẫn cả quy tắc lẫn ngoại lệ.

## 5. Node 3 — Synthesis Agent

Synthesis dùng `OPENAI_SYNTHESIS_MODEL` (mặc định `gpt-5.5`) qua Responses API.
Prompt bên dưới được truyền ở vai trò `instructions`; câu hỏi và các chunk được
render thành `input`. Nội dung ổn định đặt trước, dữ liệu truy vấn đặt sau.

```
Bạn là trợ lý tra cứu pháp luật lao động Việt Nam.

QUY TẮC BẮT BUỘC:
1. CHỈ dùng thông tin trong phần CĂN CỨ dưới đây. Tuyệt đối không dùng kiến
   thức có sẵn của bạn về pháp luật.
2. Mọi khẳng định pháp lý phải kèm trích dẫn dạng [chunk_id] ngay sau câu.
3. Nếu CĂN CỨ không đủ để trả lời, nói rõ "Không tìm thấy căn cứ trong phạm vi
   dữ liệu hiện có". Không suy đoán.
4. Nếu hai căn cứ mâu thuẫn, ưu tiên theo thứ tự: Bộ luật/Luật > Nghị định >
   Thông tư. Nếu cùng cấp, ưu tiên văn bản ban hành sau. Nêu rõ cả hai.
5. Trả lời bằng tiếng Việt, rõ ràng, không dùng từ ngữ tư vấn hành động kiểu
   "bạn nên kiện" hay "bạn hãy làm X". Chỉ trình bày quy định.

Câu hỏi được đặt trong bối cảnh áp dụng pháp luật tại thời điểm: {as_of_date}

CĂN CỨ:
{% for c in chunks %}
[{{ c.chunk_id }}] {{ c.breadcrumb }}
Hiệu lực: từ {{ c.effective_from }}{% if c.effective_to %} đến {{ c.effective_to }}{% endif %}
{{ c.text }}
---
{% endfor %}

CÂU HỎI: {question}
```

```python
def synthesize(state: AgentState) -> AgentState:
    response = openai_client.responses.create(
        model=os.getenv("OPENAI_SYNTHESIS_MODEL", "gpt-5.5"),
        instructions=SYNTHESIS_INSTRUCTIONS,
        input=render_synthesis_input(state),
    )
    return {**state, "answer": response.output_text}
```

Các biến cấu hình tối thiểu:

| Biến | Bắt buộc | Mặc định | Mục đích |
|---|---|---|---|
| `OPENAI_API_KEY` | Có | — | Xác thực OpenAI API; chỉ lưu trong `.env` cục bộ |
| `OPENAI_PLANNER_MODEL` | Không | `gpt-5.4-mini` | Model cho phân loại và phân rã truy vấn |
| `OPENAI_SYNTHESIS_MODEL` | Không | `gpt-5.5` | Model tổng hợp câu trả lời có căn cứ |
| `OPENAI_EMBEDDING_MODEL` | Không | `text-embedding-3-large` | Model tạo dense vector |

## 6. Node 4 — Citation Verifier (code, không LLM)

Đây là lớp phòng vệ chính chống hallucination. Bằng code nên kết quả xác định.

```python
CITATION_RE = re.compile(r"\[([a-zA-Z0-9_\-/]+)\]")

def verify(state: AgentState) -> AgentState:
    cited = set(CITATION_RE.findall(state["answer"]))
    available = {c.chunk_id for c in state["chunks"]}
    invalid = cited - available
    return {**state, "citations": sorted(cited & available),
            "invalid_citations": sorted(invalid)}

def route_after_verify(state: AgentState) -> str:
    if state["invalid_citations"] and state["retry_count"] < 1:
        return "synthesis"      # thử lại 1 lần, kèm cảnh báo trong prompt
    return END
```

Khi retry, thêm vào prompt: "Lần trước bạn trích dẫn các mã không tồn tại: {list}.
Chỉ được dùng đúng các mã có trong phần CĂN CỨ."

Nếu retry vẫn sai → strip các citation sai khỏi câu trả lời và hiển thị cảnh báo
trên UI. Ghi lại vào log để phân tích trong `EVALUATION.md`.

**Mở rộng nếu còn thời gian:** kiểm tra thêm mức độ *grounding* — với mỗi câu có
citation, đo độ tương đồng với chunk được trích. Câu nào dưới ngưỡng thì cảnh báo.

## 7. Lắp graph

```python
from langgraph.graph import StateGraph, END

g = StateGraph(AgentState)
g.add_node("planner",   planner)
g.add_node("retriever", retrieve)
g.add_node("synthesis", synthesize)
g.add_node("verifier",  verify)

g.set_entry_point("planner")
g.add_conditional_edges("planner",
    lambda s: "retriever" if s["in_scope"] else END,
    {"retriever": "retriever", END: END})
g.add_edge("retriever", "synthesis")
g.add_edge("synthesis", "verifier")
g.add_conditional_edges("verifier", route_after_verify,
    {"synthesis": "synthesis", END: END})

app = g.compile()
```

## 8. UI (Streamlit — giữ tối giản)

Ba phần trên một trang:

1. Ô nhập câu hỏi + date picker "Áp dụng luật tại thời điểm" (mặc định hôm nay)
2. Câu trả lời, với citation `[chunk_id]` render thành link mở expander chứa
   nguyên văn Điều được trích
3. Expander "Chi tiết truy vấn" hiển thị `retrieval_trace`: các sub-query, chunk
   nào được lấy, điểm số, chunk nào đến từ mở rộng dẫn chiếu

Phần 3 quan trọng khi demo — nó cho người xem thấy hệ thống **không phải hộp đen**.

Disclaimer cố định ở chân trang.
