# Kiến trúc tổng quan — Agent Platform (sau Wave 0-11, 2026-08-24)

> Tài liệu này tóm tắt trạng thái THẬT của kiến trúc sau khi hoàn thành
> `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` Wave 0-11 +
> 2 fix follow-up (governance durability, 6 ADR bổ sung). Không phải bản lặp
> lại nội dung Blueprint V2 — chỉ ghi những gì ĐÃ tồn tại trong code, kèm
> trạng thái verify thật.

## 4 vùng kiến trúc (không đổi từ CLAUDE.md)

```text
Experience Plane      Flutter (chưa đụng trong phiên này)
COSA Control Plane    services/cosa      (Encore/TS — identity/license + control-plane mới Wave 7)
Company Business      services/company   (Encore/TS — không đụng trong phiên này)
Agent Platform        packages/agent_core (Python, reusable) + apps/cosa (Python, composition)
                       packages/agent_integrations (Python, runtime adapter — MỚI từ Wave 0)
                       packages/agent_recipes (Python/YAML, recipe corpus — MỚI từ Wave 11)
```

## Execution spine (Wave 1-2, đã harden)

```
ExecutionKernel (OpenAIAgentsKernel mặc định | LangChainKernel opt-in)
  → publish spec vào agent_registry (bất biến, version+hash pin)
  → resolve pinned_skills (từ chối nếu hash không khớp — chống floating reference)
  → PromptBundle (platform policy + agent instructions + skill instructions + locale)
  → vòng lặp reasoning → tool call
    → CapabilityGateway.execute() [10 bước]
      → atomic idempotency claim
      → governance accumulate (durable, GovernanceStateStore)
      → approval gate (CAS decision)
      → execute handler → audit event
```

## Runtime priority (ADR-RUNTIME-001, DRAFT chưa review)

Mặc định production: `OpenAIAgentsKernel` (manual loop, chưa phải SDK thật). `LangChainKernel` là opt-in tường minh qua `runtime="langchain"`. Google ADK chạy production THẬT nhưng ở `legacy/backend/`, ngoài `packages/agent_integrations/`.

## Control Plane (Wave 7, TypeScript/Encore — CHƯA verify Postgres/Encore CLI thật)

`services/cosa` có thêm schema `control_plane` (missions/tasks/assignments/workers/runtime_leases/scheduled_tasks/watches/signal_observations/delivery_policies/delivery_attempts/cost_ledger) — port từ 2 class Python in-memory (`RunLeaseManager`/`RunScheduler`) vốn KHÔNG có consumer production nào.

## Protocol layer (Wave 9)

MCP (tool discovery → CapabilitySpec, qua đúng Gateway), A2A (authority attenuation, invariant `child ⊆ parent`), AG-UI (event normalize cho UI client) — cả 3 ở `packages/agent_integrations/`.

## Điểm khác biệt lớn nhất so với thiết kế ban đầu

Xem `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` và các ADR trong `docs/architecture/adr/` (đặc biệt `ADR-RUNTIME-001`, `ADR-CONTROLPLANE-001`, `ADR-SKILL-IDENTITY-trigger-based-evaluation.md` §4) để biết chính xác quyết định nào đảo ngược quyết định đã ratify trước đó và tại sao.

## Giới hạn xác nhận (2026-08-24)

Toàn bộ Python (`packages/agent_core`, `packages/agent_integrations`, `packages/agent_recipes`) đã test pass (256 passed, 15 skipped cần Postgres/DeepSeek key thật). TypeScript (`services/cosa` Wave 7) chỉ verify được bằng `tsc --noEmit` — không có Encore CLI trong môi trường phát triển.
