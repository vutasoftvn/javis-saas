# ADR-RUNTIME-001: LangChain + DeepSeek là runtime chính, supersede ADR-KERNEL và ADR-LANGGRAPH

- **Trạng thái:** ACCEPTED (quyết định người dùng, phiên plan-mode 2026-08-24) — **triển khai chưa bắt đầu**, chờ review trước khi code Wave 1.
- **Ngày quyết định:** 2026-08-24
- **Tác giả:** COSA Core Architecture Team (quyết định do người dùng chốt trực tiếp trong phiên phân tích Blueprint V2)
- **Supersedes:**
  - `ADR-KERNEL-openai-agents-sdk-ratification.md` (2026-08-23, RATIFIED)
  - `ADR-LANGGRAPH-adoption-decision.md` (2026-08-23, CLOSED — REJECT AS RUNTIME DEPENDENCY)
- **Tham chiếu:**
  - `COSA_AGENT_PLATFORM_IMPLEMENTATION_BLUEPRINT_V2_2026-08-24.md` §0, §64, §74
  - `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` Phần A, Phần F (Wave 4)
  - `docs/architecture/langgraph_spike_results.md`

---

## 1. Bối cảnh

Hai ADR trước đã ratify hướng đi khác:

- `ADR-KERNEL` (2026-08-23) chốt **OpenAI Agents SDK** là canonical execution kernel duy nhất, coi custom loop hiện tại (`packages/agent_core/kernel/openai_agents_kernel.py`) là transitional code phải thay thế.
- `ADR-LANGGRAPH` (2026-08-23) chốt **reject LangGraph làm runtime dependency**, sau khi chạy đầy đủ Acceptance Matrix HL-01→HL-18 và **toàn bộ 18 tiêu chí đều PASS** — quyết định reject không phải vì LangGraph thất bại kỹ thuật, mà vì "COSA đã có `ExecutionKernel` (OpenAI Agents SDK) làm runtime chủ đạo", tránh thêm dependency nặng không cần thiết.

ADR này **không tranh luận lại** kết quả kỹ thuật của 2 ADR trên (matrix HL-01→18 PASS vẫn đúng, custom loop vẫn là transitional code như mô tả). Đây là một **quyết định chiến lược của người dùng**, chọn hướng LangChain + DeepSeek làm runtime chính theo `COSA_AGENT_PLATFORM_IMPLEMENTATION_BLUEPRINT_V2_2026-08-24.md`, ưu tiên hệ sinh thái tích hợp rộng của LangChain (model/tool adapters, provider breadth) và alignment với DeepSeek làm model provider chính, thay vì tiếp tục đầu tư vào OpenAI Agents SDK làm kernel duy nhất hay giữ nguyên quyết định loại bỏ LangGraph.

**Xác nhận trạng thái code tại thời điểm quyết định (2026-08-24, HEAD `fcfe387`):**
- `packages/agent_core/kernel/openai_agents_kernel.py` vẫn là custom loop, chưa migrate sang SDK thật — không có gì thay đổi so với mô tả trong ADR-KERNEL.
- Chưa có bất kỳ dòng dependency LangChain/LangGraph nào trong `packages/` — đây là lần đầu đưa LangChain vào repo.
- Google ADK (`AdkCofounderWorkflow`, `google-adk==2.7.0`) đã ship và chạy production, tài liệu tại `docs/agent-platform/ADK_INTEGRATION.md` — **không nằm trong phạm vi 2 ADR bị supersede**, và ADR này không thay đổi trạng thái production của ADK.

---

## 2. Quyết định

1. **LangChain + DeepSeek trở thành runtime/model integration ưu tiên (primary)** cho COSA Agent Platform, theo Blueprint V2 §64.1 bảng vai trò công nghệ.
2. **OpenAI Agents SDK chuyển từ "canonical kernel duy nhất" xuống "adapter tuỳ chọn"** (`packages/agent_integrations/openai_agents/`, Wave 10). Việc hoàn thiện SDK thật (thay custom loop) vẫn nên làm nhưng không còn là exit criterion bắt buộc của Wave 1 — hạ xuống Wave 10.
3. **Google ADK giữ nguyên vai trò adapter, và giữ nguyên trạng thái production hiện tại** (`AdkCofounderWorkflow` không bị thay thế/rollback bởi ADR này). ADK **không** bị hạ cấp về mặt vận hành — chỉ không còn là ứng viên "kernel chính" theo khung phân loại mới, vì LangChain giữ vai trò đó.
4. **LangGraph được mở lại làm `WorkflowRuntime` candidate** (không phải mặc định ngay) — theo Blueprint V2 §74, cần spike + conformance suite mới trước khi thay thế `NativeWorkflowRuntime` cho bất kỳ workflow production nào. Spike mới **bắt buộc đọc lại** `docs/architecture/langgraph_spike_results.md` và acceptance matrix HL-01→18 trong `ADR-LANGGRAPH` để không lặp lại công việc đã làm, và phải giải thích rõ vì sao kết luận "reject vì đã có kernel chủ đạo" không còn áp dụng (vì kernel chủ đạo nay đổi sang LangChain, tiền đề của lập luận reject cũ đã thay đổi).
5. **Không xoá/archive `packages/agent_core/kernel/openai_agents_kernel.py`** cho tới khi `packages/agent_integrations/openai_agents/` (Wave 10) thay thế hoàn toàn và có conformance test pass.

### Điều kiện mở lại (rollback clause)

Nếu `agent_testkit/kernel_conformance/` cho `LangChainKernel` (Wave 4, Blueprint V2 §46) thất bại ở tiêu chí cứng (exact `(run_id, tool_call_id)` identity, resume/checkpoint, no-duplicate-side-effect-after-retry) mà không có cách khắc phục qua adapter, quyết định này phải được mở lại bằng ADR mới — tuyệt đối không tự động quay lại OpenAI Agents SDK/native workflow mà không ghi nhận rõ.

---

## 3. Hệ quả

### Tích cực
- Hệ sinh thái model/tool provider rộng hơn qua LangChain, giảm công sức viết adapter riêng cho từng provider ngoài OpenAI/DeepSeek.
- Alignment rõ với DeepSeek làm model chính theo định hướng sản phẩm Blueprint V2.

### Rủi ro & biện pháp
- **Đảo ngược 1 phân tích kỹ thuật đã PASS toàn bộ 18/18 tiêu chí (ADR-LANGGRAPH)** — rủi ro lặp lại vấn đề đã biết (framework coupling, persistence trùng lặp, serialization risk) nếu spike mới không xử lý nghiêm túc. Biện pháp: Wave 4 bắt buộc chạy lại đúng bộ acceptance matrix HL-01→18 cho LangGraph spike mới, không được coi ADR cũ đã PASS là "đã chứng minh cho ngữ cảnh mới".
- **Custom loop kernel kéo dài thời gian tồn tại hơn dự kiến ban đầu** (ADR-KERNEL yêu cầu thay thế trước khi Phase 3 DoD hoàn tất; ADR này hạ xuống Wave 10) — chấp nhận rủi ro nợ kỹ thuật này có kiểm soát, không mở rộng thêm tính năng mới trên custom loop (giữ nguyên ràng buộc gốc của ADR-KERNEL mục 2).
- **Google ADK và LangChain chạy song song** trong giai đoạn chuyển tiếp (Wave 4-10) — cần runtime policy rõ ràng (`apps/cosa/composition/agent_plane.py`) để không có 2 kernel cùng nhận 1 run, tránh xung đột governance/audit.

---

## 4. Việc cần cập nhật kèm theo ADR này

- `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` dòng "Execution Kernel" (hiện trỏ OpenAI Agents SDK) → cập nhật trỏ ADR này.
- `COSA_CANONICAL_MASTER_ARCHITECTURE_AND_IMPLEMENTATION_GUIDE_2026-08-23.md` §1.1 Decision 3, §9 — thêm ghi chú "Superseded by ADR-RUNTIME-001" (không sửa nội dung lịch sử).
- `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` mục "Trạng thái triển khai" — đánh dấu Wave 0.1 (phần runtime) hoàn tất sau khi ADR này được người dùng review.
