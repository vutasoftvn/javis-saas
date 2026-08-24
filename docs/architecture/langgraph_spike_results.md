# Báo Cáo Kỹ Thuật: LangGraph Technical Spike Results

> **Tham chiếu:**
> - `docs/architecture/roadmap/hermes-langgraph-integration/phase-03-kernel-coordination.md`
> - `COSA_HERMES_LANGGRAPH_INTEGRATION_PLAN_2026-08-23.md` §3, §4
> - `COSA_HERMES_LANGGRAPH_ARCHITECTURE_AND_IMPLEMENTATION_SUPPLEMENT_2026-08-23.md` §35–§47

---

## 1. Mục tiêu và Phạm vi của Spike (Phase 3)

Technical Spike này nhằm đánh giá tính khả thi kỹ thuật (technical feasibility) của LangGraph đối với COSA Agent Platform trước khi đưa ra quyết định chấp thuận tại Phase 6 Decision Gate.
- **Tính chất:** Độc lập, Non-binding (không ràng buộc quyết định sản phẩm tại Phase 3).
- **Mục tiêu kỹ thuật:**
  1. Đánh giá việc biên dịch `WorkflowSpec` (từ `packages/agent_core/workflows/`) thành LangGraph `StateGraph`.
  2. Kiểm tra tính chất superstep execution & cách ly write giữa các nhánh song song.
  3. Kiểm tra tính tương thích của checkpointing / resume và cơ chế phục hồi pending-writes.
  4. Xác minh boundary kiểm soát: LangGraph `interrupt()` chỉ là control primitive, không thay thế hoặc làm suy yếu quyền hạn quản trị (governance authority) của COSA.

---

## 2. Kết quả Spike Kỹ Thuật

### 2.1. Biên dịch WorkflowSpec → LangGraph StateGraph (Mapping Feasibility)
- **Mapping:**
  - `DeterministicStep` → Normal Python graph node (`func(state) -> state_updates`).
  - `AgentStep` → Node đóng gói lời gọi `ExecutionKernel.run()`.
  - `ToolStep` → Node gọi qua `CapabilityGateway` (Phase 4), đảm bảo kiểm tra readiness và governance.
  - `depends_on` → Graph edges và Conditional routing edges.
  - `ParallelStep` → Fan-out ready nodes trong cùng một Pregel superstep.
- **Đánh giá:**
  - `WorkflowSpec` có thể biên dịch có tính tất định (deterministic) sang `StateGraph`.
  - Cấu trúc DAG của COSA map tự nhiên vào Pregel computational model.

### 2.2. Superstep Isolation & Reducer Semantics
- **Đặc tính Pregel:**
  - Trong cùng một superstep (ví dụ: `ResearchA` và `ResearchB` chạy song song), các state writes của `ResearchA` hoàn toàn không hiển thị đối với `ResearchB` cho đến khi superstep kết thúc.
  - Reducer giải quyết xung đột khi hợp nhất state về nhánh chính một cách tường minh, loại bỏ lỗi race condition của cơ chế shared dict mutation thông thường.

### 2.3. Durable Checkpoint & Pending-Writes Recovery
- **Checkpointing:**
  - LangGraph hỗ trợ Postgres checkpointer native (Option A). Khi lưu trữ, cần serialize `StateSnapshot` vào bảng persistence.
  - Cần bảo đảm định danh: `thread_id` tương đương với `run_id`, tuyệt đối không dùng chung giữa các Run khác nhau trong cùng conversation (`thread_id ≠ conversation_id`).
- **Pending-Writes:**
  - Khi một superstep có 3 nhánh [A, B, C], trong đó A và B thành công nhưng C gặp lỗi crash tiến trình: Checkpoint lưu trữ kết quả của A và B. Khi restart/resume, hệ thống chỉ cần retry nhánh C mà không phải chạy lại A và B.

### 2.4. Khảo sát Approval Interruption (Phase 5 Spike Verification)
- Khi một node cần phê duyệt của con người, LangGraph phát sinh lệnh `interrupt()`.
- **Nguyên tắc Invariant Bắt buộc của COSA:**
  - `interrupt()` **chỉ là control-flow pause primitive**.
  - Việc phê duyệt bắt buộc phải do `packages/agent_core/capabilities/approval_service.py` thẩm định dựa trên `(run_id, tool_call_id, checkpoint_ref)` và đánh giá lại fresh ambient governance tại thời điểm resume.
  - Nếu quyền hạn của tenant/principal bị thu hồi trước khi resume, lệnh resume phải bị **DENY**, giá trị interrupt value đã lưu trữ trong LangGraph không được phép bypass governance của COSA.

---

## 3. Trạng thái Hoàn Tất & Quyết Định Cuối Cùng (Phase 6 & 11)

- **Trạng thái cuối cùng:** CLOSED — REJECT AS RUNTIME DEPENDENCY / HARVEST PATTERNS.
- **Căn cứ quyết định:**
  - Theo **ADR-LANGGRAPH** (`docs/architecture/adr/ADR-LANGGRAPH-adoption-decision.md`) tại Phase 6 Decision Gate: Hệ thống quyết định **không** đưa thư viện LangGraph làm dependency runtime chính thức do chi phí framework coupling và serialization overhead lớn hơn lợi ích mang lại so với `WorkflowEngine` native của COSA (đã pass 100% DAG, retry, compensation, approval pause/resume, version pinning).
  - Thay vào đó, toàn bộ các mẫu hình ưu tú nhất của LangGraph (Superstep execution model, Reducer-based state merge, Pending-write durability, State vs Context separation) đã được tiếp thu và chuẩn hóa trực tiếp trong `packages/agent_core/workflows/` và `packages/agent_core/contracts/context.py`.
- **Lưu trữ lịch sử:** Toàn bộ kết quả spike được lưu trữ vĩnh viễn tại tài liệu này phục vụ đối chiếu lịch sử theo Phase 11.

---

## 4. Re-spike 2026-08-24 — Chạy lại THẬT với code, không chỉ đọc lại prose

Theo `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` Phần 2
(quyết định #1 mở lại LangGraph làm `WorkflowRuntime` candidate cần spike +
conformance trước khi thay Native engine), đã chạy lại các tuyên bố kỹ thuật
cốt lõi của spike 2026-08-23 bằng code thật thay vì chỉ đọc lại tài liệu cũ —
lần đầu tiên có Postgres/Docker để verify thật (spike gốc dựa trên phân tích
kỹ thuật + review API, không có môi trường chạy thật).

**Code:** `packages/agent_integrations/langgraph/workflow_runtime.py` —
`compile_deterministic_workflow()` compile 1 `WorkflowSpec` (chỉ bước
DETERMINISTIC, phạm vi cố ý thu hẹp — xem docstring trong file) sang LangGraph
`StateGraph` thật.

**Test:** `packages/agent_testkit/workflow_conformance/test_langgraph_respike_2026.py`
— 2 test chạy thật với `langgraph==0.x` + `AsyncPostgresSaver` (Postgres 16
thật, không mock):

1. `test_langgraph_superstep_isolation_and_reducer_merge` — verify lại tuyên
   bố §2.2 (superstep isolation, reducer merge) — **PASS**: 2 nhánh song song
   ghi kết quả độc lập, reducer hợp nhất đúng, thứ tự thực thi đúng
   root→{branch_a,branch_b}→join.
2. `test_langgraph_pending_write_recovery_after_crash` — verify lại tuyên bố
   §2.3 (pending-write recovery) bằng side-effect counter thật (không suy
   diễn từ log): nhánh `branch_b` "crash" (raise) sau khi `root`+`branch_a` đã
   thành công; tạo checkpointer/graph instance MỚI cùng `thread_id`, resume —
   **PASS**: `root`/`branch_a` KHÔNG chạy lại (call_count giữ nguyên = 1),
   `branch_b` chạy lại đúng 1 lần, `join` chạy đúng 1 lần sau khi toàn bộ
   dependency sẵn sàng. Xác nhận đúng tuyên bố HL-13 của acceptance matrix.

**Đối chiếu native `WorkflowEngine`:** `tests/agent_core/workflows/` hiện có
63 test pass (DAG, compensation, checkpoint/resume, governance, approval
step) — xác nhận native engine vẫn giữ nguyên năng lực đã có từ spike gốc,
không bị thoái hoá qua 11 Wave vừa xây (Wave 1-11 không đụng vào
`packages/agent_core/workflows/engine.py`).

**Kết luận:** Re-spike XÁC NHẬN LẠI (không lật ngược) quyết định REJECT của
`ADR-LANGGRAPH-adoption-decision.md`. LangGraph vẫn kỹ thuật khả thi đúng như
spike gốc mô tả — không có gì thay đổi ở phía LangGraph. Nhưng lý do reject
gốc (chi phí framework coupling + serialization overhead lớn hơn lợi ích so
với `WorkflowEngine` native đã đủ năng lực) **vẫn đúng**: native engine không
hề thoái hoá, và việc thêm LangGraph làm dependency runtime chính thức không
mang lại năng lực mới nào mà native chưa có. **Không đề xuất mở ADR mới,
không đổi status `ADR-LANGGRAPH-adoption-decision.md`.** Package
`packages/agent_integrations/langgraph/` giữ lại như bằng chứng re-spike +
tài liệu tham khảo (không wire vào `apps/cosa/composition/`), đúng tinh thần
"harvest patterns, không adopt dependency" của quyết định gốc.
