# ADR-RUNTIME-002: OpenAI Agents SDK là runtime chính, DeepSeek là model provider chính, LangChain là adapter tuỳ chọn — supersede ADR-RUNTIME-001

- **Trạng thái:** ACCEPTED (quyết định người dùng, phiên phân tích/đối chiếu `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md`, 2026-08-25) — **triển khai chưa bắt đầu**, xem Phase 7 của bảng "Kế hoạch triển khai chi tiết" trong tài liệu trên.
- **Ngày quyết định:** 2026-08-25
- **Tác giả:** COSA Core Architecture Team (quyết định do người dùng chốt trực tiếp, sau khi được chỉ ra rằng ADR-RUNTIME-001 có 4 nguồn mâu thuẫn nhau: header ACCEPTED, ghi chú "chưa có bằng chứng review kỹ" trong chính phiên tạo ra nó, code default vẫn `OpenAIAgentsKernel`, và comment code gọi LangChain là "DRAFT chưa review")
- **Supersedes:**
  - `ADR-RUNTIME-001-langchain-deepseek-primary-supersedes-kernel-and-langgraph.md` (2026-08-24, ACCEPTED nhưng chưa từng implement)
- **Tham chiếu:**
  - `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md` §29 "Reconciliation Addendum" (phần 3 — Runtime, Decision RUNTIME-001)
  - `ADR-KERNEL-openai-agents-sdk-ratification.md` (2026-08-23, RATIFIED — nội dung kỹ thuật ADR này khôi phục lại)
  - `ADR-LANGGRAPH-adoption-decision.md` (2026-08-23, CLOSED — REJECT; không bị mở lại bởi ADR này)

---

## 1. Bối cảnh

`ADR-RUNTIME-001` (2026-08-24) chốt LangChain + DeepSeek làm runtime chính, hạ OpenAI Agents SDK xuống adapter tuỳ chọn. Tại thời điểm đối chiếu tài liệu `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md` với code thật (2026-08-25), phát hiện 4 nguồn thông tin về trạng thái quyết định này **mâu thuẫn nhau**:

1. Header `ADR-RUNTIME-001` ghi `Trạng thái: ACCEPTED`.
2. Chính mục "Tổng kết toàn bộ 11 Wave" trong `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` (tài liệu tạo ra ADR này) tự ghi: *"KHÔNG tự ý coi đây là đã xong — cần người dùng xác nhận rõ ràng đã đọc/duyệt 2 ADR này trước khi coi quyết định kiến trúc... là chính thức"*.
3. Code hiện tại (`apps/cosa/composition/agent_plane.py`) vẫn mặc định `OpenAIAgentsKernel`, không phải `LangChainKernel`.
4. Comment trong cùng file gọi LangChain là "DRAFT chưa được review" — ngôn ngữ này lẽ ra phải đổi thành "ACCEPTED, chưa implement" nếu ADR-RUNTIME-001 thật sự đã qua review, nhưng chưa từng được cập nhật.

Đây là loại quyết định code không được tự suy luận. Người dùng đã được hỏi trực tiếp và chọn hướng ngược lại nội dung ADR-RUNTIME-001.

---

## 2. Quyết định

1. **OpenAI Agents SDK là primary execution runtime (canonical kernel)** — khôi phục lại đúng nội dung kỹ thuật của `ADR-KERNEL-openai-agents-sdk-ratification.md` (2026-08-23). Không phải "giữ tạm vì code chưa đổi" — đây là lựa chọn kiến trúc tường minh.
2. **DeepSeek là primary model provider**, truy cập qua LiteLLM — không đổi so với định hướng sản phẩm gốc. Đã có bằng chứng chạy thật: `RealOpenAIAgentsSDKKernel` + `LitellmModel` gọi DeepSeek thành công (`packages/agent_testkit/kernel_conformance/test_openai_agents_sdk_kernel_deepseek_live.py`).
3. **LangChain trở thành optional integration/model adapter** (`packages/agent_integrations/langchain/`) — tồn tại, có conformance test, nhưng **không nằm trên đường cutover production**, không phải "runtime chủ đạo". Đảo ngược hoàn toàn quyết định #1-2 của `ADR-RUNTIME-001`.
4. **Google ADK giữ nguyên vai trò adapter tuỳ chọn** (`packages/agent_integrations/google_adk/`) — không đổi so với ADR-RUNTIME-001.
5. **`AdkCofounderWorkflow`** (`legacy/agent_runtime/workforce/agents/orchestration/adk/workflow.py`) — quyết định PROMOTE hay RETIRE **không nằm trong phạm vi ADR này**, vì đây là một business workflow cụ thể (mission/founder domain), khác trục với việc chọn kernel generic. Phải hỏi người dùng riêng ở đầu Phase 7 triển khai (xem `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md` §29).
6. **`ADR-LANGGRAPH-adoption-decision.md` không bị mở lại** — giữ nguyên `CLOSED — REJECT`. Re-spike 2026-08-24 (`docs/architecture/langgraph_spike_results.md` mục 4) đã xác nhận lại kết luận reject; ADR-RUNTIME-001 từng mở khả năng dùng LangGraph làm `WorkflowRuntime` candidate — khả năng đó không còn tiền đề hợp lý một khi kernel chủ đạo quay lại OpenAI Agents SDK (LangGraph không liên kết với OpenAI Agents SDK theo cách nó liên kết với LangChain).

### Điều kiện mở lại (rollback clause)

Nếu trong Phase 7 (harden OpenAI Agents SDK cho production — DeepSeek conformance đầy đủ, checkpoint/resume, restart recovery, parallel tool calls) phát hiện giới hạn kỹ thuật thật sự không khắc phục được (không phải "chưa làm" mà là "không làm được"), quyết định này phải mở lại bằng ADR mới — không tự động quay lại LangChain mà không ghi nhận rõ lý do kỹ thuật.

---

## 3. Hệ quả

### Tích cực
- Loại bỏ một "framework selection" giả — công sức Phase 7 dồn hẳn vào production-hardening một runtime đã có nền tảng lớn nhất (spec registry, prompt bundle, exact invocation identity, đã từng gọi DeepSeek thật thành công), thay vì vừa cutover kernel mới vừa phải chứng minh lại toàn bộ các invariant đó.
- `packages/agent_integrations/langchain/` không bị xoá — vẫn dùng được cho các nhu cầu tích hợp model/tool ngoài OpenAI/DeepSeek trong tương lai, chỉ không phải đường mặc định.

### Rủi ro & biện pháp
- **Đảo ngược một quyết định "ACCEPTED" chỉ sau 1 ngày** — rủi ro tạo thêm một vòng lặp "quyết định chồng quyết định" nếu không ghi rõ provenance. Biện pháp: ADR này trích dẫn nguyên văn 4 nguồn mâu thuẫn đã phát hiện (mục 1) làm bằng chứng, không chỉ ghi "đổi ý".
- **`packages/agent_integrations/langchain/kernel.py` đã có code + test conformance** (Wave 4 cũ) — không xoá, nhưng cần gắn nhãn rõ "optional adapter, không trên cutover path" để tránh người triển khai sau hiểu nhầm là đang chờ cutover.

---

## 4. Việc cần cập nhật kèm theo ADR này

- `ADR-RUNTIME-001` — thêm dòng `Status: SUPERSEDED by ADR-RUNTIME-002 (2026-08-25)` vào header, giữ nguyên nội dung làm lịch sử.
- `CLAUDE.md` — sửa dòng nhắc tới "LangChain-primary... ADR-RUNTIME-001" thành "OpenAI Agents SDK-primary (DeepSeek provider)... ADR-RUNTIME-002".
- `apps/cosa/composition/agent_plane.py` — sửa comment "LangChain DRAFT chưa được review" cho khớp ADR này (việc này thuộc Phase 7 code, không phải phiên tài liệu 2026-08-25).
- `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` dòng "Execution Kernel" — trỏ lại ADR này thay vì ADR-RUNTIME-001 (việc của phiên implementation sau, không thuộc phiên tài liệu này).
