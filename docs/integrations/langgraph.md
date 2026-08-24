# Integration: LangGraph

## Trạng thái: CHƯA TẠO

`packages/agent_integrations/langgraph/` không tồn tại — quyết định thu hẹp phạm vi có chủ đích trong Wave 4 (2026-08-24).

## Lý do

`ADR-LANGGRAPH-adoption-decision.md` (2026-08-23) đã chạy đầy đủ Acceptance Matrix HL-01→HL-18 và **PASS toàn bộ 18/18 tiêu chí**, nhưng quyết định REJECT làm runtime dependency (lý do: đã có kernel chủ đạo lúc đó, tránh thêm dependency nặng). `ADR-RUNTIME-001` (2026-08-24) đảo hướng runtime chính sang LangChain, nhưng **không tự động mở lại LangGraph** — mở lại đòi hỏi:

1. Đọc lại `docs/architecture/langgraph_spike_results.md` và toàn bộ acceptance matrix HL-01→18 trong `ADR-LANGGRAPH-adoption-decision.md`.
2. Chạy lại matrix đó cho ngữ cảnh MỚI (kernel chủ đạo giờ là LangChain, không phải OpenAI Agents SDK) — tiền đề reject cũ ("đã có kernel chủ đạo") đã thay đổi, nhưng phải verify nghiêm túc lại, không giả định PASS cũ vẫn áp dụng.

## Việc cần làm khi mở lại

Xem `ADR-RUNTIME-001-langchain-deepseek-primary-supersedes-kernel-and-langgraph.md` §2 mục 4 (điều kiện mở lại).
