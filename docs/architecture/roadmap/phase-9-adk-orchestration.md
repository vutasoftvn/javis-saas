# Phase 9 — ADK Orchestration Port

> Chi tiết thực thi cho Phase 9 của `docs/architecture/COSA_IMPLEMENTATION_ROADMAP_2026-08-22.md`. **Nguyên tắc bắt buộc, không thương lượng:** port hành vi/invariant từ `legacy/agent_runtime/workforce/agents/orchestration/adk/` vào `agentos/orchestration/adk/`, **không `mv`/import nguyên dependency graph legacy**. Mọi side effect từ ADK node phải qua Tool Gateway đã chuẩn hoá ở Phase 3, không có ngoại lệ.

## Bối cảnh đã xác nhận

- `agentos/orchestration/adk/` **không tồn tại**. ADK implementation thật chỉ có ở `legacy/agent_runtime/workforce/agents/orchestration/adk/`: `workflow.py, governed_tool.py, model_adapter.py, session_bridge.py, session_service_factory.py, specialist_delegation.py`, và `nodes/{approval_gate_node, build_company_context_node, create_mission_node, execution_node, governance_gate_node, planning_node, quality_gate_node, risk_classification_node, specialist_delegation_node, synthesis_node}.py`.
- `agentos/requirements.txt` chưa pin `google-adk` (chỉ có `httpx, pydantic, PyYAML, pytest, pytest-asyncio`). Gói `google_adk==2.7.0` có mặt trong `.venv` (khả năng do cài đặt dev từ trước) nhưng **không phải dependency khai báo của `agentos/`** — không được coi là "đã sẵn sàng dùng" chỉ vì có trong venv.
- `AgentRuntimeAdapter` Protocol đã có ở `agentos/core/adapters/contracts.py` (Phase 0b) — `async def run(self, context: AgentContext) -> tuple[str, int]`. Đây là interface ADK orchestrator phải implement để cắm vào composition root.
- `deepseek_harness_provider.py` xác nhận là model-call wrapper thuần, không có tool loop — tool loop hiện nằm ở `agentos/core/executor.py`. ADK port phải quyết định: dùng tool loop của `Executor` bên trong mỗi specialist node, hay ADK tự có tool loop riêng (khuyến nghị: tái dùng `Executor`, không viết tool loop thứ hai).

## 9a. Pin & xác nhận dependency

**Task:**
1. Pin `google-adk==2.7.0` (khớp version đã có trong `.venv`, tránh mismatch) và `deepseek-harness-sdk` (khớp version legacy đã pin, kiểm tra `legacy/agent_runtime/requirements.txt` để lấy đúng version — không tự đoán) vào `agentos/requirements.txt`.
2. Cài lại từ requirements sạch (venv mới hoặc `pip install --force-reinstall`) để xác nhận không có dependency conflict giữa `google-adk` và các package hiện có của `agentos/`.

**Acceptance:**
- [ ] `agentos/requirements.txt` có 2 dòng pin version cụ thể.
- [ ] `pip install -r agentos/requirements.txt` trên venv sạch không lỗi conflict.

## 9b. Port node theo invariant, không port nguyên khối

**Task — với mỗi node trong `legacy/.../orchestration/adk/nodes/`, làm theo quy trình sau (không copy-paste file):**
1. Đọc node legacy, xác định **invariant nghiệp vụ** thật sự cần giữ (ví dụ `governance_gate_node.py` giữ đúng logic "chặn nếu risk cao chưa duyệt" — không giữ cách nó gọi DB/session cụ thể của legacy).
2. Viết lại node tương ứng trong `agentos/orchestration/adk/nodes/` bằng cách gọi các thành phần `agentos/` hiện có thay vì code legacy:
   - `governance_gate_node.py` → gọi `evaluate_access()` (Phase 1c), không tự implement logic quyết định riêng.
   - `approval_gate_node.py` → gọi `ApprovalService`/luồng pause-resume (Phase 8a), không tạo cơ chế approval thứ hai.
   - `execution_node.py` → gọi `Executor` (`AgentRuntimeAdapter` implementation, Phase 0b) để chạy 1 specialist với tool loop có sẵn, không viết tool loop mới.
   - `build_company_context_node.py` → gọi `ContextBuilder` (Phase 4c/7D) đã có sẵn memory/knowledge/skill wiring, không tự query business data riêng.
   - `specialist_delegation_node.py` → gọi `SkillRegistry`/`AgentProfile` (Phase 5) để chọn specialist phù hợp, không hard-code danh sách specialist trong node.
   - `risk_classification_node.py` → dùng `ToolRiskLevel` (Phase 1c/3a) đã chuẩn hoá, không tự định nghĩa thang risk riêng.
   - `quality_gate_node.py`, `synthesis_node.py`, `planning_node.py`, `create_mission_node.py` → port logic nghiệp vụ thuần (không phụ thuộc DB/session legacy), viết lại bằng Python thuần trong `agentos/orchestration/adk/nodes/`.
3. `session_bridge.py`/`session_service_factory.py`: đánh giá xem ADK SDK 2.7.0 có built-in session service phù hợp không (đọc doc/source `google-adk` đã cài) — nếu có, dùng thẳng, không port bridge tuỳ chỉnh của legacy trừ khi ADK SDK thật sự thiếu tính năng đó.
4. **Không node nào được** import trực tiếp từ `legacy/` sau khi port xong — kể cả tạm thời. Nếu 1 node chưa port xong, để trống có `NotImplementedError` rõ ràng, không fallback âm thầm về code legacy.

**Acceptance:**
- [ ] `grep -r "legacy" agentos/orchestration/adk/` không có kết quả.
- [ ] Mỗi node có ít nhất 1 test xác nhận nó gọi đúng thành phần `agentos/` tương ứng (governance qua `evaluate_access`, approval qua `ApprovalService`, v.v.) — dùng mock để verify lời gọi, không chỉ test output cuối.
- [ ] Test end-to-end: 1 mission ví dụ (2 specialist chạy song song rồi synthesis) chạy qua toàn bộ node đã port, ra kết quả hợp lý.

## 9c. Orchestrator lifecycle & specialist delegation

**Task:**
1. `agentos/orchestration/adk/orchestrator.py` — quản lý vòng đời 1 mission: `create_mission → planning → parallel specialist execution → quality_gate → synthesis → (approval nếu cần) → hoàn tất`.
2. Specialist delegation: route tới đúng `AgentProfile` (Phase 5c) dựa trên nội dung task con — không hard-code mapping, đọc từ `SkillRegistry`/`AgentProfile` registry.
3. Parallel execution: nhiều specialist chạy đồng thời qua `asyncio.gather` hoặc tương đương, mỗi specialist là 1 lời gọi `Executor.run()` độc lập với `AgentContext` riêng — không chia sẻ state ngầm giữa các specialist đang chạy song song (tránh race condition).
4. Không side effect nào (ghi DB, gọi API bên ngoài) xảy ra trực tiếp trong orchestrator — mọi side effect đi qua specialist's tool call, được `evaluate_access()` gác cổng như bình thường.

**Acceptance:**
- [ ] Test: mission với 2 specialist độc lập → cả 2 chạy song song (đo thời gian xác nhận), kết quả tổng hợp đúng ở bước synthesis.
- [ ] Test: 1 specialist trong mission cần approval → mission tạm dừng đúng ở bước đó (dùng lại cơ chế Phase 8a), không phải cả mission bị treo hoàn toàn hay tự động bỏ qua.
- [ ] Review thủ công: `orchestrator.py` không có dòng nào gọi DB/HTTP business trực tiếp — chỉ điều phối, mọi thực thi qua specialist/tool.

## 9d. Composition root routing (§9.2)

**Task:**
1. Mở rộng `build_cosa_agent_plane()` (Phase 0b) thêm logic chọn runtime:
```
Nếu request có marker multi-agent/mission (ví dụ agent_profile chỉ định orchestration_mode="multi_agent", hoặc intent phân loại cần nhiều specialist)
    → khởi tạo ADK Orchestrator (9c)
Nếu agent_profile.preferred_runtime == "deepseek_harness"
    → khởi tạo DeepSeekHarnessRuntimeAdapter (đã có model-call wrapper, cần wrap thêm để implement AgentRuntimeAdapter Protocol nếu chưa đủ)
Mặc định
    → Native Executor (fallback, đã có từ trước)
```
2. Cả 3 runtime đều implement `AgentRuntimeAdapter` Protocol (Phase 0b) — `AgentRuntime`/Agent API (Phase 4) gọi đồng nhất `runtime.run(context)`, không có nhánh đặc biệt theo runtime nào ở tầng gọi.
3. Trace/audit/approval logic (Phase 0a, 1c, 3d) phải hoạt động giống hệt bất kể runtime nào được chọn — test `test_runtime_convergence.py` (đã có từ Phase 0b) phải được mở rộng thêm case cho ADK runtime.

**Acceptance:**
- [ ] Test: request đơn giản (1 agent, không cần specialist) → route tới Native Executor.
- [ ] Test: request có marker multi-agent → route tới ADK Orchestrator.
- [ ] Test: `agent_profile.preferred_runtime="deepseek_harness"` → route tới DSH adapter.
- [ ] `test_runtime_convergence.py` mở rộng pass cho cả 3 runtime — governance/approval không đổi hành vi theo runtime.

## Dependency

9a làm trước tiên (dependency phải sẵn sàng). 9b phụ thuộc Phase 1c (governance), Phase 5 (skill/profile registry), Phase 4c/7D (ContextBuilder đầy đủ), Phase 8a (approval pause/resume). 9c phụ thuộc 9b (node đã port xong). 9d phụ thuộc 9c và Phase 0b (composition root, Protocol).
