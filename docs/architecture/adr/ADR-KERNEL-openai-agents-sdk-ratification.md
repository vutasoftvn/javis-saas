# ADR-KERNEL: Ratification của OpenAI Agents SDK làm Canonical Execution Kernel

- **Trạng thái:** RATIFIED (Đã phê chuẩn)
- **Ngày quyết định:** 2026-08-23
- **Tác giả:** COSA Core Architecture Team
- **Tham chiếu:**
  - `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md` §Phase 3 (Step 5, P0.4)
  - `COSA_CANONICAL_MASTER_ARCHITECTURE_AND_IMPLEMENTATION_GUIDE_2026-08-23.md` §9, §10
  - `docs/architecture/roadmap/hermes-langgraph-integration/phase-01-contracts-workflow-engine.md`

---

## 1. Bối cảnh (Context)

Kiến trúc cũ của COSA (`legacy/agent_runtime/` và `agentos/`) sử dụng các custom execution loops hoặc Google ADK orchestrator kết hợp lỏng lẻo. Quá trình kiểm tra mã nguồn cho thấy:
1. `AgentRuntime` / `Executor` / `Planner` tự chế tạo ra rủi ro cao về việc duy trì state vòng lặp không đồng bộ và xử lý tool call không chuẩn.
2. Tại `packages/agent_core/kernel/openai_agents_kernel.py`, implementation hiện tại là một custom loop (dùng trực tiếp package `openai` raw completion loop) chứ chưa phải là OpenAI Agents SDK chính thức (`openai-agents`).
3. Cần một quyết định kiến trúc chính thức chốt chuẩn kernel để tránh việc tiếp tục mở rộng tính năng mới trên nền custom loop tạm thời.

---

## 2. Quyết định (Decision)

1. **Phê chuẩn Canonical Kernel:** OpenAI Agents SDK (`openai-agents`) chính thức là **canonical execution kernel implementation** duy nhất cho COSA Agent Platform (thực hiện theo quyết định tại Phase 3 của Promotion Plan gốc: *"ExecutionKernel có 1 implementation thật dựa trên OpenAI Agents SDK"*).
2. **Trạng thái của Custom Loop hiện tại:** Mã nguồn tại `packages/agent_core/kernel/openai_agents_kernel.py` (dùng package `openai` trần) được xác định là **TẠM THỜI / NON-CONFORMING TRANSITIONAL CODE**.
   - Cấm gán thêm bất kỳ trách nhiệm kiến trúc hay tính năng mới nào vào custom loop này.
   - Giữ vai trò transitional execution substrate phục vụ các test harness cho đến khi SDK chính thức được migrate hoàn toàn.
3. **Tiêu chuẩn nghiệm thu chuyển đổi (Exit Criterion):**
   - Thay thế bằng SDK `openai-agents` thật trước khi Phase 3 Definition of Done được coi là hoàn tất.
4. **Cơ chế Fallback:**
   - Quyết định này chỉ được mở lại nếu và chỉ nếu DeepSeek/Model Compatibility Matrix (Phase 3, mục 6) chứng minh OpenAI Agents SDK có lỗi chặn cứng không thể khắc phục qua proxy/adapter.
   - Khi đó bắt buộc phải tạo một ADR mới riêng biệt, tuyệt đối không tự động quay lại custom loop.

---

## 3. Hệ quả (Consequences)

### Tích cực:
- Thống nhất cơ chế tool call streaming, RunState serialization, và agent-as-tool theo chuẩn công nghiệp.
- Giảm thiểu hàng ngàn dòng code tự quản lý vòng lặp ReAct/tool execution phức tạp.
- Tương thích tốt với các mô hình tiên tiến và các coordination primitives (`delegate`, `parallel`, `supervisor`).

### Thách thức & Biện pháp:
- Cần kiểm thử cẩn thận khả năng tương thích của `openai-agents` với các mô hình non-OpenAI (như DeepSeek V3/R1 qua base URL). Đã có bộ test suite `test_deepseek_compatibility_matrix.py` để phát hiện sớm bất kỳ sai lệch nào.
