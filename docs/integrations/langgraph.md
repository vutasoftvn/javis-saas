# Integration: LangGraph

## Cập nhật 2026-08-24: đã re-spike thật, KẾT LUẬN GIỮ NGUYÊN REJECT

`packages/agent_integrations/langgraph/workflow_runtime.py` — đã tạo (trái
với trạng thái "CHƯA TẠO" mô tả ở phần dưới, viết trước khi re-spike diễn
ra), compile `WorkflowSpec` (bước DETERMINISTIC) sang LangGraph `StateGraph`
thật, verify lại 2 tuyên bố kỹ thuật cốt lõi của spike gốc
(`packages/agent_testkit/workflow_conformance/test_langgraph_respike_2026.py`,
2 test, cả 2 PASS trên Postgres thật): superstep isolation + reducer merge,
và pending-write recovery (HL-13) bằng side-effect counter thật (không suy
diễn). Đối chiếu `tests/agent/workflows/` (63 test) xác nhận native
`WorkflowEngine` không thoái hoá qua Wave 0-11.

**Kết luận: giữ nguyên REJECT** của `ADR-LANGGRAPH-adoption-decision.md` —
LangGraph vẫn kỹ thuật khả thi đúng như trước, nhưng lý do reject gốc (chi
phí framework coupling lớn hơn lợi ích so với native engine đã đủ năng lực)
vẫn đúng, không có thay đổi nào justify việc mở lại. Chi tiết đầy đủ:
`docs/architecture/langgraph_spike_results.md` mục 4 "Re-spike 2026-08-24".
Package giữ lại làm bằng chứng kỹ thuật, KHÔNG wire vào `apps/cosa/composition/`.

## Trạng thái trước re-spike (giữ nguyên để đối chiếu lịch sử)

## Lý do

`ADR-LANGGRAPH-adoption-decision.md` (2026-08-23) đã chạy đầy đủ Acceptance Matrix HL-01→HL-18 và **PASS toàn bộ 18/18 tiêu chí**, nhưng quyết định REJECT làm runtime dependency (lý do: đã có kernel chủ đạo lúc đó, tránh thêm dependency nặng). `ADR-RUNTIME-001` (2026-08-24) đảo hướng runtime chính sang LangChain, nhưng **không tự động mở lại LangGraph** — mở lại đòi hỏi:

1. Đọc lại `docs/architecture/langgraph_spike_results.md` và toàn bộ acceptance matrix HL-01→18 trong `ADR-LANGGRAPH-adoption-decision.md`.
2. Chạy lại matrix đó cho ngữ cảnh MỚI (kernel chủ đạo giờ là LangChain, không phải OpenAI Agents SDK) — tiền đề reject cũ ("đã có kernel chủ đạo") đã thay đổi, nhưng phải verify nghiêm túc lại, không giả định PASS cũ vẫn áp dụng.

## Việc cần làm khi mở lại

Xem `ADR-RUNTIME-001-langchain-deepseek-primary-supersedes-kernel-and-langgraph.md` §2 mục 4 (điều kiện mở lại).
