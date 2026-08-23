# ADR-LANGGRAPH: Quyết Định Thẩm Định & Lựa Chọn Kiến Trúc LangGraph (Decision Gate)

- **Trạng thái:** CLOSED — REJECT AS RUNTIME DEPENDENCY / HARVEST PATTERNS INTO NATIVE WORKFLOW ENGINE
- **Ngày quyết định:** 2026-08-23
- **Tác giả:** COSA Core Architecture Team
- **Tham chiếu:**
  - `docs/architecture/roadmap/hermes-langgraph-integration/phase-06-drift-suite-langgraph-gate.md`
  - `COSA_HERMES_LANGGRAPH_INTEGRATION_PLAN_2026-08-23.md` §0, §3, §5
  - `COSA_HERMES_LANGGRAPH_ARCHITECTURE_AND_IMPLEMENTATION_SUPPLEMENT_2026-08-23.md` §45–§47
  - `docs/architecture/langgraph_spike_results.md`

---

## 1. Bối cảnh & Mục tiêu Đánh giá

Tại Phase 6, hệ thống kích hoạt **LangGraph Adoption Decision Gate** duy nhất trong toàn bộ roadmap để đưa ra quyết định chính thức: **Adopt**, **Reject**, hay **Defer** việc tích hợp LangGraph vào COSA Agent Platform.

Căn cứ theo Complexity Gate (§46):
> *"Chỉ Adopt nếu: `custom code removed + failure semantics improved + tests simplified/strengthened` > `framework coupling + extra persistence + integration complexity`."*

---

## 2. Kết quả Đánh giá Ma trận Nghiệm thu (Acceptance Matrix HL-01 → HL-18)

| ID | Tiêu chí Kiểm định | Đánh giá | Ghi chú & Bằng chứng thực tế |
|---|---|---|---|
| **HL-01** | Context Lifetime | **PASS** | Phân tầng STABLE, RUN, CURRENT, EPHEMERAL hoạt động độc lập qua `ContextSnapshot`. |
| **HL-02** | Business Truth > Stale Memory | **PASS** | Kết quả RPC của `services/company` luôn là nguồn sự thật tối thượng. |
| **HL-03** | Tenant Isolation | **PASS** | Dữ liệu context và execution gắn chặt với `tenant_id` / `workspace_id`. |
| **HL-06** | Child Authority Attenuation | **PASS** | Quyền của child luôn là tập con của parent (`Authority(child) ⊆ Authority(parent)`). |
| **HL-11** | WorkflowSpec Determinism | **PASS** | Cùng `WorkflowSpec` cho ra cùng execution graph và `definition_hash`. |
| **HL-12** | Version Pinning qua Resume | **PASS** | Đã chứng minh qua Test Case A (v1 pause → v2 publish → resume đúng v1). |
| **HL-13** | Parallel Pending-Write Recovery | **PASS** | Khôi phục nhánh thất bại mà không chạy lại nhánh đã thành công. |
| **HL-14** | Approval Authority Retention | **PASS** | `interrupt()` chỉ là control primitive; COSA Governance luôn giữ quyền tối cao. |
| **HL-15** | Crash Window Idempotency | **PASS** | Đã chứng minh qua Test Case I (không duplicate side effects sau restart). |
| **HL-16** | Thread Identity Independence | **PASS** | Phân tách rành mạch `thread_id/checkpoint_id ≈ run_id ≠ conversation_id`. |
| **HL-17** | Run Fork Lineage | **PASS** | Replay/Fork tạo checkpoint mới, không ghi đè lịch sử cũ. |
| **HL-18** | Serialization Security | **PASS** | Serialization kiểm soát qua Typed Pydantic models, loại trừ arbitrary code execution. |

---

## 3. Quyết định Kiến trúc (Decision)

### **QUYẾT ĐỊNH: REJECT AS RUNTIME DEPENDENCY / HARVEST PATTERNS (Theo Supplement §47)**

1. **Không đưa `langgraph` vào làm dependency runtime chính thức của `packages/agent_core`:**
   - `WorkflowEngine` native của COSA (migrate từ `agentos/workflows/*` tại Phase 1) đã được kiểm chứng qua 12 test suites, 35+ test cases, hỗ trợ đầy đủ DAG, YAML declarative, approval pause/resume, compensation rollback, và version pinning.
   - Thêm `langgraph` sẽ kéo theo chuỗi dependency nặng nề (`langchain-core`, graph runtime overhead), tạo thêm một tầng trừu tượng không cần thiết trong khi COSA đã có `ExecutionKernel` (OpenAI Agents SDK) làm runtime chủ đạo.
2. **Tiếp thu toàn bộ các mẫu hình ưu tú của LangGraph (Harvest Patterns) vào Native `WorkflowEngine` ở Phase 9:**
   - Tách biệt rõ 3 pha **PLAN / EXECUTE / UPDATE** (Superstep model).
   - Áp dụng **Reducer-based state updates** cho các nhánh song song thay vì shared dict mutation.
   - **Pending-write durability:** Lưu trữ partial parallel success để phục hồi nhánh lỗi mà không chạy lại nhánh đã pass.
   - Giữ rành mạch phân định **State vs Context** qua `ContextSnapshot`.

---

## 4. Hệ quả & Lợi ích

- **Zero Heavy External Coupling:** Không phụ thuộc vào sự biến đổi API nhanh chóng của LangGraph/LangChain.
- **Bảo toàn Invariants Quản trị:** Tối giản hóa đường truyền thực thi, giảm rủi ro bypass governance.
- **Hiệu năng & Tối ưu:** Mã nguồn Python thuần gọn nhẹ, thời gian khởi động tức thì, tương thích 100% với Postgres 5 bảng canonical.
