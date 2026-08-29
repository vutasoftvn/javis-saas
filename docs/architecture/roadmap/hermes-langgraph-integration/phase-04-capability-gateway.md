# Phase 4 — Capability Layer & Invocation Identity (+ Readiness Minimum Enforcement)

> Nguồn gốc: `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md` §"Phase 4" (Step 7, P0.5–P0.9). Bổ sung Hermes/LangGraph theo `COSA_HERMES_LANGGRAPH_INTEGRATION_PLAN_2026-08-23.md` §3.

## Mục tiêu

Capability Gateway thật, invocation identity ổn định, test chứng minh idempotency qua kịch bản crash thật — và (mới) readiness check tối thiểu chèn đúng vị trí trong pipeline thật.

## Điều kiện tiên quyết

Phase 2 (bảng `run_tool_calls`) và Phase 3 (kernel phát tool-call events) đã xong.

## Việc cụ thể (gốc)

1. Viết `packages/agent/capabilities/gateway.py` implement pipeline đầy đủ: resolve capability → validate input (theo `CapabilitySpec` Phase 1) → resolve connector/grant → construct `InvocationIdentity` ổn định → policy evaluate (gọi `governance/`) → accumulate governance → approval gate (check `agent.approvals`) → construct `ExecutionTargetSnapshot` → idempotency check (theo `idempotency_key`) → execute → audit (ghi `run_events`) → persist (`run_tool_calls`).

   > **Lưu ý verify code thật:** pipeline hiện tại (`packages/agent/capabilities/gateway.py`) đã tồn tại với thứ tự: resolve capability → validate input → canonicalize+hash → build invocation identity & target snapshot → idempotency → policy → governance accumulate → approval → execute handler. `connector_id` trong target snapshot hiện chỉ lấy trực tiếp `spec.connector_requirements.get("connector_id")`, KHÔNG có health-check thật. Đây chính là chỗ readiness minimum enforcement (mục bổ sung dưới) cần chèn vào.

2. Stable `tool_call_id`: nếu SDK cung cấp call ID ổn định từ Phase 3, dùng trực tiếp; nếu không, sinh UUID nội bộ và map rõ external↔internal trong `run_tool_calls`.
3. Payload canonicalization: hàm canonicalize input (sort keys, normalize types) trước khi hash — dùng cho cả `payload_hash` lẫn idempotency key.
4. Viết idempotency failure-window test:
   - bước 1: gọi capability write giả lập (mock external API ghi vào file/DB phụ giả lập "remote system");
   - bước 2: remote system "commit" thành công;
   - bước 3: kill process COSA (thật, qua subprocess) TRƯỚC khi mark `run_tool_calls.status = completed`;
   - bước 4: restart/retry cùng `idempotency_key`;
   - bước 5: assert không có side effect thứ hai ở remote system, COSA reconcile được kết quả gốc.

## Bổ sung Hermes/LangGraph — CapabilityReadiness Minimum Enforcement

**Vị trí chính xác trong pipeline (đã verify từ code thật):** chèn giữa bước "build invocation identity & target snapshot" và bước "idempotency check / policy evaluate" — KHÔNG dồn về P2/Phase F như supplement gốc §18/§43 đề xuất, vì đây đúng là điểm pipeline thật cần nó.

**Việc cụ thể:**

1. Viết `packages/agent/capabilities/readiness.py`:
   ```text
   CapabilityReadinessChecker (Protocol):
       async def check(capability_id, run_context) -> CapabilityReadiness
   ```
   Implementation Phase 4 là **stub/minimum**: kiểm tra connector_id có tồn tại trong config/registry không (không cần health-check network thật — đó là Phase 9).
2. Tích hợp vào gateway pipeline:
   ```python
   readiness = await readiness_checker.check(capability_id, run_context)
   if not readiness.ready and readiness.reason_code == "MISSING_CREDENTIAL":
       raise CapabilityReadinessError(readiness)   # block rõ ràng
   if not readiness.ready and readiness.reason_code == "CONNECTOR_OFFLINE":
       logger.warning(...)   # log, tiếp tục — governance quyết định cuối cùng
   # else: tiếp tục pipeline bình thường
   ```
3. **Security nuance (khác supplement gốc):** không đặt ordering tuyệt đối "readiness luôn chạy trước policy" — readiness có thể leak thông tin (vd. "Stripe account CFO_PROD đang online") cho principal chưa được authorize biết connector đó tồn tại. Đánh giá static eligibility (principal có được phép thấy capability này không) TRƯỚC khi expose `reason_code` chi tiết.
4. **LangGraph ToolStep integration** (chỉ nếu spike Phase 3 tiếp diễn trên branch riêng): chứng minh ToolStep node trong LangGraph graph gọi đúng qua `CapabilityGateway` (bao gồm readiness check mới), không bypass — đây là bước đầu tiên spike chạm vào boundary thật thay vì giả lập như ở Phase 3.

## Test bắt buộc

**Gốc:**
- `CapabilityGateway` chạy được ít nhất 1 capability giả lập (mock, chưa cần nối `services/company` — Phase 7) qua đủ pipeline 10 bước.
- `tool_call_id` không bao giờ trùng giữa 2 lần gọi khác nhau trong cùng Run.
- Idempotency failure-window test pass.

**Bổ sung:**
- Test case readiness `CONNECTOR_OFFLINE` + governance `ALLOW` → proceed với warning, không block.
- Test case readiness `READY` + governance `DENY` → blocked bởi governance, không phải bởi readiness — chứng minh tách biệt `Readiness ≠ Authorization`.
- (Nếu LangGraph spike tiếp diễn) test ToolStep gọi qua gateway, không bypass readiness/policy.

## Definition of Done — Phase 4

**Gốc:**
- `CapabilityGateway` chạy được qua đủ pipeline 10 bước.
- `tool_call_id` không trùng trong test "same tool twice".
- Idempotency failure-window test pass — điều kiện bắt buộc theo Master doc §17.3.

**Bổ sung:**
- Readiness check đã tích hợp đúng vị trí trong pipeline thật (verify bằng đọc code, không chỉ test pass).
- 2 test case readiness/governance độc lập ở trên pass.

## Rủi ro/lưu ý

**Gốc:** Kịch bản "kill process giữa lúc side-effect đã commit nhưng local chưa mark success" khó mô phỏng đúng — cần điểm dừng xác định (`os.kill` sau khi mock remote ghi file nhưng trước khi COSA update DB), không dùng sleep đoán thời điểm.

**Bổ sung:** Readiness dễ bị lạm dụng làm "authorization nhẹ" nếu implement ẩu — luôn giữ tách biệt rõ ràng 2 khái niệm trong code (không gộp field `ready` và `allowed` vào cùng object trả về từ cùng một hàm).
