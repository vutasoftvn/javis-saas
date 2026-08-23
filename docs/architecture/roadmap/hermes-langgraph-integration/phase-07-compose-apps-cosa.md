# Phase 7 — Compose `apps/cosa/` (+ Context Assembler thật)

> Nguồn gốc: `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md` §"Phase 7" (Step 8, P0.11). Bổ sung Hermes/LangGraph theo `COSA_HERMES_LANGGRAPH_INTEGRATION_PLAN_2026-08-23.md` §3.

## Mục tiêu

Có composition boundary thật, gọi được ít nhất 1 read + 1 write capability thật vào `services/company/` — và (mới) đây là nơi đầu tiên chứng minh use case thật cho `ContextSnapshot`/`ContextFragment` (đóng băng contract ở Phase 1), tránh abstraction đóng băng không có consumer.

## Điều kiện tiên quyết

Phase 1–6 đã xong (đủ contracts, kernel, capability gateway + readiness, approval, drift tests, quyết định LangGraph đã đóng ở ADR-LANGGRAPH).

## Việc cụ thể (gốc)

1. Tạo cấu trúc `apps/cosa/{api,composition,policies,capabilities,agents,workflows}/` theo Master doc §4.
2. `apps/cosa/composition/`: dùng bảng dependency graph đã ghi lại từ `build_cosa_agent_plane()` ở Phase 0 (PROMOTE composition knowledge) làm checklist — implement lại composition root: model provider, capability registry, memory/knowledge port (stub tạm nếu Phase 9 chưa xong), policy engine, approval service, trace/audit, tất cả từ `packages/agent_core/*` đã build.
3. `apps/cosa/capabilities/`: implement 1 read-only capability thật gọi `services/company/operations` hoặc `services/company/operations/strategy` (vd. `operations.task.read` hoặc `strategy.gate.read`) qua Encore RPC/HTTP client hiện có — đây là nơi DUY NHẤT được phép import `services/company/*`.
4. Implement 1 write capability thật có approval gate risk MEDIUM+ (vd. một action trong `finance-legal`) — dùng đầy đủ pipeline Phase 4–5.
5. Reusability gate check: viết 1 script/test riêng compose "app thứ hai" giả lập, chỉ dùng `RunService`/`ExecutionKernel`/`WorkflowEngine`/Capability contract/Events/Governance/Memory-Knowledge ports từ `packages/agent_core/`, KHÔNG import gì từ `services/company`. Nếu import bị cần thì boundary chưa đạt — sửa lại `packages/agent_core/` trước khi tuyên bố Phase 7 xong.

## Bổ sung Hermes/LangGraph — Context Assembler thật

**Nguyên tắc:** salvage invariant từ audit Phase 0 (`docs/architecture/CONTEXT_ASSEMBLER_AUDIT.md`), KHÔNG port code legacy nguyên xi (vi phạm boundary `agent_core` không import business domain — legacy `CofounderContextAssembler` query trực tiếp SQLAlchemy business models).

**Việc cụ thể:**

1. Viết `apps/cosa/composition/context_assembler.py` implement `ContextAssemblerPort` (đóng băng ở Phase 1):
   ```python
   class COSAContextAssembler(ContextAssemblerPort):
       def __init__(self, company_service, memory_provider, knowledge_provider): ...
       async def assemble(self, principal_id, tenant_id, intent, metadata={}) -> ContextSnapshot:
           # STABLE: workspace/identity/tenant policy — qua Encore RPC tới services/company
           # RUN: current project/strategy stage — qua Encore RPC
           # CURRENT: KPI snapshot — fresh read qua Encore RPC
           # EPHEMERAL: approval response nếu có trong metadata
           ...
   ```
2. Salvage cụ thể từ audit Phase 0 (giữ ý tưởng, viết lại code):
   - **Giữ:** governance-before-fetch (`builder.py`) — đánh giá quyền truy cập fragment TRƯỚC khi gọi Encore RPC, không fetch rồi mới lọc.
   - **Giữ:** intent-based scoping concept (`assembler.py`) — nhưng thay vì hardcode 5 loại intent gắn chặt với domain founder, định nghĩa `ContextIntent` framework-neutral (`kind: str`, `domain: str | None`) theo contract Phase 1.
   - **Giữ có điều kiện:** progressive disclosure L0-L5 concept (`compiler.py`) — chỉ implement mức cần thiết cho use case thật đầu tiên ở Phase 7 (thường L0-L2 đủ); KHÔNG cố gắng hoàn thiện L5/rebalance-token-thật ở đây nếu chưa có consumer cần — đó là việc của Phase 9.
   - **KHÔNG mang theo:** query trực tiếp SQLAlchemy business model — mọi truy cập business data phải qua Encore RPC client tới `services/company`, đúng boundary composition root.
   - **KHÔNG mang theo:** graceful-degradation kiểu `except Exception: return {}` không phân biệt lỗi — dùng logging/observability rõ ràng phân biệt "không có data" vs "lỗi gọi API" (cùng nguyên tắc sẽ áp dụng cho `AgentChatService` ở Phase 8).
3. Test bắt buộc: assemble context cho ít nhất 1 intent thật (vd. `founder_review`) trả về `ContextSnapshot` với fragment đúng lifetime (STABLE cho workspace, RUN cho project hiện tại, CURRENT cho KPI nếu có).

## Definition of Done — Phase 7

**Gốc:**
- `apps/cosa/` chạy được 1 read capability + 1 write capability thật (không mock) chống lại `services/company/` dev instance.
- Reusability gate check script pass.
- `grep -r "services.company" packages/agent_core/` → rỗng.

**Bổ sung:**
- Integration test: context assembly cho ≥1 intent thật trả về `ContextSnapshot` đúng lifetime, gọi qua Encore RPC.
- `grep -r "sqlalchemy" apps/cosa/composition/context_assembler.py` không import trực tiếp business ORM model (chỉ gọi qua RPC client) — kiểm tra thủ công khi review, không có business model class nào được import trực tiếp từ `services/company`.

## Rủi ro/lưu ý

**Gốc:** Đây là phase dễ bị cám dỗ import tắt cho nhanh — giữ kỷ luật boundary vì đây là gate cuối cùng chứng minh Agent Core "tái sử dụng được".

**Bổ sung:** Rủi ro riêng: bị cám dỗ port thẳng `CofounderContextAssembler` vì "đã có sẵn, chạy được" — đây chính xác là REJECT đã ghi trong Integration Plan §5; nếu áp lực thời gian lớn, thà làm ít intent hơn (1 thay vì 5) còn hơn vi phạm boundary.
