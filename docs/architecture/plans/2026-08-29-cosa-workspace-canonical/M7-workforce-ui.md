# M7 — AI workforce & UI integration

**Audit:** §9.7, §7, §3.9, §3.13, §3.8 · **Phụ thuộc:** M2, M4 · **Master:** [../2026-08-29-cosa-workspace-canonical-master-plan.md](../2026-08-29-cosa-workspace-canonical-master-plan.md)

## Context

Backend đã capability/function-first:
- [packages/agent_core/contracts/spec.py:15-69](../../../../packages/agent_core/contracts/spec.py#L15-L69) —
  `AgentSpec` pin `capability_refs`, `pinned_skills`, `model_policy`, `model_policy_ref`, `definition_hash`.
- [services/company/identity/services/workforce.service.ts:10-20](../../../../services/company/identity/services/workforce.service.ts#L10-L20) —
  `workforce_members` tách `agent_spec_id`/`agent_spec_version` khỏi `role_title`.
- [packages/agent_core/coordination/supervisor.py:27-112](../../../../packages/agent_core/coordination/supervisor.py#L27-L112) — `SupervisorCoordinator`.
- Capability Gateway + idempotency + durable approval: [packages/agent_core/capabilities/gateway.py](../../../../packages/agent_core/capabilities/gateway.py),
  `idempotency.py`, `approval_service.py`.

Nhưng UI chia đôi:
- [frontend/lib/modules/agents/services/agent_platform_service.dart:34-194](../../../../frontend/lib/modules/agents/services/agent_platform_service.dart#L34-L194) —
  hardcode `default12Agents` (Founder Copilot, General Assistant, CFO, CMO, Sales, CTO,
  Developer, DevOps, Legal, HR, Product, Data Analyst) + hardcode org chart; `return
  default12Agents` khi API lỗi.
- Gọi `/workforce/agents`, `/workforce/packs`, `/workforce/org-chart` — **chưa có backend**;
  lỗi API bị che bằng fallback tĩnh.

Vertical slice chưa nối (audit §3.9): `VentureOnboardingScreen`, `EntitlementProvider`,
`ReconciliationCard`, `CitationCard`, `ActionProposalCard` chỉ trong file định nghĩa/test.
`EntitlementProvider` đọc `features`/`limits`; backend trả `effectiveFeatures`/`effectiveLimits`.
[frontend/lib/core/network/api_client.dart:92-102](../../../../frontend/lib/core/network/api_client.dart#L92-L102)
rewrite `/finance/`→`/finance-legal/`, `/legal/`→`/finance-legal/` trong khi API TT58/legal-entity
mới expose dưới `/finance/` và `/legal/`.

Finance calc (audit §3.8): [financial-snapshot.service.ts:40-70](../../../../services/company/finance-legal/services/financial-snapshot.service.ts#L40-L70)
cộng toàn bộ IN/OUT lịch sử, `currentCash = cashIn - cashOut`, `netBurn = cashOut - cashIn`,
`runway = currentCash / netBurn`, hard-code `99` khi cash-flow dương.

Chọn **phương án C** (audit §7.1): function/capability-first + role/persona overlay.

## Deliverables

### 1. Functional AgentSpec catalog + capability boundaries (audit §7.2)
Ba lớp identity:
```
Capability            finance.transaction.read, finance.cashflow.forecast,
                      finance.payment.propose, marketing.campaign.plan, legal.obligation.assess ...
Functional AgentSpec  Cashflow Planner, Accounting Document Specialist, Market Research Specialist,
                      Campaign Planner, Compliance Analyst ...
Workforce Assignment  Finance Copilot, CFO, CMO, COO, Chief of Staff  (role/persona overlay)
```
- `agent_spec_id + version + definition_hash` = execution identity.
- `role_title`, display name, department, manager = workspace-level presentation/organization metadata.
- Chuẩn hóa catalog spec trong `packages/agent_core` (registry published specs).

### 2. Workspace workforce assignment/persona/manager model (audit §7.5)
- Backend source of truth: published AgentSpec registry + workspace workforce assignments +
  role/persona/manager hierarchy + capability readiness + entitlement/stage eligibility +
  active runs/health/budget/approval queue.
- Schema: mở rộng `workforce_members` ([workforce.service.ts:10-20](../../../../services/company/identity/services/workforce.service.ts#L10-L20))
  + bảng `workforce_assignments` / `workforce_org_edges` nếu cần manager hierarchy.

### 3. Implement `/workforce/*` endpoints (audit §9.7.3)
- `GET /workforce/agents` — list functional agents + assignment + readiness + entitlement/stage eligibility.
- `GET /workforce/packs` — default packs theo workspace/project stage.
- `GET /workforce/org-chart` — role/persona/manager hierarchy từ assignment model.
- `+` readiness + budget endpoints.
- Handler + service mới trong `services/company/identity/`.
- [agent_platform_service.dart:34](../../../../frontend/lib/modules/agents/services/agent_platform_service.dart#L34) —
  **bỏ `return default12Agents`**; backend unavailable ⇒ hiển thị unavailable/stale state rõ ràng
  (không fake workforce).

### 4. Stage-aware composition (audit §7.3)
```
eligible = workspace_stage_policy + project_stage_policy + entitlement
         + capability_readiness + connector/data availability + risk/approval policy
```
- Default packs W0–W5 theo bảng §7.3 audit (W0–W1: Founder Office/Chief of Staff, Problem
  Research, Evidence Analyst, Finance Basics, Legal Readiness; … W5: domain supervisors +
  persona CFO/CMO/COO).
- Project P0 trong workspace W4 vẫn nhận Discovery/Research composition cho project context đó
  (đọc cả hai stage — có từ M4).

### 5. Governance: title không cấp quyền (audit §7.4)
- CFO Agent không tự approve payment vì có title CFO; CMO Agent không tự publish/spend campaign
  nếu policy yêu cầu human approval.
- High-risk approval resolve tới human principal/role hoặc quorum policy đã xác minh.
- Agent write luôn qua Capability Gateway + idempotency + durable approval
  ([gateway.py](../../../../packages/agent_core/capabilities/gateway.py), `idempotency.py`, `approval_service.py`).
- Role/title change KHÔNG silent-widen capability; mọi capability change tạo spec/version/hash mới.
- Founder Office/Chief of Staff orchestration; C-suite persona chỉ là role overlay theo stage.

### 6. Nối vertical slices vào production flow (audit §3.9)
- [VentureOnboardingScreen](../../../../frontend/lib/modules/onboarding/screens/venture_onboarding_screen.dart) —
  vào navigation thật; onboarding tạo account + workspace + venture profile + evidence seed;
  gửi đủ `problemStatement`/`targetCustomer`/`goal` + email/password.
- [EntitlementProvider](../../../../frontend/lib/shared/providers/entitlement_provider.dart) —
  đọc `effectiveFeatures`/`effectiveLimits` (khớp backend), không `features`/`limits`.
- [ReconciliationCard](../../../../frontend/lib/modules/finance/widgets/reconciliation_card.dart),
  [CitationCard](../../../../frontend/lib/modules/legal/widgets/citation_card.dart),
  [ActionProposalCard](../../../../frontend/lib/modules/strategy/widgets/action_proposal_card.dart) —
  vào screen Finance/Legal/Strategy thật (screen chính đã có route + controller; chỉ cần nối slice).
- [api_client.dart:92-102](../../../../frontend/lib/core/network/api_client.dart#L92-L102) —
  **bỏ** rewrite `/finance/`→`/finance-legal/` và `/legal/`→`/finance-legal/`; để client gọi
  đúng path API expose (`/finance/...`, `/legal/...`, `/finance-legal/...` theo route inventory M0).

### 7. Contract-test / client generation cho route production UI (audit §9.7.8)
- Sinh client hoặc contract test cho toàn bộ route UI dùng → ngăn route drift tái diễn.
- Tích hợp CI route-alias lint (M0).

### 8. Fix finance calculation (audit §3.8)
- [financial-snapshot.service.ts:40-70](../../../../services/company/finance-legal/services/financial-snapshot.service.ts#L40-L70):
  - `currentCash` = số dư thật (opening balance + Σ transactions tới kỳ), không phải
    `cashIn - cashOut` toàn lịch sử.
  - `netBurn` = burn theo kỳ (trailing N tháng, mặc định 3), không phải tổng lịch sử.
  - `runway = currentCash / monthlyNetBurn` khi `monthlyNetBurn > 0`; cash-flow dương ⇒ trả
    `null` / cờ `cashFlowPositive: true`, **bỏ hard-code `99`**.
  - Reconciliation accept đã siết ở M1 (proposal PENDING, cùng workspace, `acceptedBy` ghi).

## Test plan (audit §10.8, §10.9)

- Agent selection dùng workspace stage + project stage + entitlement + readiness + risk.
- Role/title change không làm capability widen.
- CFO/CMO AI không tự approve high-risk action.
- Org chart + packs lấy từ backend source of truth, không hardcoded fallback.
- AgentSpec/version/hash pin trong run manifest và resolve lại được lịch sử.
- Cloud/local runtime resolve cùng AgentSpec/policy version cho cùng mission.
- Contract test cho toàn bộ route production UI sử dụng.
- Entitlement đọc đúng `effectiveFeatures`/`effectiveLimits`.
- Onboarding tạo account + workspace + venture profile + evidence seed.
- Reconciliation/citation/action proposal test từ screen → controller → API → DB/outbox.
- UI không biến network/backend failure thành fallback "thành công" hoặc fake workforce.
- Runway: dataset burn đều ⇒ runway hợp lý; cash-flow dương ⇒ không trả 99.

## Exit gate

- [ ] Org chart phản ánh registry/workforce thật; `default12Agents` không còn trong production path.
- [ ] Title change không đổi capability (test).
- [ ] High-risk action vẫn cần human approval.
- [ ] 5 vertical slice nối vào production flow; entitlement key khớp; `normalizeEndpoint` rewrite đã gỡ.
- [ ] Contract test route UI xanh; CI route lint xanh.
- [ ] Finance runway không hard-code 99; test dataset pass.

## Ngoài phạm vi M7

Outcome-based pricing. Autonomous multi-agent org tầm nhìn 2030 (audit §7.6 — chỉ mở khi tổ
chức đủ trưởng thành + governance tương ứng). Marketplace AgentSpec.
